"""
FindMyJobAI Backend - Main FastAPI Application
Endpoint: /api/jobs/stream (StreamingResponse)
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Ensure the parent directory is in sys.path so 'shared' module is found
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import FastAPI, Request, Query, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Import configuration
from app.config import get_settings

# Import services
from app.services.scorer import score_jobs
from app.services.aggregator import SearchAggregator, normalize_jobs_for_frontend
from app.services.cache import cache_service
from app.services.llm_service import llm_service
from app.api.cache import router as cache_router

# Import scrapers
from app.scrapers.api_sources import get_france_travail_source, get_france_travail_rss_source, get_adzuna_source, get_google_jobs_source, get_jooble_source, get_apify_source
from app.scrapers.bypass_strategies import get_optimal_limit
from app.scrapers.web_sources import (
    scrape_indeed,
    scrape_linkedin,
    scrape_monster,
    scrape_hellowork,
    scrape_google_jobs,
    scrape_jobspy,
    scrape_enhanced,
)
from app.scrapers.freelance_sources import (
    scrape_free_work,
    scrape_codeur_com,
    scrape_freelance_republik,
)

from shared.ai import call_ai_provider, analyze_cv_with_fallback, generate_cover_letter
from shared.utils import extract_text_from_pdf
from app.services.chat import ChatRequest, build_system_prompt, orchestrate_chat_fallback
from app.agents.job.cv_analyzer import analyze_job_cv
from app.agents.job.filters import validate_job_filters
from app.agents.job.searcher import JobSearcher
from app.agents.freelance.cv_analyzer import analyze_freelance_cv
from app.agents.freelance.filters import validate_freelance_filters
from app.agents.freelance.searcher import FreelanceSearcher
from app.agents.recruiter.cv_analyzer import analyze_recruiter_cv
from app.agents.recruiter.filters import validate_recruiter_filters
from app.agents.recruiter.searcher import WorkerSearcher
import io
import re

import httpx


import logging
import json
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load settings
settings = get_settings()

# Limits used by search and display logic
MAX_DISPLAY_ADS_PER_SOURCE = 120
MIN_DISPLAY_ADS_PER_SOURCE = 5
MAX_SEARCH_LIMIT = 120
MIN_SEARCH_LIMIT = 50

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute", "10/second"])

# Create FastAPI app
app = FastAPI(
    title="FindMyJobAI API",
    description="Backend API for job search with streaming",
    version="2.0.0"
)

# Disable rate limiting in test mode
if os.getenv("PYTEST_CURRENT_TEST"):
    # In test mode, don't add rate limiting middleware
    pass
else:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

# CORS middleware - Configuration permissive pour autoriser tous les domaines
# (Vercel, Netlify, etc.) sans restriction
logger.info("[CORS] Configured with allow_origins=['*'] (all domains allowed)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include cache routes
app.include_router(cache_router)

# Initialize cache service with Redis if configured
if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
    from app.services.cache import CacheService
    cache_service = CacheService(settings.REDIS_URL)
    logger.info(f"[CACHE] Initialized with Redis: {settings.REDIS_URL}")
else:
    logger.warning("[CACHE] No Redis configuration found, cache service will be limited")

# Initialize LLM service
llm_service.initialize_clients()
logger.info("[LLM] LLM service initialized with available providers")


# ─── Helper Functions ────────────────────────────────────────────────────────

def _generate_job_signature(job: dict) -> str:
    """Generate a stable signature for a job based on title + company + link.
    
    This utility function is used to identify duplicate jobs across sources.
    """
    title = (job.get("title") or job.get("titre") or "").lower().strip()
    company = (job.get("company") or job.get("entreprise") or "").lower().strip()
    link = (job.get("link") or job.get("lien") or "").lower().strip()
    return f"{title}|{company}|{link}"


def get_source_timeout(source: str) -> float:
    """Return timeout in seconds based on source type.

    Sources that involve multiple API calls, retries with exponential backoff,
    query relaxation variations, or sequential sub-scrapers need longer timeouts.
    """
    # Sources with retry/backoff + query relaxation need more time
    extended_timeout_sources = {
        "Adzuna": 30.0,        # 4 query variations × 3 retries with 1s/2s/4s backoff
        "Google Jobs": 30.0,   # 3 query variations × 3 retries with 2s/4s/8s backoff
        "JobSpy": 30.0,        # jobspy library scraping multiple sites with 3 variations
        "Enhanced": 10.0,     # ⏱️ Timeout strict : 10s max
        "Jooble": 20.0,        # API call with potential retries
        "Apify": 30.0,         # Apify LinkedIn scraper can be slow
    }
    return extended_timeout_sources.get(source, 15.0)


def log_source_diagnostic(source: str, status: str, detail: str = ""):
    """Log diagnostic for source execution."""
    status_map = {
        "timeout": "[TIMEOUT]",
        "auth_error": "[AUTH_ERROR]",
        "empty": "[EMPTY]",
        "success": "✅",
        "error": "❌",
    }
    prefix = status_map.get(status, "ℹ️")
    logger.info(f"{prefix} {source}: {detail}")


def _get_source_diagnostic_hint(source: str, error: str = "") -> str:
    """Return a human-readable diagnostic hint for a source that returned 0 results."""
    error_lower = (error or "").lower()
    
    # Quota / rate limit
    if "429" in error_lower or "quota" in error_lower or "rate limit" in error_lower:
        return "Quota API dépassé (HTTP 429). Attendez la réinitialisation du quota ou augmentez votre plan."
    
    # Auth errors
    if "401" in error_lower or "auth" in error_lower or "invalid" in error_lower:
        return "Clé API invalide ou expirée (HTTP 401). Vérifiez vos identifiants dans les variables d'environnement."
    
    # Forbidden
    if "403" in error_lower or "forbidden" in error_lower or "permission" in error_lower:
        return "Accès refusé (HTTP 403). Vérifiez les permissions de votre compte API."
    
    # Timeout
    if "timeout" in error_lower or "timed out" in error_lower:
        return "Timeout de la source. Le site/API met trop de temps à répondre. Réessayez ou réduisez le nombre de sources."
    
    # Source-specific hints
    source_lower = source.lower()
    if "adzuna" in source_lower:
        return "Vérifiez ADZUNA_APP_ID et ADZUNA_APP_KEY dans .env. Le quota gratuit est limité à 100 requêtes/jour."
    if "google" in source_lower:
        return "Vérifiez SERPAPI_KEY dans .env. Le plan gratuit SerpApi est limité à 100 recherches/mois."
    if "enhanced" in source_lower:
        return "La source Enhanced agrège Indeed, LinkedIn, Monster et HelloWork. Ces sites bloquent souvent les scrapers. Essayez de réduire le nombre de sources simultanées."
    if "jobspy" in source_lower:
        return "JobSpy scrape Indeed et Glassdoor. Ces sites peuvent bloquer les requêtes automatisées. Réessayez plus tard."
    if "linkedin" in source_lower:
        return "LinkedIn bloque agressivement les scrapers. Essayez la source 'LinkedIn (Apify)' avec une clé API Apify."
    if "indeed" in source_lower:
        return "Indeed bloque les scrapers avec des CAPTCHAs. Essayez la source JobSpy qui utilise une approche différente."
    if "france travail" in source_lower:
        return "Vérifiez FRANCE_TRAVAIL_CLIENT_ID et FRANCE_TRAVAIL_CLIENT_SECRET. Le scope 'o2dsoffre' est requis pour la recherche d'offres."
    if "jooble" in source_lower:
        return "Vérifiez JOOBLE_API_KEY dans .env."
    if "apify" in source_lower:
        return "Vérifiez APIFY_API_KEY dans .env. Le scraper LinkedIn d'Apify peut être lent ou nécessiter un quota."
    
    # Generic
    if not error:
        return "Aucun résultat trouvé pour cette requête. Essayez d'élargir la recherche ou de modifier la localisation."
    return f"Erreur: {error[:200]}"


# ─── Source Registry Builder ─────────────────────────────────────────────────

def build_source_registry(selected_sources: list, cv_data: Optional[dict] = None) -> dict:
    """
    Build a registry of sources to search.

    Args:
        selected_sources: List of source names
        cv_data: Optional CV data for AI scoring

    Returns:
        Dictionary of {source_name: callable}
    """
    source_registry = {}

    # API sources
    if "France Travail" in selected_sources:
        ft_source = get_france_travail_source()
        ft_rss_source = get_france_travail_rss_source()

        async def _search_france_travail_with_fallback(q: str, l: str, n: int):
            api_jobs = []
            if ft_source:
                try:
                    api_jobs = await ft_source.search_jobs(q, l, n)
                    if api_jobs:
                        logger.info(f"[SSE] France Travail API returned {len(api_jobs)} jobs")
                        return api_jobs
                except Exception as e:
                    logger.warning(f"[SSE] France Travail API failed, falling back to RSS: {e}")
            if ft_rss_source:
                try:
                    result = await ft_rss_source.search_jobs(q, l, n)
                    if result:
                        logger.info(f"[SSE] France Travail RSS returned {len(result)} jobs")
                        return result
                except Exception as e:
                    logger.error(f"[SSE] France Travail RSS fallback failed: {e}")
            return api_jobs

        source_registry['France Travail'] = _search_france_travail_with_fallback

    if "Adzuna" in selected_sources:
        adzuna_source = get_adzuna_source()
        if adzuna_source:
            async def _adzuna_search(q: str, l: str, n: int):
                try:
                    logger.info(f"[SSE] Adzuna search start query={q!r} location={l!r} limit={n}")
                    # ✅ CORRECTION: search_jobs est async, on l'await directement (pas asyncio.to_thread)
                    result = await adzuna_source.search_jobs(q, l, n)
                    logger.info(f"[SSE] Adzuna returned {len(result)} jobs")
                    # Attacher le diagnostic d'erreur aux résultats
                    if not result and adzuna_source.last_error:
                        logger.warning(f"[SSE] Adzuna diagnostic: {adzuna_source.last_error} - {adzuna_source.last_error_detail}")
                    return result
                except Exception as e:
                    logger.error(f"[SSE] Adzuna search error: {e}", exc_info=True)
                    return []
            source_registry['Adzuna'] = _adzuna_search

    # Web scrapers
    if "LinkedIn" in selected_sources:
        source_registry['LinkedIn'] = scrape_linkedin

    if "Indeed" in selected_sources:
        source_registry['Indeed'] = scrape_indeed

    if "Monster" in selected_sources:
        source_registry['Monster'] = scrape_monster

    if "HelloWork" in selected_sources:
        source_registry['HelloWork'] = scrape_hellowork

    if "Google Jobs" in selected_sources:
        async def _google_jobs_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] Google Jobs search start query={q!r} location={l!r} limit={n}")
                result = await scrape_google_jobs(q, l, n, settings.SERPAPI_KEY)
                logger.info(f"[SSE] Google Jobs returned {len(result)} jobs")
                # Attacher le diagnostic d'erreur aux résultats
                if not result:
                    gj_source = get_google_jobs_source()
                    if gj_source and gj_source.last_error:
                        logger.warning(f"[SSE] Google Jobs diagnostic: {gj_source.last_error} - {gj_source.last_error_detail}")
                return result
            except Exception as e:
                logger.error(f"[SSE] Google Jobs search error: {e}", exc_info=True)
                return []
        source_registry['Google Jobs'] = _google_jobs_search

    if "JobSpy" in selected_sources:
        async def _jobspy_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] JobSpy search start query={q!r} location={l!r} limit={n}")
                # ✅ CORRECTION: scrape_jobspy est synchrone, on utilise asyncio.to_thread
                result = await asyncio.to_thread(scrape_jobspy, q, l, n)
                logger.info(f"[SSE] JobSpy returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] JobSpy search error: {e}", exc_info=True)
                return []
        source_registry['JobSpy'] = _jobspy_search

    if "Enhanced" in selected_sources:
        async def _enhanced_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] Enhanced search start query={q!r} location={l!r} limit={n}")
                # ✅ CORRECTION: scrape_enhanced est synchrone, on utilise asyncio.to_thread correctement
                result = await asyncio.to_thread(scrape_enhanced, q, l, n)
                logger.info(f"[SSE] Enhanced returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] Enhanced search error: {e}", exc_info=True)
                return []
        source_registry['Enhanced'] = _enhanced_search

    if "Jooble" in selected_sources:
        jooble_source = get_jooble_source()
        if jooble_source:
            async def _jooble_search(q, l, n):
                # ✅ CORRECTION: search_jobs est async, on l'await directement
                return await jooble_source.search_jobs(q, l, n)
            source_registry['Jooble'] = _jooble_search

    if "Apify" in selected_sources:
        apify_source = get_apify_source()
        if apify_source:
            async def _apify_search(q, l, n):
                # ✅ CORRECTION: search_jobs est async, on l'await directement
                return await apify_source.search_jobs(q, l, n)
            source_registry['Apify'] = _apify_search

    if "Free-Work" in selected_sources:
        async def _free_work_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] Free-Work search start query={q!r} location={l!r} limit={n}")
                result = await scrape_free_work(q, l, n)
                logger.info(f"[SSE] Free-Work returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] Free-Work search error: {e}", exc_info=True)
                return []
        source_registry['Free-Work'] = _free_work_search

    if "Codeur.com" in selected_sources:
        async def _codeur_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] Codeur.com search start query={q!r} location={l!r} limit={n}")
                result = await scrape_codeur_com(q, l, n)
                logger.info(f"[SSE] Codeur.com returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] Codeur.com search error: {e}", exc_info=True)
                return []
        source_registry['Codeur.com'] = _codeur_search

    if "FreelanceRepublik" in selected_sources:
        async def _freelance_republik_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] FreelanceRepublik search start query={q!r} location={l!r} limit={n}")
                result = await scrape_freelance_republik(q, l, n)
                logger.info(f"[SSE] FreelanceRepublik returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] FreelanceRepublik search error: {e}", exc_info=True)
                return []
        source_registry['FreelanceRepublik'] = _freelance_republik_search

    if "Malt" in selected_sources:
        async def _malt_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] Malt search start query={q!r} location={l!r} limit={n}")
                from app.scrapers.freelance_sources import scrape_malt
                result = await scrape_malt(q, l, n)
                logger.info(f"[SSE] Malt returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] Malt search error: {e}", exc_info=True)
                return []
        source_registry['Malt'] = _malt_search

    if "UpworkRSS" in selected_sources:
        async def _upwork_rss_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] UpworkRSS search start query={q!r} location={l!r} limit={n}")
                from app.scrapers.freelance_sources import scrape_upwork_rss
                result = await scrape_upwork_rss(query=q, location=l, limit=n)
                logger.info(f"[SSE] UpworkRSS returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] UpworkRSS search error: {e}", exc_info=True)
                return []
        source_registry['UpworkRSS'] = _upwork_rss_search

    if "WeWorkRemotelyRSS" in selected_sources:
        async def _wwr_rss_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] WeWorkRemotelyRSS search start query={q!r} location={l!r} limit={n}")
                from app.scrapers.freelance_sources import scrape_wwr_rss
                result = await scrape_wwr_rss(category=q, query=l, limit=n)
                logger.info(f"[SSE] WeWorkRemotelyRSS returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] WeWorkRemotelyRSS search error: {e}", exc_info=True)
                return []
        source_registry['WeWorkRemotelyRSS'] = _wwr_rss_search

    if "RemoteOK" in selected_sources:
        async def _remoteok_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] RemoteOK search start query={q!r} location={l!r} limit={n}")
                from app.scrapers.freelance_sources import scrape_remoteok_api
                result = await scrape_remoteok_api(query=q, location=l, limit=n)
                logger.info(f"[SSE] RemoteOK returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] RemoteOK search error: {e}", exc_info=True)
                return []
        source_registry['RemoteOK'] = _remoteok_search

    if "Freelancer.com" in selected_sources:
        async def _freelancer_com_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] Freelancer.com search start query={q!r} location={l!r} limit={n}")
                from app.scrapers.freelance_sources import scrape_freelancer_com
                result = await scrape_freelancer_com(query=q, location=l, limit=n)
                logger.info(f"[SSE] Freelancer.com returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] Freelancer.com search error: {e}", exc_info=True)
                return []
        source_registry['Freelancer.com'] = _freelancer_com_search

    if "GitHub" in selected_sources:
        async def _github_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] GitHub search start query={q!r} location={l!r} limit={n}")
                result = await asyncio.to_thread(_scrape_github, q, l, n)
                logger.info(f"[SSE] GitHub returned {len(result)} candidates")
                return result
            except Exception as e:
                logger.error(f"[SSE] GitHub search error: {e}", exc_info=True)
                return []
        source_registry['GitHub'] = _github_search

    if "StackOverflow" in selected_sources:
        async def _stackoverflow_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] StackOverflow search start query={q!r} location={l!r} limit={n}")
                result = await asyncio.to_thread(_scrape_stackoverflow, q, l, n)
                logger.info(f"[SSE] StackOverflow returned {len(result)} candidates")
                return result
            except Exception as e:
                logger.error(f"[SSE] StackOverflow search error: {e}", exc_info=True)
                return []
        source_registry['StackOverflow'] = _stackoverflow_search

    if "LinkedIn" in selected_sources:
        async def _linkedin_xray_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] LinkedIn X-Ray search start query={q!r} location={l!r} limit={n}")
                result = await asyncio.to_thread(_scrape_linkedin_xray, q, l, n)
                logger.info(f"[SSE] LinkedIn X-Ray returned {len(result)} candidates")
                return result
            except Exception as e:
                logger.error(f"[SSE] LinkedIn X-Ray search error: {e}", exc_info=True)
                return []
        source_registry['LinkedIn'] = _linkedin_xray_search

    return source_registry


def _scrape_free_work(query: str, location: str, limit: int) -> list:
    """Scrape Free-Work for freelance IT candidates."""
    import urllib.parse

    candidates = []

    # Method 1: X-Ray Google via SerpApi
    serp_query = f'site:free-work.com/fr/tech-it/freelancers "{query}" "{location}" "Disponible"'
    logger.info(f"[FREE-WORK] X-Ray query: {serp_query}")

    try:
        serp_params = {
            "q": serp_query,
            "num": min(limit, 10),
            "hl": "fr",
            "gl": "fr",
        }
        if settings.SERPAPI_KEY:
            serp_params["api_key"] = settings.SERPAPI_KEY

        import requests as req_lib
        response = req_lib.get(
            "https://serpapi.com/search",
            params=serp_params,
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            organic_results = data.get("organic_results", [])
            for result in organic_results:
                link = result.get("link", "")
                title = result.get("title", "")
                snippet = result.get("snippet", "")

                candidate = {
                    "worker_id": f"freework_{hash(link)}",
                    "full_name": _extract_name_from_title(title),
                    "headline_title": title,
                    "target_contract": "FREELANCE",
                    "skills": _extract_skills_from_text(snippet + " " + title),
                    "location": location,
                    "tjm_or_rate": None,
                    "availability": "Disponible",
                    "source_platform": "Free-Work",
                    "profile_url": link,
                }
                candidates.append(candidate)
    except Exception as e:
        logger.warning(f"[FREE-WORK] SerpApi X-Ray failed: {e}")

    # Method 2: Direct HTML scraping
    try:
        encoded_query = urllib.parse.quote(query)
        encoded_location = urllib.parse.quote(location)
        url = f"https://www.free-work.com/fr/tech-it/freelancers?query={encoded_query}&locations={encoded_location}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9",
        }

        response = req_lib.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            cards = soup.find_all("div", class_=lambda c: c and ("freelancer" in c.lower() or "profile" in c.lower() or "candidate" in c.lower()))
            if not cards:
                cards = soup.find_all("a", href=lambda h: h and "/fr/tech-it/freelancers/" in h)

            for card in cards[:limit]:
                name = card.get_text(strip=True) or card.get("title", "")
                href = card.get("href", "")
                if not href.startswith("http"):
                    href = f"https://www.free-work.com{href}"

                candidate = {
                    "worker_id": f"freework_{hash(href)}",
                    "full_name": name,
                    "headline_title": name,
                    "target_contract": "FREELANCE",
                    "skills": _extract_skills_from_text(name),
                    "location": location,
                    "tjm_or_rate": None,
                    "availability": "",
                    "source_platform": "Free-Work",
                    "profile_url": href,
                }
                candidates.append(candidate)
    except Exception as e:
        logger.warning(f"[FREE-WORK] HTML scraping failed: {e}")

    return candidates


def _scrape_malt(query: str, location: str, limit: int) -> list:
    """Scrape Malt for freelance IT candidates.

    Uses SerpApi X-Ray Google search and direct HTML scraping.
    """
    import urllib.parse

    candidates = []

    # Method 1: X-Ray Google via SerpApi
    serp_query = f'site:malt.fr "{query}" "{location}" freelance'
    logger.info(f"[MALT] X-Ray query: {serp_query}")

    try:
        serp_params = {
            "q": serp_query,
            "num": min(limit, 10),
            "hl": "fr",
            "gl": "fr",
        }
        if settings.SERPAPI_KEY:
            serp_params["api_key"] = settings.SERPAPI_KEY

        import requests as req_lib
        response = req_lib.get(
            "https://serpapi.com/search",
            params=serp_params,
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            organic_results = data.get("organic_results", [])
            for result in organic_results:
                link = result.get("link", "")
                title = result.get("title", "")
                snippet = result.get("snippet", "")

                candidate = {
                    "worker_id": f"malt_{hash(link)}",
                    "full_name": _extract_name_from_title(title),
                    "headline_title": title,
                    "target_contract": "FREELANCE",
                    "skills": _extract_skills_from_text(snippet + " " + title),
                    "location": location,
                    "tjm_or_rate": _extract_tjm(snippet),
                    "availability": "Disponible",
                    "source_platform": "Malt",
                    "profile_url": link,
                }
                candidates.append(candidate)
    except Exception as e:
        logger.warning(f"[MALT] SerpApi X-Ray failed: {e}")

    # Method 2: Direct HTML scraping
    try:
        encoded_query = urllib.parse.quote(query)
        encoded_location = urllib.parse.quote(location)
        url = f"https://www.malt.fr/search/results?query={encoded_query}&location={encoded_location}&contract_type=freelance"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9",
        }

        response = req_lib.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            cards = soup.find_all("div", class_=lambda c: c and ("profile" in c.lower() or "freelance" in c.lower() or "candidate" in c.lower()))
            if not cards:
                cards = soup.find_all("a", href=lambda h: h and "/fr/" in h and "malt" in h)

            for card in cards[:limit]:
                name = card.get_text(strip=True) or card.get("title", "")
                href = card.get("href", "")
                if not href.startswith("http"):
                    href = f"https://www.malt.fr{href}"

                candidate = {
                    "worker_id": f"malt_{hash(href)}",
                    "full_name": name,
                    "headline_title": name,
                    "target_contract": "FREELANCE",
                    "skills": _extract_skills_from_text(name),
                    "location": location,
                    "tjm_or_rate": None,
                    "availability": "",
                    "source_platform": "Malt",
                    "profile_url": href,
                }
                candidates.append(candidate)
    except Exception as e:
        logger.warning(f"[MALT] HTML scraping failed: {e}")

    return candidates


def _scrape_linkedin_xray(query: str, location: str, limit: int) -> list:
    """Scrape LinkedIn for candidates using X-Ray Google search."""
    import urllib.parse

    candidates = []

    # Freelance X-Ray
    serp_query = f'site:linkedin.com/in/ ("freelance" OR "indépendant" OR "consultant") "{query}" "{location}"'
    logger.info(f"[LINKEDIN-XRAY] Freelance query: {serp_query}")

    try:
        serp_params = {
            "q": serp_query,
            "num": min(limit, 10),
            "hl": "fr",
            "gl": "fr",
        }
        if settings.SERPAPI_KEY:
            serp_params["api_key"] = settings.SERPAPI_KEY

        import requests as req_lib
        response = req_lib.get(
            "https://serpapi.com/search",
            params=serp_params,
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            organic_results = data.get("organic_results", [])
            for result in organic_results:
                link = result.get("link", "")
                title = result.get("title", "")
                snippet = result.get("snippet", "")

                target_contract = "FREELANCE" if "freelance" in snippet.lower() or "indépendant" in snippet.lower() else "MIXTE"

                candidate = {
                    "worker_id": f"linkedin_{hash(link)}",
                    "full_name": _extract_name_from_title(title),
                    "headline_title": title,
                    "target_contract": target_contract,
                    "skills": _extract_skills_from_text(snippet + " " + title),
                    "location": location,
                    "tjm_or_rate": None,
                    "availability": "Open to Work" if "open to work" in snippet.lower() else "",
                    "source_platform": "LinkedIn",
                    "profile_url": link,
                }
                candidates.append(candidate)
    except Exception as e:
        logger.warning(f"[LINKEDIN-XRAY] SerpApi failed: {e}")

    # CDD X-Ray
    cdd_query = f'site:linkedin.com/in/ ("CDD" OR "recherche CDD" OR "disponible immédiatement") "{query}" "{location}"'
    logger.info(f"[LINKEDIN-XRAY] CDD query: {cdd_query}")

    try:
        serp_params = {
            "q": cdd_query,
            "num": min(limit, 10),
            "hl": "fr",
            "gl": "fr",
        }
        if settings.SERPAPI_KEY:
            serp_params["api_key"] = settings.SERPAPI_KEY

        import requests as req_lib
        response = req_lib.get(
            "https://serpapi.com/search",
            params=serp_params,
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            organic_results = data.get("organic_results", [])
            for result in organic_results:
                link = result.get("link", "")
                title = result.get("title", "")
                snippet = result.get("snippet", "")

                candidate = {
                    "worker_id": f"linkedin_cdd_{hash(link)}",
                    "full_name": _extract_name_from_title(title),
                    "headline_title": title,
                    "target_contract": "CDD",
                    "skills": _extract_skills_from_text(snippet + " " + title),
                    "location": location,
                    "tjm_or_rate": None,
                    "availability": "Disponible immédiatement",
                    "source_platform": "LinkedIn",
                    "profile_url": link,
                }
                candidates.append(candidate)
    except Exception as e:
        logger.warning(f"[LINKEDIN-XRAY] CDD SerpApi failed: {e}")

    return candidates


def _scrape_france_travail_candidates(query: str, location: str, limit: int) -> list:
    """Scrape France Travail Banque de CV for CDD candidates."""
    candidates = []

    try:
        import requests as req_lib
        # France Travail Banque de CV API
        url = "https://api.francetravail.io/partenaire/banquedecv/v1/candidats"
        params = {
            "motsCles": query,
            "localisation": location,
            "typeContratRequested": "CDD",
            "range": f"0-{limit}",
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        response = req_lib.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("resultats", data.get("candidates", data.get("data", [])))
            for result in results:
                candidate = {
                    "worker_id": f"ft_{result.get('id', hash(result.get('nom', '')))}",
                    "full_name": result.get("nom", result.get("name", "")),
                    "headline_title": result.get("metier", result.get("title", "")),
                    "target_contract": "CDD",
                    "skills": result.get("competences", result.get("skills", [])),
                    "location": result.get("localisation", result.get("location", location)),
                    "tjm_or_rate": None,
                    "availability": result.get("disponibilite", "Immédiate"),
                    "source_platform": "France Travail",
                    "profile_url": result.get("url", result.get("profile_url", "")),
                }
                candidates.append(candidate)
    except Exception as e:
        logger.warning(f"[FRANCE-TRAVAIL] API failed: {e}")

    return candidates


def _scrape_github(query: str, location: str, limit: int) -> list:
    """Scrape GitHub for tech candidates."""
    candidates = []

    try:
        import requests as req_lib
        # GitHub user search by location and skills
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.github.com/search/users?q={encoded_query}+location:{location}&per_page={limit}"

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FindMyWorker-Agent",
        }

        response = req_lib.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            for item in items:
                candidate = {
                    "worker_id": f"github_{item.get('id', '')}",
                    "full_name": item.get("login", ""),
                    "headline_title": f"Developer - {item.get('login', '')}",
                    "target_contract": "MIXTE",
                    "skills": [query],
                    "location": location,
                    "tjm_or_rate": None,
                    "availability": "",
                    "source_platform": "GitHub",
                    "profile_url": item.get("html_url", ""),
                }
                candidates.append(candidate)
    except Exception as e:
        logger.warning(f"[GITHUB] API failed: {e}")

    return candidates


def _scrape_stackoverflow(query: str, location: str, limit: int) -> list:
    """Scrape StackOverflow for tech candidates."""
    candidates = []

    try:
        import requests as req_lib
        # StackOverflow user search
        url = "https://api.stackexchange.com/2.3/users"
        params = {
            "order": "desc",
            "sort": "reputation",
            "site": "stackoverflow",
            "pagesize": limit,
            "filter": "display_name,location,reputation,link",
        }

        response = req_lib.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            for item in items:
                location_match = location.lower() in (item.get("location") or "").lower()
                if location_match or not location:
                    candidate = {
                        "worker_id": f"so_{item.get('user_id', '')}",
                        "full_name": item.get("display_name", ""),
                        "headline_title": f"Developer - StackOverflow",
                        "target_contract": "MIXTE",
                        "skills": [query],
                        "location": item.get("location", location),
                        "tjm_or_rate": None,
                        "availability": "",
                        "source_platform": "StackOverflow",
                        "profile_url": item.get("link", ""),
                    }
                    candidates.append(candidate)
    except Exception as e:
        logger.warning(f"[STACKOVERFLOW] API failed: {e}")

    return candidates


def _extract_tjm(text: str) -> str:
    """Extract TJM rate from text."""
    import re
    if not text:
        return None
    patterns = [
        r'(\d+)\s*€\s*/\s*j',
        r'TJM\s*:?\s*(\d+)\s*€',
        r'taux\s*journalier\s*:?\s*(\d+)\s*€',
        r'(\d+)\s*euros\s*/\s*jour',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return f"{match.group(1)}€/j"
    return None


def _extract_name_from_title(title: str) -> str:
    """Extract candidate name from a search result title."""
    if not title:
        return ""
    cleaned = title
    for prefix in ["Freelance ", "Consultant ", "Développeur ", "Développeuse ", "Dev ", "Developer "]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    return cleaned.strip()


def _extract_skills_from_text(text: str) -> list:
    """Extract technical skills from text."""
    if not text:
        return []
    common_skills = [
        "React", "Vue", "Angular", "TypeScript", "JavaScript", "Python", "Java",
        "Node.js", "Node", "Django", "Flask", "FastAPI", "Spring", "Laravel",
        "Ruby", "Go", "Rust", "PHP", "C#", ".NET", "React Native", "Flutter",
        "Swift", "Kotlin", "Docker", "Kubernetes", "AWS", "Azure", "GCP",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "GraphQL", "REST API",
        "Git", "CI/CD", "Agile", "Scrum", "Microservices", "DevOps",
        "UI/UX", "Design", "Marketing", "Data", "Machine Learning", "AI",
        "SEO", "Content", "Rédaction", "Communication", "Management",
    ]
    text_lower = text.lower()
    skills = []
    for skill in common_skills:
        if skill.lower() in text_lower:
            skills.append(skill)
    return skills[:10]


# ─── Main Streaming Endpoint ─────────────────────────────────────────────────

@app.get("/api/jobs/stream")
async def api_jobs_stream(
    request: Request,
    query: str = Query(...),
    location: str = Query("Paris, France"),
    num_ads: str = Query("10"),
    contract: str = Query("CDI"),
    remote: bool = Query(False),
    selected_sources: str = Query(""),
    ranking_engine: str = Query("Groq / Llama 3.3"),
    custom_gemini_key: str = Query(None),
    cv_data: str = Query(None),
    agent_type: str = Query("job"),
    no_ai_mode: bool = Query(False),
):
    """Stream job search results using Server-Sent Events (SSE)."""
    return await _stream_jobs(
        query=query,
        location=location,
        num_ads=num_ads,
        contract=contract,
        remote=remote,
        selected_sources=selected_sources,
        ranking_engine=ranking_engine,
        custom_gemini_key=custom_gemini_key,
        cv_data=cv_data,
        agent_type=agent_type,
        no_ai_mode=no_ai_mode,
    )


@app.get("/api/search-jobs-stream")
async def legacy_api_search_jobs_stream(
    request: Request,
    query: str = Query(...),
    location: str = Query("Paris, France"),
    num_ads: str = Query("10"),
    contract: str = Query("CDI"),
    remote: bool = Query(False),
    selected_sources: str = Query(""),
    ranking_engine: str = Query("Groq / Llama 3.3"),
    custom_gemini_key: str = Query(None),
    cv_data: str = Query(None),
    global_search: str = Query("false"),
    sort_option: str = Query("Pertinence (IA)"),
    lang_code: str = Query("fr"),
    lang_label: str = Query("français"),
    agent_type: str = Query("job"),
    no_ai_mode: bool = Query(False),
):
    """⚠️ LEGACY ROUTE - Compatibility route for the legacy frontend.
    
    TODO: Remove this route once all frontend clients migrate to /api/jobs/stream
    """
    logger.info(f"[COMPAT] /api/search-jobs-stream called, forwarding to /api/jobs/stream")
    return await _stream_jobs(
        query=query,
        location=location,
        num_ads=num_ads,
        contract=contract,
        remote=remote,
        selected_sources=selected_sources,
        ranking_engine=ranking_engine,
        custom_gemini_key=custom_gemini_key,
        cv_data=cv_data,
        agent_type=agent_type,
        no_ai_mode=no_ai_mode,
    )


@app.post("/api/search-jobs")
async def post_search_jobs(request: Request):
    """POST endpoint for job search (used by FreelanceMissionApp and WorkerApp)."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    query = body.get("query", "")
    location = body.get("location", "France")
    num_ads = body.get("num_ads", 10)
    contract = body.get("contract", "CDI")
    remote = body.get("remote", False)
    selected_sources = body.get("selected_sources", "")
    ranking_engine = body.get("ranking_engine", "Groq / Llama 3.3")
    custom_gemini_key = body.get("custom_gemini_key")
    cv_data = body.get("cv_data")
    agent_type = body.get("agent_type", "job")
    no_ai_mode = body.get("no_ai_mode", False)
    if isinstance(selected_sources, list):
        selected_sources = ",".join(selected_sources)
    if selected_sources == "":
        if contract == "Freelance":
            selected_sources = "Indeed,LinkedIn,Monster,Google Jobs,JobSpy"
        else:
            selected_sources = "LinkedIn,Indeed,France Travail,Apec,Monster"
    logger.info(f"[POST /api/search-jobs] query={query!r} sources={selected_sources} agent_type={agent_type} no_ai_mode={no_ai_mode}")
    return await _stream_jobs(
        query=query,
        location=location,
        num_ads=num_ads,
        contract=contract,
        remote=remote,
        selected_sources=selected_sources,
        ranking_engine=ranking_engine,
        custom_gemini_key=custom_gemini_key,
        cv_data=cv_data,
        agent_type=agent_type,
        no_ai_mode=no_ai_mode,
    )


async def _stream_jobs(
    query: str,
    location: str,
    num_ads: str,
    contract: str,
    remote: bool,
    selected_sources: str,
    ranking_engine: str,
    custom_gemini_key: Optional[str],
    cv_data: Optional[str],
    agent_type: str = "job",
    no_ai_mode: bool = False,
):
    sources_list = [s.strip() for s in selected_sources.split(",") if s.strip()]
    cv_data_dict = None
    if cv_data:
        try:
            cv_data_dict = json.loads(cv_data)
        except Exception:
            pass

    # Handle num_ads: support "Max" for unlimited display per source, or numeric value
    if isinstance(num_ads, str) and num_ads.lower() == "max":
        display_limit = MAX_DISPLAY_ADS_PER_SOURCE
    else:
        parsed_num_ads = int(num_ads) if isinstance(num_ads, str) else num_ads
        display_limit = max(MIN_DISPLAY_ADS_PER_SOURCE, min(parsed_num_ads, MAX_DISPLAY_ADS_PER_SOURCE))

    # Always search with a high limit to get maximum results per source
    search_limit = MAX_SEARCH_LIMIT

    async def event_generator():
        try:
            logger.info(f"[SSE] START query={query!r} location={location!r} sources={sources_list} ranking={ranking_engine} agent_type={agent_type} no_ai_mode={no_ai_mode}")
            source_registry = build_source_registry(sources_list, cv_data_dict)
            total_sources = len(source_registry)
            logger.info(f"[SSE] registry={total_sources} built from requested={sources_list}")
            yield f"data: {json.dumps({'type': 'STARTED', 'query': query, 'total_sources': total_sources})}\n\n"
            await asyncio.sleep(0)

            if total_sources == 0:
                logger.warning("[SSE] no source available")
                yield f"data: {json.dumps({'type': 'COMPLETED', 'jobs': [], 'source_status': {}, 'progress': 100})}\n\n"
                return

            aggregator = SearchAggregator(
                max_workers=settings.SCRAPER_MAX_WORKERS,
                timeout_per_source=settings.SCRAPER_TIMEOUT,
            )
            logger.info(f"[SSE] searching sources={sources_list}")

            # All sources are always queried; no early termination based on job count
            target_total = 0
            total_sources = len(source_registry)
            sources_done = 0
            all_jobs = []
            source_results = {}
            emit_count = 0
            scored_jobs_map = {}  # signature -> scored job (for COMPLETED event)

            source_timeouts = {name: get_source_timeout(name) for name in source_registry}
            source_limits = {name: get_optimal_limit(search_limit, name) for name in source_registry}
            emitted_counts = {}
            async for result in aggregator.search_parallel_streaming(
                sources=source_registry,
                query=query,
                location=location,
                limit=search_limit,
                target_jobs=target_total,
                source_timeouts=source_timeouts,
                source_limits=source_limits,
            ):
                # Accumulate all jobs per source (support partial batches)
                if result.jobs:
                    all_jobs.extend(result.jobs)

                # Merge into source_results: append jobs and update status
                prev = source_results.get(result.source_name)
                if prev:
                    prev.jobs = (prev.jobs or []) + (result.jobs or [])
                    prev.success = prev.success and result.success
                    prev.execution_time = round((prev.execution_time or 0) + (result.execution_time or 0), 2)
                else:
                    source_results[result.source_name] = result

                # Only count source as done when result.done is True
                if getattr(result, 'done', True):
                    sources_done += 1

                status = "completed" if result.success and getattr(result, 'done', True) else ("streaming" if getattr(result, 'is_partial', False) else "error")
                jobs_count = len(result.jobs) if result.jobs else 0
                progress = min(100, int(sources_done / total_sources * 100)) if total_sources > 0 else 100
                source_progress = min(100, int(sources_done / total_sources * 100)) if total_sources > 0 else 100

                logger.info(
                    f"[SSE] source={result.source_name} status={status} jobs={jobs_count} duration={result.execution_time} error={result.error} progress={progress} sources_done={sources_done}/{total_sources}"
                )

                if result.jobs and jobs_count > 0:
                    logger.info(f"[SSE] source={result.source_name} sample_job={result.jobs[0].get('titre', 'N/A')}")

                # Build diagnostic info for sources that returned 0 jobs
                diagnostic = None
                if jobs_count == 0 and not result.success:
                    diagnostic = {
                        "source": result.source_name,
                        "error": result.error or "Aucun résultat",
                        "hint": _get_source_diagnostic_hint(result.source_name, result.error),
                    }
                elif jobs_count == 0 and result.success:
                    diagnostic = {
                        "source": result.source_name,
                        "error": "Aucun résultat trouvé",
                        "hint": _get_source_diagnostic_hint(result.source_name, ""),
                    }

                # Limit emitted jobs per source to display_limit
                jobs_to_emit = result.jobs or []
                if display_limit <= MAX_DISPLAY_ADS_PER_SOURCE:
                    emitted_so_far = emitted_counts.get(result.source_name, 0)
                    remaining = display_limit - emitted_so_far
                    if remaining <= 0:
                        jobs_to_emit = []
                    else:
                        jobs_to_emit = (result.jobs or [])[:remaining]
                        emitted_counts[result.source_name] = emitted_so_far + len(jobs_to_emit)

                # Send PROGRESS event for partial or final batches
                source_result = source_results.get(result.source_name)
                total_found_by_source = len(source_result.jobs) if source_result and source_result.jobs else 0
                yield f"data: {json.dumps({'type': 'SOURCE_RESULT', 'progress': progress, 'total_so_far': len(all_jobs), 'target': display_limit, 'source': result.source_name, 'status': status, 'jobs': jobs_to_emit, 'sources_done': sources_done, 'total_sources': total_sources, 'source_progress': source_progress, 'execution_time': result.execution_time, 'is_partial': getattr(result, 'is_partial', False), 'fallback': getattr(result, 'fallback', False), 'diagnostic': diagnostic, 'total_found_by_source': total_found_by_source})}\n\n"
                emit_count += 1
                await asyncio.sleep(0)

                # Score ONLY the new batch from this source (not all accumulated jobs)
                # DÉSACTIVÉ en Mode Sans IA (no_ai_mode)
                if result.jobs and cv_data_dict and not no_ai_mode:
                    try:
                        new_batch = result.jobs
                        job_chunks = [new_batch] if len(new_batch) <= 20 else [new_batch[i:i+20] for i in range(0, len(new_batch), 20)]
                        scored_jobs = []
                        for chunk in job_chunks:
                            scored = score_jobs(cv_data_dict, chunk, fast=True)
                            scored_jobs.extend(scored)
                        scored_jobs.sort(key=lambda x: x.get('pertinence_ai', 0), reverse=True)

                        # Update the scored jobs map for the COMPLETED event
                        for job in scored_jobs:
                            sig = _generate_job_signature(job)
                            scored_jobs_map[sig] = job

                        yield f"data: {json.dumps({'type': 'SCORES_UPDATED', 'jobs': scored_jobs, 'progress': progress})}\n\n"
                    except Exception as e:
                        logger.error(f"[SSE] Progressive AI scoring failed: {e}")
                        yield f"data: {json.dumps({'type': 'SCORES_UPDATED', 'jobs': [], 'progress': progress})}\n\n"

            # Emit COMPLETED event with all accumulated jobs and source status
            source_status = {}
            for sname, sresult in source_results.items():
                source_status[sname] = {
                    "success": sresult.success,
                    "count": len(sresult.jobs) if sresult.jobs else 0,
                    "status": "completed" if sresult.success else "error",
                    "error": sresult.error,
                    "execution_time": sresult.execution_time,
                    "diagnostic": _get_source_diagnostic_hint(sname, sresult.error) if (not sresult.success or (sresult.jobs is None or len(sresult.jobs) == 0)) else None,
                }

            # Build final jobs list with scores (if CV data was provided)
            if cv_data_dict and scored_jobs_map:
                final_jobs = []
                for job in all_jobs:
                    sig = _generate_job_signature(job)
                    if sig in scored_jobs_map:
                        final_jobs.append(scored_jobs_map[sig])
                    else:
                        final_jobs.append(job)
                final_jobs.sort(key=lambda x: x.get('pertinence_ai', 0), reverse=True)
            else:
                final_jobs = all_jobs

            # Normalize all jobs for frontend
            normalized_jobs = normalize_jobs_for_frontend(final_jobs)

            # Limit displayed results per source to display_limit
            if display_limit <= MAX_DISPLAY_ADS_PER_SOURCE:
                limited_jobs = []
                source_display_counts = {}
                for job in normalized_jobs:
                    job_source = job.get('source', '')
                    source_display_counts[job_source] = source_display_counts.get(job_source, 0) + 1
                    if source_display_counts[job_source] <= display_limit:
                        limited_jobs.append(job)
                normalized_jobs = limited_jobs

            yield f"data: {json.dumps({'type': 'COMPLETED', 'jobs': normalized_jobs, 'source_status': source_status, 'progress': 100, 'total_jobs': len(all_jobs)})}\n\n"
            await asyncio.sleep(0)
        except Exception as e:
            logger.exception("[SSE] GLOBAL_ERROR")
            yield f"data: {json.dumps({'type': 'ERROR', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── AI Models Status ─────────────────────────────────────────────────────────

@app.get("/api/ai/status")
async def ai_status(custom_gemini_key: Optional[str] = Query(None)):
    """Check real connectivity of AI models using the same provider calls as the app."""
    logger.info("[AI_STATUS] Starting AI models connectivity check...")

    groq_key = (settings.GROQ_API_KEY or "").strip()
    gemini_key = (custom_gemini_key or settings.GEMINI_API_KEY or "").strip()
    ollama_url = (settings.OLLAMA_URL or "").strip()

    logger.info(f"[AI_STATUS] GROQ key present: {bool(groq_key)}")
    logger.info(f"[AI_STATUS] GEMINI key present: {bool(gemini_key)}")
    logger.info(f"[AI_STATUS] OLLAMA url: {ollama_url}")

    groq_ok = False
    gemini_ok = False
    ollama_ok = False
    groq_error = None
    gemini_error = None
    ollama_error = None

    if groq_key:
        try:
            logger.info("[AI_STATUS] Testing Groq connectivity...")
            text = await asyncio.to_thread(
                call_ai_provider,
                prompt="ping",
                selected_model="Groq / Llama 3.3",
                is_json=False,
                groq_api_key=groq_key,
            )
            if text:
                groq_ok = True
                logger.info("[AI_STATUS] Groq OK")
            else:
                groq_error = "Empty response"
                logger.error("[AI_STATUS] Groq error: empty response")
        except Exception as e:
            groq_error = str(e)
            logger.error(f"[AI_STATUS] Groq exception: {groq_error}")
    else:
        logger.warning("[AI_STATUS] Groq skipped: no API key")

    active_gemini_key = gemini_key
    if active_gemini_key:
        try:
            logger.info("[AI_STATUS] Testing Gemini connectivity...")
            text = await asyncio.to_thread(
                call_ai_provider,
                prompt="ping",
                selected_model="Gemini 3.5",
                is_json=False,
                gemini_api_key=active_gemini_key,
            )
            if text:
                gemini_ok = True
                logger.info("[AI_STATUS] Gemini OK")
            else:
                gemini_error = "Empty response"
                logger.error("[AI_STATUS] Gemini error: empty response")
        except Exception as e:
            gemini_error = str(e)
            logger.error(f"[AI_STATUS] Gemini exception: {gemini_error}")
    else:
        logger.warning("[AI_STATUS] Gemini skipped: no API key")

    if ollama_url:
        try:
            logger.info(f"[AI_STATUS] Testing Ollama connectivity at {ollama_url}/api/generate...")
            text = await asyncio.to_thread(
                call_ai_provider,
                prompt="ping",
                selected_model="Llama 3.2 (Local/dev)",
                is_json=False,
                ollama_url=ollama_url,
            )
            if text:
                ollama_ok = True
                logger.info("[AI_STATUS] Ollama OK")
            else:
                ollama_error = "Empty response"
                logger.error("[AI_STATUS] Ollama error: empty response")
        except Exception as e:
            ollama_error = str(e)
            logger.error(f"[AI_STATUS] Ollama exception: {ollama_error}")
    else:
        logger.warning("[AI_STATUS] Ollama skipped: no URL configured")

    result = {
        "groq": {
            "configured": bool(groq_key),
            "online": groq_ok,
            "error": groq_error,
        },
        "gemini": {
            "configured": bool(gemini_key),
            "online": gemini_ok,
            "error": gemini_error,
        },
        "ollama": {
            "configured": bool(ollama_url),
            "online": ollama_ok,
            "error": ollama_error,
        },
    }
    logger.info(f"[AI_STATUS] Final result: {result}")
    return result


# ─── Unified AI Call Endpoint ──────────────────────────────────────────────────

@app.post("/api/ai/call")
async def ai_call(request: Request):
    """Unified AI call endpoint for all providers."""
    try:
        body = await request.json()
        prompt = body.get("prompt", "")
        model = body.get("model", "Groq / Llama 3.3 70B")
        provider = body.get("provider", "groq")
        model_name = body.get("modelName")
        api_key = body.get("apiKey")
        is_json = body.get("isJson", False)
        temperature = body.get("temperature", 0.3)
        max_tokens = body.get("maxTokens", 4096)

        if not prompt:
            return {"error": "Prompt is required"}

        # Map provider to the correct API key parameter
        kwargs = {
            "prompt": prompt,
            "selected_model": model,
            "is_json": is_json,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Add the appropriate API key based on provider
        if provider == "groq":
            groq_key = api_key or (settings.GROQ_API_KEY or "").strip()
            if not groq_key:
                return {"error": "Groq API key is required"}
            kwargs["groq_api_key"] = groq_key
        elif provider == "gemini":
            gemini_key = api_key or (settings.GEMINI_API_KEY or "").strip()
            if not gemini_key:
                return {"error": "Gemini API key is required"}
            kwargs["gemini_api_key"] = gemini_key
        elif provider == "openai":
            openai_key = api_key or (settings.OPENAI_API_KEY or "").strip()
            if not openai_key:
                return {"error": "OpenAI API key is required"}
            kwargs["openai_api_key"] = openai_key
        elif provider == "anthropic":
            anthropic_key = api_key or (settings.ANTHROPIC_API_KEY or "").strip()
            if not anthropic_key:
                return {"error": "Anthropic API key is required"}
            kwargs["anthropic_api_key"] = anthropic_key
        elif provider == "deepseek":
            deepseek_key = api_key or (settings.DEEPSEEK_API_KEY or "").strip()
            if not deepseek_key:
                return {"error": "DeepSeek API key is required"}
            kwargs["deepseek_api_key"] = deepseek_key
        elif provider == "mistral":
            mistral_key = api_key or (settings.MISTRAL_API_KEY or "").strip()
            if not mistral_key:
                return {"error": "Mistral API key is required"}
            kwargs["mistral_api_key"] = mistral_key
        else:
            return {"error": f"Unsupported provider: {provider}"}

        # Call the AI provider
        text = await asyncio.to_thread(
            call_ai_provider,
            **kwargs
        )

        return {"text": text}

    except Exception as e:
        logger.error(f"[AI_CALL] Error: {str(e)}")
        return {"error": str(e)}


# ─── AI Copilot Chat Endpoint ─────────────────────────────────────────────────

@app.post("/api/chat")
async def ai_copilot_chat(request: Request):
    """Context-Aware AI Copilot chat endpoint.

    Accepts a JSON body with `message` and `context` (agent_type, system_status,
    user_profile, displayed_jobs_summary).

    Reads user API keys from HTTP headers (never from the body):
    - X-User-Gemini-Key: User's personal Gemini API key
    - X-User-Groq-Key: User's personal Groq API key

    Fallback priority: User Gemini > User Groq > Server Groq > Support Alert.
    """
    try:
        body = await request.json()
    except Exception:
        return {"error": "Invalid JSON body"}

    # Read API keys from HTTP headers (security: never in body)
    user_gemini_key = (request.headers.get("X-User-Gemini-Key") or "").strip()
    user_groq_key = (request.headers.get("X-User-Groq-Key") or "").strip()
    server_groq_key = (settings.GROQ_API_KEY or "").strip()

    # Validate request with Pydantic
    try:
        chat_req = ChatRequest(**body)
    except Exception as e:
        logger.warning(f"[CHAT] Validation error: {e}")
        return {"error": f"Invalid request: {str(e)}"}

    # Build the dynamic system prompt with XML-isolated context
    system_prompt = build_system_prompt(chat_req.context)
    logger.info(f"[CHAT] message={chat_req.message[:80]!r} agent={chat_req.context.agent_type} jobs={len(chat_req.context.displayed_jobs_summary)} gemini={'Y' if user_gemini_key else 'N'} groq_user={'Y' if user_groq_key else 'N'} groq_srv={'Y' if server_groq_key else 'N'}")

    # Orchestrate fallback
    result = await orchestrate_chat_fallback(
        message=chat_req.message,
        system_prompt=system_prompt,
        user_gemini_key=user_gemini_key,
        user_groq_key=user_groq_key,
        server_groq_key=server_groq_key,
    )

    return {
        "response": result["response"],
        "provider_used": result["provider_used"],
        "quota_exhausted": result["quota_exhausted"],
    }


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    services = settings.validate()
    return {
        "status": "healthy",
        "version": "2.0.0",
        "ollama_online": bool(services.get("ollama_configured")),
        "services": services,
    }


@app.get("/health")
async def health_check_light():
    """Lightweight health check endpoint for server wake-up."""
    return {"status": "ok"}


# ─── Diagnostic Endpoint ──────────────────────────────────────────────────────

@app.get("/api/diagnostic")
async def diagnostic():
    """Diagnostic endpoint to check API key configuration."""
    return settings.validate()


# ─── Cover Letter Generation Endpoint ─────────────────────────────────

@app.post("/api/generate-letter")
async def generate_letter_endpoint(request: Request):
    """Generate a personalized cover letter using AI."""
    try:
        body = await request.json()
        cv_data = body.get("cv_data", {})
        job_title = body.get("job_title", "")
        company = body.get("company", "")
        job_description = body.get("job_description", "")
        ranking_engine = body.get("ranking_engine", "Groq / Llama 3.3")
        custom_gemini_key = body.get("custom_gemini_key")
        lang_label = body.get("lang_label", "français")

        if not cv_data:
            return {"error": "CV data is required"}
        if not job_title:
            return {"error": "Job title is required"}

        target_lang = (lang_label or "français").split("(")[0].strip().lower()
        if "english" in target_lang or "anglais" in target_lang:
            target_lang = "anglais"
        elif "espagnol" in target_lang or "español" in target_lang:
            target_lang = "espagnol"
        else:
            target_lang = "français"

        gemini_key = (custom_gemini_key or "").strip()
        logger.info(f"[LETTER] Generating letter for job={job_title!r} company={company!r}")

        result = await asyncio.to_thread(
            generate_cover_letter,
            cv_data=cv_data,
            job_title=job_title,
            company=company,
            job_description=job_description,
            target_lang=target_lang,
            selected_model=ranking_engine,
            gemini_api_key=settings.GEMINI_API_KEY,
            groq_api_key=settings.GROQ_API_KEY,
            ollama_url=settings.OLLAMA_URL,
            custom_gemini_key=gemini_key or None,
        )

        if not result:
            return {"error": "Failed to generate cover letter"}

        return {"letter": result}

    except Exception as e:
        logger.error(f"[LETTER] Error: {str(e)}")
        return {"error": str(e)}


# ─── Mock Interview: Generate Question ────────────────────────────────

@app.post("/api/mock-interview/question")
async def mock_interview_question(request: Request):
    """Generate an interview question using AI."""
    try:
        body = await request.json()
        job_title = body.get("job_title", "Poste")
        job_description = body.get("job_description", "")
        company = body.get("company", "")
        cv_data = body.get("cv_data")
        interview_stage = body.get("interview_stage", "débutant")
        question_type = body.get("question_type", "technique")
        ranking_engine = body.get("ranking_engine", "Groq / Llama 3.3")
        custom_gemini_key = body.get("custom_gemini_key")

        gemini_key = (custom_gemini_key or "").strip()

        cv_context = ""
        if cv_data:
            cv_context = f"""
PROFIL CANDIDAT :
- Metier : {cv_data.get('metier', 'Non specifie')}
- Annees d'experience : {cv_data.get('annees_experience', 0)}
- Competences cles : {', '.join(cv_data.get('mots_cles', []))}
- Resume : {cv_data.get('resume', '')}
"""

        prompt = f"""Tu es un recruteur expérimenté en {company or 'entreprise'}. Prepare une question d'entretien pour le poste de {job_title}.

{cv_context}

CONTEXTE :
- Niveau d'experience du candidat : {interview_stage}
- Type de question : {question_type}
- Description du poste : {job_description}

Pose une question pertinente, professionnelle, qui permet de veritablement evaluer les competences du candidat pour ce poste. La question doit etre en francais. Reponds uniquement par la question, sans aucune autre mention."""

        result = await asyncio.to_thread(
            call_ai_provider,
            prompt=prompt,
            selected_model=ranking_engine,
            is_json=False,
            custom_gemini_key=gemini_key or None,
        )

        if not result:
            return {"error": "Failed to generate interview question"}

        return {"question": result}

    except Exception as e:
        logger.error(f"[MOCK_INTERVIEW] Question error: {str(e)}")
        return {"error": str(e)}


# ─── Mock Interview: Evaluate Answer ────────────────────────────────

@app.post("/api/mock-interview/evaluate")
async def mock_interview_evaluate(request: Request):
    """Evaluate an interview answer using AI."""
    try:
        body = await request.json()
        question = body.get("question", "")
        answer = body.get("answer", "")
        job_title = body.get("job_title", "Poste")
        job_description = body.get("job_description", "")
        cv_data = body.get("cv_data")
        ranking_engine = body.get("ranking_engine", "Groq / Llama 3.3")
        custom_gemini_key = body.get("custom_gemini_key")

        if not question or not answer:
            return {"error": "Question and answer are required"}

        gemini_key = (custom_gemini_key or "").strip()

        cv_context = ""
        if cv_data:
            cv_context = f"""
PROFIL CANDIDAT :
- Metier : {cv_data.get('metier', 'Non specifie')}
- Annees d'experience : {cv_data.get('annees_experience', 0)}
- Competences cles : {', '.join(cv_data.get('mots_cles', []))}
"""

        prompt = f"""Tu es un recruteur experimente. Evalue la reponse d'un candidat a la question d'entretien suivante.

QUESTION: {question}
REPONSE DU CANDIDAT: {answer}
POSTE: {job_title}
DESCRIPTION: {job_description}
{cv_context}

Evalue sur 10 et fournis un retour constructif. Retourne UN OBJET JSON avec les cles suivantes : score (entier 0-10), feedback (texte court), points_forts (liste de 3 items), axes_amelioration (liste de 3 items)."""

        result = await asyncio.to_thread(
            call_ai_provider,
            prompt=prompt,
            selected_model=ranking_engine,
            is_json=True,
            custom_gemini_key=gemini_key or None,
        )

        if not result:
            return {"error": "Failed to evaluate interview answer"}

        try:
            data = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                return {"error": "Invalid response format"}

        return {"evaluation": data}

    except Exception as e:
        logger.error(f"[MOCK_INTERVIEW] Evaluation error: {str(e)}")
        return {"error": str(e)}


# ─── CV Analysis Endpoint ─────────────────────────────────────────────────────

@app.post("/api/analyze-cv")
async def analyze_cv_endpoint(
    file: UploadFile = File(...),
    selected_model: str = Form("Groq / Llama 3.3"),
    custom_gemini_key: Optional[str] = Form(None),
    lang_label: str = Form("français"),
    force_fallback_mode: bool = Form(False),
):
    """Analyze a CV PDF and return structured analysis."""
    request_id = id(file)
    logger.info(f"[CV_ANALYSIS] request={request_id} start model={selected_model} file={file.filename} lang={lang_label}")

    try:
        if not file or file.content_type != "application/pdf":
            logger.error(f"[CV_ANALYSIS] request={request_id} invalid file type={file.content_type if file else 'none'}")
            return {"error": "Seuls les fichiers PDF sont supportés."}

        pdf_bytes = await file.read()
        logger.info(f"[CV_ANALYSIS] request={request_id} read {len(pdf_bytes)} bytes")
        if not pdf_bytes:
            logger.error(f"[CV_ANALYSIS] request={request_id} empty pdf")
            return {"error": "Le fichier PDF est vide."}

        pdf_file = io.BytesIO(pdf_bytes)
        text = await asyncio.to_thread(extract_text_from_pdf, pdf_file)
        logger.info(f"[CV_ANALYSIS] request={request_id} extracted_text_len={len(text) if text else 0}")

        if not text or len(text.strip()) < 50:
            logger.error(f"[CV_ANALYSIS] request={request_id} extracted text too short")
            return {"error": "Impossible d'extraire du texte de ce PDF. Vérifiez qu'il contient du texte selectable."}

        target_lang = (lang_label or "français").split("(")[0].strip().lower()
        if "english" in target_lang or "anglais" in target_lang:
            target_lang = "anglais"
        elif "espagnol" in target_lang or "español" in target_lang:
            target_lang = "espagnol"
        else:
            target_lang = "français"

        gemini_key = (custom_gemini_key or settings.GEMINI_API_KEY or "").strip()
        logger.info(f"[CV_ANALYSIS] request={request_id} calling analyze_cv model={selected_model} lang={target_lang} gemini_present={bool(gemini_key)}")

        result = await asyncio.to_thread(
            analyze_cv_with_fallback,
            text=text,
            target_lang=target_lang,
            selected_model=selected_model,
            gemini_api_key=gemini_key,
            groq_api_key=settings.GROQ_API_KEY,
            ollama_url=settings.OLLAMA_URL,
            force_fallback_mode=force_fallback_mode,
        )

        if not result:
            logger.error(f"[CV_ANALYSIS] request={request_id} analyze_cv returned None")
            return {"error": "L'analyse du CV a échoué. Vérifiez la clé API ou le modèle sélectionné."}

        mode = "MODE SECOURS (regex)" if result.get("is_fallback") else "IA"
        logger.warning(f"[CV_ANALYSIS] request={request_id} mode={mode} metier={result.get('metier')}")
        return result

    except Exception as e:
        logger.exception(f"[CV_ANALYSIS] request={request_id} unexpected error")
        return {"error": str(e)}


# ─── Freelance Agent CV Analysis Endpoint ──────────────────────────────

@app.post("/api/freelance/analyze-cv")
async def analyze_freelance_cv_endpoint(
    file: UploadFile = File(...),
    selected_model: str = Form("Groq / Llama 3.3"),
    custom_gemini_key: Optional[str] = Form(None),
    lang_label: str = Form("français"),
    force_fallback_mode: bool = Form(False),
):
    """Analyze a CV PDF specifically for freelance mission matching."""
    request_id = id(file)
    logger.info(f"[FREELANCE_CV] request={request_id} start model={selected_model} file={file.filename} lang={lang_label}")

    try:
        if not file or file.content_type != "application/pdf":
            logger.error(f"[FREELANCE_CV] request={request_id} invalid file type={file.content_type if file else 'none'}")
            return {"error": "Seuls les fichiers PDF sont supportés."}

        pdf_bytes = await file.read()
        logger.info(f"[FREELANCE_CV] request={request_id} read {len(pdf_bytes)} bytes")
        if not pdf_bytes:
            logger.error(f"[FREELANCE_CV] request={request_id} empty pdf")
            return {"error": "Le fichier PDF est vide."}

        pdf_file = io.BytesIO(pdf_bytes)
        text = await asyncio.to_thread(extract_text_from_pdf, pdf_file)
        logger.info(f"[FREELANCE_CV] request={request_id} extracted_text_len={len(text) if text else 0}")

        if not text or len(text.strip()) < 50:
            logger.error(f"[FREELANCE_CV] request={request_id} extracted text too short")
            return {"error": "Impossible d'extraire du texte de ce PDF. Vérifiez qu'il contient du texte selectable."}

        target_lang = (lang_label or "français").split("(")[0].strip().lower()
        if "english" in target_lang or "anglais" in target_lang:
            target_lang = "anglais"
        elif "espagnol" in target_lang or "español" in target_lang:
            target_lang = "espagnol"
        else:
            target_lang = "français"

        gemini_key = (custom_gemini_key or settings.GEMINI_API_KEY or "").strip()
        logger.info(f"[FREELANCE_CV] request={request_id} calling analyze_freelance_cv model={selected_model} lang={target_lang}")

        result = await asyncio.to_thread(
            analyze_freelance_cv,
            text=text,
            target_lang=target_lang,
            selected_model=selected_model,
            gemini_api_key=gemini_key,
            groq_api_key=settings.GROQ_API_KEY,
            ollama_url=settings.OLLAMA_URL,
            force_fallback_mode=force_fallback_mode,
        )

        if not result:
            logger.error(f"[FREELANCE_CV] request={request_id} analyze_freelance_cv returned None")
            return {"error": "L'analyse du CV freelance a échoué."}

        mode = "MODE SECOURS (regex)" if result.get("is_fallback") else "IA"
        logger.warning(f"[FREELANCE_CV] request={request_id} mode={mode} metier={result.get('metier')}")
        return result

    except Exception as e:
        logger.exception(f"[FREELANCE_CV] request={request_id} unexpected error")
        return {"error": str(e)}


# ─── Recruiter Agent CV Analysis Endpoint ──────────────────────────────

@app.post("/api/recruiter/analyze-cv")
async def analyze_recruiter_cv_endpoint(
    file: UploadFile = File(...),
    selected_model: str = Form("Groq / Llama 3.3"),
    custom_gemini_key: Optional[str] = Form(None),
    lang_label: str = Form("français"),
    force_fallback_mode: bool = Form(False),
):
    """Analyze a CV PDF specifically for recruiter candidate matching."""
    request_id = id(file)
    logger.info(f"[RECRUITER_CV] request={request_id} start model={selected_model} file={file.filename} lang={lang_label}")

    try:
        if not file or file.content_type != "application/pdf":
            logger.error(f"[RECRUITER_CV] request={request_id} invalid file type={file.content_type if file else 'none'}")
            return {"error": "Seuls les fichiers PDF sont supportés."}

        pdf_bytes = await file.read()
        logger.info(f"[RECRUITER_CV] request={request_id} read {len(pdf_bytes)} bytes")
        if not pdf_bytes:
            logger.error(f"[RECRUITER_CV] request={request_id} empty pdf")
            return {"error": "Le fichier PDF est vide."}

        pdf_file = io.BytesIO(pdf_bytes)
        text = await asyncio.to_thread(extract_text_from_pdf, pdf_file)
        logger.info(f"[RECRUITER_CV] request={request_id} extracted_text_len={len(text) if text else 0}")

        if not text or len(text.strip()) < 50:
            logger.error(f"[RECRUITER_CV] request={request_id} extracted text too short")
            return {"error": "Impossible d'extraire du texte de ce PDF. Vérifiez qu'il contient du texte selectable."}

        target_lang = (lang_label or "français").split("(")[0].strip().lower()
        if "english" in target_lang or "anglais" in target_lang:
            target_lang = "anglais"
        elif "espagnol" in target_lang or "español" in target_lang:
            target_lang = "espagnol"
        else:
            target_lang = "français"

        gemini_key = (custom_gemini_key or settings.GEMINI_API_KEY or "").strip()
        logger.info(f"[RECRUITER_CV] request={request_id} calling analyze_recruiter_cv model={selected_model} lang={target_lang}")

        result = await asyncio.to_thread(
            analyze_recruiter_cv,
            text=text,
            target_lang=target_lang,
            selected_model=selected_model,
            gemini_api_key=gemini_key,
            groq_api_key=settings.GROQ_API_KEY,
            ollama_url=settings.OLLAMA_URL,
            force_fallback_mode=force_fallback_mode,
        )

        if not result:
            logger.error(f"[RECRUITER_CV] request={request_id} analyze_recruiter_cv returned None")
            return {"error": "L'analyse du CV recruteur a échoué."}

        mode = "MODE SECOURS (regex)" if result.get("is_fallback") else "IA"
        logger.warning(f"[RECRUITER_CV] request={request_id} mode={mode} metier={result.get('metier')}")
        return result

    except Exception as e:
        logger.exception(f"[RECRUITER_CV] request={request_id} unexpected error")
        return {"error": str(e)}


# ─── Freelance Agent Search Endpoint ───────────────────────────────────

@app.get("/api/freelance/search")
async def freelance_search(
    request: Request,
    query: str = Query(...),
    location: str = Query("France"),
    num_ads: str = Query("10"),
    mission_type: str = Query(""),
    duration: str = Query(""),
    remote: str = Query(""),
    tjm_min: str = Query(""),
    tjm_max: str = Query(""),
    selected_sources: str = Query(""),
    ranking_engine: str = Query("Groq / Llama 3.3"),
    custom_gemini_key: str = Query(None),
    cv_data: str = Query(None),
    no_ai_mode: bool = Query(False),
):
    """Freelance-specific job search endpoint."""
    logger.info(f"[FREELANCE_ENDPOINT] Starting freelance search: query={query!r} location={location!r} sources={selected_sources!r} no_ai_mode={no_ai_mode}")
    try:
        result = await _stream_agent_jobs(
            query=query,
            location=location,
            num_ads=num_ads,
            agent_type="freelance",
            agent_filters={
                "missionType": mission_type,
                "duration": duration,
                "remote": remote,
                "tjmMin": tjm_min,
                "tjmMax": tjm_max,
            },
            selected_sources=selected_sources,
            ranking_engine=ranking_engine,
            custom_gemini_key=custom_gemini_key,
            cv_data=cv_data,
            no_ai_mode=no_ai_mode,
        )
        logger.info(f"[FREELANCE_ENDPOINT] _stream_agent_jobs returned successfully")
        return result
    except Exception as e:
        logger.exception(f"[FREELANCE_ENDPOINT] Error in freelance search: {e}")
        raise


# ─── Recruiter Agent Search Endpoint ───────────────────────────────────

@app.get("/api/recruiter/search")
async def recruiter_search(
    request: Request,
    query: str = Query(...),
    location: str = Query("France"),
    num_ads: str = Query("10"),
    experience: str = Query(""),
    salary_min: str = Query(""),
    salary_max: str = Query(""),
    skills: str = Query(""),
    contract: str = Query("CDD"),
    remote: bool = Query(False),
    target_contract: str = Query("MIXTE"),
    availability: str = Query(""),
    selected_sources: str = Query(""),
    ranking_engine: str = Query("Groq / Llama 3.3"),
    custom_gemini_key: str = Query(None),
    cv_data: str = Query(None),
    no_ai_mode: bool = Query(False),
):
    """Recruiter-specific candidate search endpoint."""
    return await _stream_agent_jobs(
        query=query,
        location=location,
        num_ads=num_ads,
        agent_type="recruiter",
        agent_filters={
            "experience": experience,
            "salaryMin": salary_min,
            "salaryMax": salary_max,
            "skills": skills,
            "contract": contract,
            "remote": remote,
            "targetContract": target_contract,
            "availability": availability,
        },
        selected_sources=selected_sources,
        ranking_engine=ranking_engine,
        custom_gemini_key=custom_gemini_key,
        cv_data=cv_data,
        no_ai_mode=no_ai_mode,
    )


async def _stream_agent_jobs(
    query: str,
    location: str,
    num_ads: str,
    agent_type: str,
    agent_filters: dict,
    selected_sources: str,
    ranking_engine: str,
    custom_gemini_key: Optional[str],
    cv_data: Optional[str],
    no_ai_mode: bool,
):
    """Unified streaming handler for agent-specific searches."""
    logger.info(f"[AGENT_STREAM] START agent_type={agent_type} query={query!r} location={location!r} selected_sources={selected_sources!r}")
    sources_list = [s.strip() for s in selected_sources.split(",") if s.strip()]
    cv_data_dict = None
    if cv_data:
        try:
            cv_data_dict = json.loads(cv_data)
        except Exception:
            pass
    
    logger.info(f"[AGENT_STREAM] agent_type={agent_type} query={query!r} sources={sources_list}")
    
    # Handle num_ads: support "Max" for unlimited display per source, or numeric value
    if isinstance(num_ads, str) and num_ads.lower() == "max":
        display_limit = MAX_DISPLAY_ADS_PER_SOURCE
    else:
        parsed_num_ads = int(num_ads) if isinstance(num_ads, str) else num_ads
        display_limit = max(MIN_DISPLAY_ADS_PER_SOURCE, min(parsed_num_ads, MAX_DISPLAY_ADS_PER_SOURCE))
    
    search_limit = MAX_SEARCH_LIMIT

    # Get agent-specific searcher
    if agent_type == "freelance":
        searcher = FreelanceSearcher()
    elif agent_type == "recruiter":
        searcher = WorkerSearcher()
    else:
        searcher = JobSearcher()

    # Normalize agent filters to proper types for the searcher
    normalized_agent_filters = dict(agent_filters or {})
    if agent_type == "freelance":
        # Convert TJM values to integers
        if normalized_agent_filters.get("tjmMin"):
            try:
                normalized_agent_filters["tjmMin"] = int(normalized_agent_filters["tjmMin"])
            except (ValueError, TypeError):
                normalized_agent_filters["tjmMin"] = 0
        if normalized_agent_filters.get("tjmMax"):
            try:
                normalized_agent_filters["tjmMax"] = int(normalized_agent_filters["tjmMax"])
            except (ValueError, TypeError):
                normalized_agent_filters["tjmMax"] = 0
    elif agent_type == "recruiter":
        # Convert salary values to integers
        if normalized_agent_filters.get("salaryMin"):
            try:
                normalized_agent_filters["salaryMin"] = int(normalized_agent_filters["salaryMin"])
            except (ValueError, TypeError):
                normalized_agent_filters["salaryMin"] = 0
        if normalized_agent_filters.get("salaryMax"):
            try:
                normalized_agent_filters["salaryMax"] = int(normalized_agent_filters["salaryMax"])
            except (ValueError, TypeError):
                normalized_agent_filters["salaryMax"] = 0
        # Split skills into a list
        if normalized_agent_filters.get("skills"):
            normalized_agent_filters["skills"] = [
                s.strip() for s in normalized_agent_filters["skills"].split(",") if s.strip()
            ]
        # Convert remote to boolean
        if normalized_agent_filters.get("remote") in ("true", "True", "1"):
            normalized_agent_filters["remote"] = True
        elif normalized_agent_filters.get("remote") in ("false", "False", "0"):
            normalized_agent_filters["remote"] = False

    # Build the effective search query using the agent-specific searcher
    effective_query = searcher.build_search_query(query, location, normalized_agent_filters)

    # Import freelance scrapers
    from app.scrapers.freelance_sources import (
        scrape_upwork_rss,
        scrape_wwr_rss,
        scrape_remoteok_api,
        scrape_malt,
        scrape_freelancer_com,
    )

    # Map agent-specific sources to real, available sources
    AGENT_SOURCE_MAP = {
        # Freelance sources -> mapped to real scraper implementations
        "Upwork": "UpworkRSS",
        "Malt": "Malt",
        "Freelancer": "Freelancer.com",
        "404works": "Free-Work",
        "Freelance-Info": "Free-Work",
        "LeHibou": "Free-Work",
        # Codeur.com and FreelanceRepublik now have their own scrapers
        # Recruiter/Worker sources -> mapped to available scraping sources
        "Apec": "France Travail",
        "GitHub": "GitHub",
        "StackOverflow": "StackOverflow",
    }

    # Build source registry using agent-specific sources
    if not sources_list:
        sources_list = searcher.get_sources()
        logger.info(f"[AGENT_STREAM] Using default sources for {agent_type}: {sources_list}")
    else:
        logger.info(f"[AGENT_STREAM] Using provided sources: {sources_list}")

    # Map unknown agent sources to real available sources
    mapped_sources = [AGENT_SOURCE_MAP.get(s.strip(), s.strip()) for s in sources_list]
    mapped_sources = list(dict.fromkeys([s for s in mapped_sources if s]))
    logger.info(f"[AGENT_STREAM] Mapped sources: {mapped_sources}")

    # Filter to only known sources (those in build_source_registry)
    KNOWN_SOURCES = {
        "LinkedIn", "Indeed", "France Travail", "Monster", "HelloWork",
        "Google Jobs", "JobSpy", "Enhanced", "Adzuna", "Jooble", "Apify",
        "Free-Work", "Codeur.com", "FreelanceRepublik", "GitHub", "StackOverflow",
        "UpworkRSS", "WeWorkRemotelyRSS", "RemoteOK", "Malt", "Freelancer.com",
    }
    available_sources = [s for s in mapped_sources if s in KNOWN_SOURCES]
    logger.info(f"[AGENT_STREAM] Available sources after filtering: {available_sources}")

    # If no sources map to known ones, fall back to the job searcher's default sources
    if not available_sources:
        logger.warning(f"[AGENT_STREAM] No available sources for agent_type={agent_type}, falling back to job default sources")
        # Limit fallback sources to prevent timeouts
        fallback_sources = [s for s in JobSearcher().get_sources() if s in KNOWN_SOURCES][:3]
        logger.info(f"[AGENT_STREAM] Fallback sources limited to 3: {fallback_sources}")
        available_sources = fallback_sources
        logger.info(f"[AGENT_STREAM] Fallback sources: {available_sources}")

    # Use the mapped and filtered sources
    sources_list = available_sources
    logger.info(f"[AGENT_STREAM] Building registry with sources: {sources_list}")
    source_registry = build_source_registry(sources_list, cv_data_dict)
    total_sources = len(source_registry)
    logger.info(f"[AGENT_STREAM] Final source registry: {list(source_registry.keys())} (count={total_sources})")
    
    # Double-check: if registry is empty but we have sources, something went wrong
    if total_sources == 0 and available_sources:
        logger.error(f"[AGENT_STREAM] Registry is empty despite having sources: {available_sources}")
        logger.error(f"[AGENT_STREAM] This likely means the sources don't have scrapers implemented")

    async def event_generator():
        try:
            logger.info(f"[AGENT_STREAM] START agent_type={agent_type} query={query!r} sources={sources_list}")
            yield f"data: {json.dumps({'type': 'STARTED', 'query': query, 'total_sources': total_sources})}\n\n"
            await asyncio.sleep(0)

            if total_sources == 0:
                yield f"data: {json.dumps({'type': 'COMPLETED', 'jobs': [], 'source_status': {}, 'progress': 100})}\n\n"
                return

            aggregator = SearchAggregator(
                max_workers=settings.SCRAPER_MAX_WORKERS,
                timeout_per_source=settings.SCRAPER_TIMEOUT,
            )

            source_timeouts = {name: get_source_timeout(name) for name in source_registry}
            source_limits = {name: get_optimal_limit(search_limit, name) for name in source_registry}

            all_jobs = []
            source_results = {}
            sources_done = 0
            scored_jobs_map = {}
            emitted_counts = {}

            logger.info(f"[AGENT_STREAM] Starting aggregator search with query={effective_query!r} location={location!r}")

            job_count = 0
            async for result in aggregator.search_parallel_streaming(
                sources=source_registry,
                query=effective_query,
                location=location,
                limit=search_limit,
                target_jobs=0,
                source_timeouts=source_timeouts,
                source_limits=source_limits,
            ):
                if result.jobs:
                    all_jobs.extend(result.jobs)

                prev = source_results.get(result.source_name)
                if prev:
                    prev.jobs = (prev.jobs or []) + (result.jobs or [])
                    prev.success = prev.success and result.success
                    prev.execution_time = round((prev.execution_time or 0) + (result.execution_time or 0), 2)
                else:
                    source_results[result.source_name] = result

                if getattr(result, 'done', True):
                    sources_done += 1

                status = "completed" if result.success and getattr(result, 'done', True) else ("streaming" if getattr(result, 'is_partial', False) else "error")
                jobs_count = len(result.jobs) if result.jobs else 0
                progress = min(100, int(sources_done / total_sources * 100)) if total_sources > 0 else 100

                if result.jobs and jobs_count > 0:
                    logger.info(f"[AGENT_STREAM] source={result.source_name} sample_job={result.jobs[0].get('titre', 'N/A')}")

                if jobs_count == 0 and not result.success:
                    diagnostic = {
                        "source": result.source_name,
                        "error": result.error or "Aucun résultat",
                        "hint": _get_source_diagnostic_hint(result.source_name, result.error),
                    }
                elif jobs_count == 0 and result.success:
                    diagnostic = {
                        "source": result.source_name,
                        "error": "Aucun résultat trouvé",
                        "hint": _get_source_diagnostic_hint(result.source_name, ""),
                    }
                else:
                    diagnostic = None

                if display_limit <= MAX_DISPLAY_ADS_PER_SOURCE:
                    emitted_so_far = emitted_counts.get(result.source_name, 0)
                    remaining = display_limit - emitted_so_far
                    if remaining <= 0:
                        jobs_to_emit = []
                    else:
                        jobs_to_emit = (result.jobs or [])[:remaining]
                        emitted_counts[result.source_name] = emitted_so_far + len(jobs_to_emit)
                else:
                    jobs_to_emit = result.jobs or []

                yield f"data: {json.dumps({'type': 'SOURCE_RESULT', 'progress': progress, 'total_so_far': len(all_jobs), 'target': display_limit, 'source': result.source_name, 'status': status, 'jobs': jobs_to_emit, 'sources_done': sources_done, 'total_sources': total_sources, 'source_progress': progress, 'execution_time': result.execution_time, 'is_partial': getattr(result, 'is_partial', False), 'fallback': getattr(result, 'fallback', False), 'diagnostic': diagnostic})}\n\n"
                await asyncio.sleep(0)

                if result.jobs and cv_data_dict and not no_ai_mode:
                    try:
                        new_batch = result.jobs
                        job_chunks = [new_batch] if len(new_batch) <= 20 else [new_batch[i:i+20] for i in range(0, len(new_batch), 20)]
                        scored_jobs = []
                        for chunk in job_chunks:
                            scored = score_jobs(cv_data_dict, chunk, fast=True)
                            scored_jobs.extend(scored)
                        scored_jobs.sort(key=lambda x: x.get('pertinence_ai', 0), reverse=True)

                        for job in scored_jobs:
                            sig = _generate_job_signature(job)
                            scored_jobs_map[sig] = job

                        yield f"data: {json.dumps({'type': 'SCORES_UPDATED', 'jobs': scored_jobs, 'progress': progress})}\n\n"
                    except Exception as e:
                        logger.error(f"[AGENT_STREAM] Progressive AI scoring failed: {e}")
                        yield f"data: {json.dumps({'type': 'SCORES_UPDATED', 'jobs': [], 'progress': progress})}\n\n"

            source_status = {}
            for sname, sresult in source_results.items():
                source_status[sname] = {
                    "success": sresult.success,
                    "count": len(sresult.jobs) if sresult.jobs else 0,
                    "status": "completed" if sresult.success else "error",
                    "error": sresult.error,
                    "execution_time": sresult.execution_time,
                    "diagnostic": _get_source_diagnostic_hint(sname, sresult.error) if (not sresult.success or (sresult.jobs is None or len(sresult.jobs) == 0)) else None,
                }

            if cv_data_dict and scored_jobs_map:
                final_jobs = []
                for job in all_jobs:
                    sig = _generate_job_signature(job)
                    if sig in scored_jobs_map:
                        final_jobs.append(scored_jobs_map[sig])
                    else:
                        final_jobs.append(job)
                final_jobs.sort(key=lambda x: x.get('pertinence_ai', 0), reverse=True)
            else:
                final_jobs = all_jobs

            # Apply agent-specific filters on the final results using the agent searcher
            try:
                filtered_jobs = searcher.apply_filters(final_jobs, normalized_agent_filters)
                if filtered_jobs is not None:
                    final_jobs = filtered_jobs
            except Exception as e:
                logger.warning(f"[AGENT_STREAM] Agent filter application failed (continuing with unfiltered results): {e}")

            normalized_jobs = normalize_jobs_for_frontend(final_jobs)

            if display_limit <= MAX_DISPLAY_ADS_PER_SOURCE:
                limited_jobs = []
                source_display_counts = {}
                for job in normalized_jobs:
                    job_source = job.get('source', '')
                    source_display_counts[job_source] = source_display_counts.get(job_source, 0) + 1
                    if source_display_counts[job_source] <= display_limit:
                        limited_jobs.append(job)
                normalized_jobs = limited_jobs

            yield f"data: {json.dumps({'type': 'COMPLETED', 'jobs': normalized_jobs, 'source_status': source_status, 'progress': 100, 'total_jobs': len(all_jobs)})}\n\n"
            logger.info(f"[AGENT_STREAM] COMPLETED agent_type={agent_type} total_jobs={len(normalized_jobs)} sources={list(source_status.keys())}")
            await asyncio.sleep(0)
        except Exception as e:
            logger.exception(f"[AGENT_STREAM] GLOBAL_ERROR agent_type={agent_type}")
            yield f"data: {json.dumps({'type': 'ERROR', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Run with Uvicorn ─────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
