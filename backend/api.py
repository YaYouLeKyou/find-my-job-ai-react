import os
import re
import json
import sys
import urllib.parse
import logging
import time
import hashlib
import concurrent.futures
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body, Request

# Ensure the parent directory is in sys.path so 'shared' module is found
# This is needed because Railway starts the app from /app/backend/ but shared/ is at /app/shared/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import PyPDF2
from groq import Groq
try:
    import google.genai as genai
except ImportError:
    import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from jobspy import scrape_jobs
import pandas as pd
from dotenv import load_dotenv
from shared.ai import call_ai_provider, analyze_cv as shared_analyze_cv, rank_jobs_with_ai as shared_rank_jobs, generate_cover_letter as shared_generate_letter, estimate_workload as shared_estimate_workload
from ai_modules.enhanced_scrapers import search_all_free_sources, clean_title as enhanced_clean_title

# Config logging (must be before Redis setup)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import AI modules for enhanced scraping
try:
    from ai_modules.data_extraction import extract_job_data
    from ai_modules.deduplication import deduplicate_jobs
    from ai_modules.enrichment import enrich_job_data, enrich_jobs_batch
    from ai_modules.ranking import rank_jobs_ml
    AI_MODULES_AVAILABLE = True
    logger.info("✅ AI modules loaded successfully")
except ImportError as e:
    AI_MODULES_AVAILABLE = False
    logger.warning(f"⚠️ AI modules not available: {e}")

# Import Playwright scrapers (for JS-rendered sites that block requests-based scraping)
try:
    from ai_modules.playwright_scraper import (
        scrape_indeed_playwright,
        scrape_monster_playwright,
        scrape_careerbuilder_playwright,
        scrape_simplyhired_playwright,
        scrape_linkedin_playwright,
        scrape_welcometothejungle,
        scrape_hellowork,
        scrape_apec,
        scrape_jobteaser,
        scrape_all_playwright,
        PLAYWRIGHT_AVAILABLE,
    )
    logger.info("✅ Playwright scrapers loaded successfully")
except ImportError as e:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning(f"⚠️ Playwright scrapers not available: {e}")
    # Create no-op fallbacks
    def _noop(*a, **kw): return []
    scrape_indeed_playwright = _noop
    scrape_monster_playwright = _noop
    scrape_careerbuilder_playwright = _noop
    scrape_simplyhired_playwright = _noop
    scrape_linkedin_playwright = _noop
    scrape_welcometothejungle = _noop
    scrape_hellowork = _noop
    scrape_apec = _noop
    scrape_jobteaser = _noop
    scrape_all_playwright = _noop

# Redis cache setup
REDIS_AVAILABLE = False
redis_client = None
try:
    import redis
    # Create Redis client without testing connection to avoid blocking on startup
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
    REDIS_AVAILABLE = True
    logger.info("✅ Redis cache configured (connection will be tested on first use)")
except ImportError:
    logger.warning("⚠️ Redis package not installed. Caching disabled.")
except Exception as e:
    REDIS_AVAILABLE = False
    redis_client = None
    logger.warning(f"⚠️ Redis not available: {e}. Caching disabled.")

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute", "10/second"])

# Load environment variables
load_dotenv(override=True)

# Read keys from .env
api_key = os.getenv("GROQ_API_KEY", "").strip()
ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434").strip()
gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
xai_api_key = os.getenv("XAI_API_KEY", "").strip()
ft_client_id = os.getenv("FRANCE_TRAVAIL_CLIENT_ID", "").strip()
ft_client_secret = os.getenv("FRANCE_TRAVAIL_CLIENT_SECRET", "").strip()
adzuna_app_id = os.getenv("ADZUNA_APP_ID", "").strip()
adzuna_app_key = os.getenv("ADZUNA_APP_KEY", "").strip()
serpapi_key = os.getenv("SERPAPI_KEY", "").strip()
jooble_api_key = os.getenv("JOOBLE_API_KEY", "").strip()
apify_api_key = os.getenv("APIFY_API_KEY", "").strip()

# --- STARTUP DIAGNOSTIC ---
logger.info("=" * 60)
logger.info("FindMyJobAI Backend Startup Diagnostic")
logger.info("=" * 60)
logger.info(f"GROQ_API_KEY configured: {bool(api_key)}")
if api_key:
    logger.info(f"GROQ_API_KEY format valid (gsk_...): {api_key.startswith('gsk_')}")
    logger.info(f"GROQ_API_KEY preview: {api_key[:4]}...{api_key[-4:]}")
logger.info(f"GEMINI_API_KEY configured: {bool(gemini_api_key)}")
logger.info(f"Default model for CV analysis: Groq / Llama 3.3")
logger.info(f"If GROQ_API_KEY is missing, users must switch to Gemini 3.5 in the UI")
logger.info("=" * 60)

app = FastAPI(title="FindMyJobAI API", description="Backend API for React Prototype")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS middleware to allow connection from React (usually on port 5173 or 3000)
# In production, replace ["*"] with specific origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:8501,https://find-my-job-ai.netlify.app,https://*.netlify.app").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared headers for web scraping - expanded rotation
SCRAPE_HEADERS = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    },
    {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    },
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }
]

# Helper functions
def extract_text_from_pdf(pdf_file) -> Optional[str]:
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            content = page.extract_text() or ""
            if content:
                text += content + "\n"
        return text.strip() if text.strip() else None
    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        return None

def is_ollama_online() -> bool:
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def clean_job_title(title: str) -> str:
    if not title: return ""
    if isinstance(title, list):
        title = " ".join(map(str, title))
    clean = title.lower()
    clean = re.sub(r'\b(h/f|f/h|hf|fh|métier:|poste:)\b', '', clean, flags=re.IGNORECASE)
    clean = re.split(r'[,(\-:&/|]', clean)[0]
    return " ".join(clean.split()).capitalize()

def clean_html(text: str) -> str:
    try:
        return BeautifulSoup(text, "html.parser").get_text()
    except:
        return text

def get_random_headers():
    import random
    return random.choice(SCRAPE_HEADERS)

# ─── Web Scrapers for each source ───────────────────────────────────────────

def scrape_indeed(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Web scraper for Indeed jobs."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    jobs = []
    try:
        # Try Indeed France first
        urls = [
            f"https://fr.indeed.com/jobs?q={query}&l={urllib.parse.quote(location)}&limit={limit}",
            f"https://www.indeed.com/jobs?q={query}&l={urllib.parse.quote(location)}&limit={limit}"
        ]
        for url in urls:
            response = requests.get(url, headers=get_random_headers(), timeout=10)
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, 'html.parser')
            cards = soup.select('div.job_seen_beacon, .jobsearch-SerpJobCard, div[data-testid="job-card"], .cardOutline')
            if not cards:
                cards = soup.select('div[class*="jobsearch"]')
            if not cards:
                continue
            for card in cards[:limit]:
                title_elem = card.select_one('h2.jobTitle a, a.jobtitle, a[data-jk], h2 a')
                company_elem = card.select_one('span.companyName, .company, span[data-testid="companyname"], .company_info a')
                location_elem = card.select_one('div.companyLocation, span[data-testid="text-location"], .location')
                link_elem = card.select_one('h2.jobTitle a, a.jobtitle, a[data-jk]')
                link = "#"
                if link_elem:
                    href = link_elem.get('href', '')
                    if href.startswith('/'):
                        link = "https://fr.indeed.com" + href
                    elif href.startswith('http'):
                        link = href
                if title_elem:
                    jobs.append({
                        "titre": title_elem.get_text(strip=True),
                        "entreprise": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                        "lien": link,
                        "location": location_elem.get_text(strip=True) if location_elem else location,
                        "date": "",
                        "source": "Indeed"
                    })
            if jobs:
                break  # Stop if we got results from first URL
    except Exception as e:
        logger.error(f"Indeed scraper error: {e}")
    return jobs[:limit]

def scrape_linkedin(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Web scraper for LinkedIn jobs."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    loc = urllib.parse.quote(location)
    jobs = []
    try:
        url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={loc}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code != 200:
            return jobs
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('li[data-occludable-job-id], .job-search-card, .base-card')
        if not cards:
            cards = soup.select('div[class*="job-card"]')
        if not cards:
            # Try to extract from script tags
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'ItemList':
                        for item in data.get('itemListElement', []):
                            job = item.get('item', {})
                            if job.get('title'):
                                jobs.append({
                                    "titre": job.get('title'),
                                    "entreprise": job.get('hiringOrganization', {}).get('name', 'Non précisé'),
                                    "lien": job.get('url', '#'),
                                    "location": job.get('jobLocation', {}).get('address', {}).get('addressLocality', location),
                                    "date": "",
                                    "source": "LinkedIn"
                                })
                except:
                    pass
        for card in cards[:limit]:
            title_elem = card.select_one('a.base-card__full-link, h3.base-search-card__title, a[href*="/jobs/view"]')
            company_elem = card.select_one('h4.base-search-card__subtitle, a[data-tracking-control-name*="company"]')
            location_elem = card.select_one('span.job-search-card__location, span[class*="location"]')
            link_elem = card.select_one('a.base-card__full-link')
            link = link_elem.get('href', '#') if link_elem else '#'
            if title_elem:
                jobs.append({
                    "titre": title_elem.get_text(strip=True),
                    "entreprise": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                    "lien": link,
                    "location": location_elem.get_text(strip=True) if location_elem else location,
                    "date": "",
                    "source": "LinkedIn"
                })
        return jobs[:limit]
    except Exception as e:
        logger.error(f"LinkedIn scraper error: {e}")
        return jobs

def scrape_monster(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Web scraper for Monster jobs."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    jobs = []
    try:
        urls = [
            f"https://www.monster.fr/emploi/recherche?q={query}&where={urllib.parse.quote(location)}",
            f"https://www.monster.com/jobs/search?q={query}&where={urllib.parse.quote(location)}"
        ]
        for url in urls:
            response = requests.get(url, headers=get_random_headers(), timeout=10)
            if response.status_code != 200:
                continue
            soup = BeautifulSoup(response.text, 'html.parser')
            cards = soup.select('div[class*="card"], section[class*="card"], .job-row, article')
            if not cards:
                continue
            for card in cards[:limit]:
                title_elem = card.select_one('h2 a, h3 a, a[data-testid="jobTitle"], a[class*="title"]')
                company_elem = card.select_one('span[class*="company"], div[class*="company"],span[data-testid="company"]')
                location_elem = card.select_one('span[class*="location"], div[class*="location"]')
                link_elem = card.select_one('h2 a, h3 a, a[data-testid="jobTitle"]')
                link = link_elem.get('href', '#') if link_elem else '#'
                if link and not link.startswith('http'):
                    link = "https://www.monster.fr" + link
                if title_elem:
                    jobs.append({
                        "titre": title_elem.get_text(strip=True),
                        "entreprise": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                        "lien": link,
                        "location": location_elem.get_text(strip=True) if location_elem else location,
                        "date": "",
                        "source": "Monster"
                    })
            if jobs:
                break
    except Exception as e:
        logger.error(f"Monster scraper error: {e}")
    return jobs[:limit]

def scrape_careerbuilder(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Web scraper for Careerbuilder jobs."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    jobs = []
    try:
        url = f"https://www.careerbuilder.com/jobs?q={query}&location={urllib.parse.quote(location)}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code != 200:
            return jobs
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('div[data-job-id], div.job-row, article')
        if not cards:
            cards = soup.select('div[class*="job"]')
        for card in cards[:limit]:
            title_elem = card.select_one('a[data-job-id], a.job-title, h2 a')
            company_elem = card.select_one('span[class*="company"], div[class*="company"]')
            location_elem = card.select_one('span[class*="location"], div[class*="location"]')
            link_elem = card.select_one('a[data-job-id], a.job-title')
            link = link_elem.get('href', '#') if link_elem else '#'
            if link and not link.startswith('http'):
                link = "https://www.careerbuilder.com" + link
            if title_elem:
                jobs.append({
                    "titre": title_elem.get_text(strip=True),
                    "entreprise": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                    "lien": link,
                    "location": location_elem.get_text(strip=True) if location_elem else location,
                    "date": "",
                    "source": "Careerbuilder"
                })
    except Exception as e:
        logger.error(f"Careerbuilder scraper error: {e}")
    return jobs[:limit]

def scrape_simplyhired(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    """Web scraper for Simplyhired jobs."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    jobs = []
    try:
        url = f"https://www.simplyhired.com/search?q={query}&l={urllib.parse.quote(location)}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code != 200:
            return jobs
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('div[class*="card"], div.job, article')
        if not cards:
            cards = soup.select('div[class*="SerpJob"]')
        for card in cards[:limit]:
            title_elem = card.select_one('a[class*="title"], h2 a, h3 a')
            company_elem = card.select_one('span[class*="company"], div[class*="company"]')
            location_elem = card.select_one('span[class*="location"], div[class*="location"]')
            link_elem = card.select_one('a[class*="title"], h2 a')
            link = link_elem.get('href', '#') if link_elem else '#'
            if link and not link.startswith('http'):
                link = "https://www.simplyhired.com" + link
            if title_elem:
                jobs.append({
                    "titre": title_elem.get_text(strip=True),
                    "entreprise": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                    "lien": link,
                    "location": location_elem.get_text(strip=True) if location_elem else location,
                    "date": "",
                    "source": "Simplyhired"
                })
    except Exception as e:
        logger.error(f"Simplyhired scraper error: {e}")
    return jobs[:limit]

def scrape_france_travail_jobs(job_title: str, limit: int = 10) -> List[dict]:
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    headers = get_random_headers()
    jobs = []
    page = 1
    try:
        session = requests.Session()
        while len(jobs) < limit and page <= 5:
            # Try new France Travail URL (pole-emploi became France Travail in 2025)
            urls = [
                f"https://www.francetravail.fr/offres/recherche?motsCles={query}&page={page}",
                f"https://candidat.francetravail.fr/offres/recherche?motsCles={query}&page={page}",
                f"https://candidat.pole-emploi.fr/offres/recherche?motsCles={query}&page={page}"
            ]
            response = None
            for url in urls:
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        break
                except:
                    continue
            if not response or response.status_code != 200: break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.select('li[class*="offer"], article[class*="offer"], div[class*="result"], li[data-id-offre], .result-item, .offer-card')
            if not items:
                items = soup.select('div[class*="offre"], article.result, .media-body, a[class*="offer"]')
            if not items:
                # Fallback: try extracting from script JSON-LD
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        items_list = data if isinstance(data, list) else [data]
                        for item in items_list:
                            if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                                jobs.append({
                                    "title": item.get('title', ''),
                                    "company": item.get('hiringOrganization', {}).get('name', 'Non précisé'),
                                    "link": item.get('url', '#'),
                                    "source": "France Travail"
                                })
                    except:
                        pass
                if jobs:
                    break
            if not items: break

            for item in items:
                title_elem = item.select_one('h2.media-heading, .t4, .t5, a.titre, .media-heading')
                company_elem = item.select_one('p.sub-text, .nom-entreprise, span.entreprise')
                
                if title_elem:
                    link = "#"
                    href = title_elem.get('href', '')
                    if href:
                        link = "https://candidat.pole-emploi.fr" + href if href.startswith('/') else href
                    jobs.append({
                        "title": title_elem.get_text(strip=True),
                        "company": company_elem.get_text(strip=True) if company_elem else "Non précisé",
                        "link": link,
                        "source": "France Travail"
                    })
            page += 1
        return jobs
    except Exception as e:
        logger.error(f"Error scraping France Travail: {e}")
        return jobs

def get_france_travail_token() -> Optional[str]:
    if not ft_client_id or not ft_client_secret:
        return None
    auth_url = "https://entreprise.pole-emploi.fr/connexion/oauth2/access_token"
    params = {"realm": "/partenaire"}
    data = {
        "grant_type": "client_credentials",
        "client_id": ft_client_id,
        "client_secret": ft_client_secret,
        "scope": "api_offresdemploiv2"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(auth_url, params=params, data=data, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        return response.json().get("access_token")
    except Exception as e:
        logger.error(f"Error France Travail Auth: {e}")
        return None

def get_france_travail_jobs_api(job_title: str, limit: int = 10) -> List[dict]:
    token = get_france_travail_token()
    if not token:
        return []
    search_url = "https://api.pole-emploi.io/partenaire/offresdemploi/v2/offres/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "motsCles": job_title,
        "range": f"0-{limit-1}"
    }
    try:
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code == 204:
            return []
        response.raise_for_status()
        results = response.json().get("resultats", [])
        return [{
            "titre": res.get("intitule"),
            "entreprise": res.get("entreprise", {}).get("nom", "Confidentiel"),
            "lien": f"https://candidat.pole-emploi.fr/offres/recherche/detail/{res.get('id')}",
            "source": "France Travail"
        } for res in results]
    except Exception as e:
        logger.error(f"Error official France Travail API: {e}")
        return []

def chercher_offres_jobspy(job_title: str, location: str = "Paris, France", limit: int = 10, selected_sites: List[str] = None) -> List[dict]:
    try:
        clean_title = clean_job_title(job_title)
        sites = [s.lower().replace(" ", "_") for s in selected_sites] if selected_sites else ["indeed", "linkedin", "glassdoor", "zip_recruiter"]
        
        # jobspy expects specific names
        valid_sites = []
        for s in sites:
            if s == "linkedin": valid_sites.append("linkedin")
            elif s == "indeed": valid_sites.append("indeed")
            elif s == "ziprecruiter": valid_sites.append("zip_recruiter")
            elif s == "glassdoor": valid_sites.append("glassdoor")
        
        if not valid_sites:
            valid_sites = ["indeed", "linkedin", "glassdoor", "zip_recruiter"]
            
        jobs_df = scrape_jobs(
            site_name=valid_sites,
            search_term=clean_title,
            location=location,
            results_per_site=limit,
            hours_old=72
        )
        results = []
        if not jobs_df.empty:
            for _, row in jobs_df.iterrows():
                results.append({
                    "title": row.get("title", "Sans titre"),
                    "company": row.get("company", "Entreprise anonyme"),
                    "job_url": row.get("job_url", "#"),
                    "site": row.get("site", "Jobspy"),
                    "date_posted": str(row.get("date_posted", "")),
                    "location": row.get("location", ""),
                    "description": row.get("description", "")
                })
        return results
    except Exception as e:
        logger.error(f"Error Jobspy: {e}")
        return []

def get_adzuna_jobs(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    if not adzuna_app_id or not adzuna_app_key:
        return []
    url = f"https://api.adzuna.com/v1/api/jobs/fr/search/1"
    params = {
        "app_id": adzuna_app_id,
        "app_key": adzuna_app_key,
        "results_per_page": limit,
        "what": job_title,
        "where": location,
        "content-type": "application/json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json().get("results", [])
        return [{
            "titre": res.get("title"),
            "entreprise": res.get("company", {}).get("display_name", "N/C"),
            "lien": res.get("redirect_url"),
            "date": res.get("created", ""),
            "location": res.get("location", {}).get("display_name", ""),
            "source": "Adzuna"
        } for res in results]
    except Exception as e:
        logger.error(f"Adzuna API error: {e}")
        return []

def get_serpapi_jobs(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    if not serpapi_key:
        return []
    url = "https://serpapi.com/search"
    # Clean location to avoid SerpApi 400 errors
    clean_location = location.split(',')[0].strip() if location else "France"
    params = {
        "engine": "google_jobs",
        "q": f"{job_title} {clean_location}",
        "location": clean_location,
        "hl": "fr",
        "api_key": serpapi_key,
        "num": limit
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        results = data.get("jobs_results", [])
        if not results:
            logger.warning(f"SerpApi returned 0 results for: {job_title}")
        return [{
            "titre": res.get("title"),
            "entreprise": res.get("company_name", "N/C"),
            "lien": res.get("related_links", [{}])[0].get("link") if res.get("related_links") else "#",
            "date": res.get("detected_extensions", {}).get("posted_at", ""),
            "location": res.get("location", ""),
            "source": "Google Jobs"
        } for res in results[:limit]]
    except Exception as e:
        logger.error(f"SerpApi error: {e}")
        return []

def get_jooble_jobs(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    if not jooble_api_key:
        return []
    url = f"https://jooble.org/api/{jooble_api_key}"
    try:
        response = requests.post(url, json={"keywords": job_title, "location": location}, timeout=10)
        response.raise_for_status()
        results = response.json().get("jobs", [])
        return [{
            "titre": clean_html(res.get("title", "")),
            "entreprise": res.get("company", "N/C"),
            "lien": res.get("link"),
            "date": res.get("updated", ""),
            "location": res.get("type", ""),
            "source": "Jooble"
        } for res in results[:limit]]
    except Exception as e:
        logger.error(f"Jooble API error: {e}")
        return []

def scrape_malt(job_title: str, limit: int = 10) -> List[dict]:
    """Web scraper for Malt freelance missions."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    jobs = []
    try:
        url = f"https://www.malt.fr/s?q={query}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code != 200:
            return jobs
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('div[class*="card"], article, div[class*="mission-card"], div[class*="project-card"]')
        if not cards:
            cards = soup.select('div[class*="Feed_project"], div[class*="search-result"]')
        if not cards:
            return jobs
        for card in cards[:limit]:
            title_elem = card.select_one('h2 a, h3 a, a[class*="title"], a[class*="name"]')
            company_elem = card.select_one('span[class*="client"], div[class*="client"], span[class*="company"]')
            link_elem = card.select_one('a[href*="/project"], a[href*="/mission"], h2 a, h3 a')
            link = link_elem.get('href', '#') if link_elem else '#'
            if link and not link.startswith('http'):
                link = "https://www.malt.fr" + link
            if title_elem:
                jobs.append({
                    "titre": title_elem.get_text(strip=True),
                    "entreprise": company_elem.get_text(strip=True) if company_elem else "Client Malt",
                    "lien": link,
                    "date": "",
                    "source": "Malt"
                })
    except Exception as e:
        logger.error(f"Malt scraper error: {e}")
    return jobs[:limit]

def scrape_upwork(job_title: str, limit: int = 10) -> List[dict]:
    """Web scraper for Upwork freelance jobs."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    jobs = []
    try:
        url = f"https://www.upwork.com/search/jobs/?q={query}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code != 200:
            return jobs
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('article, div[class*="job-card"], div[class*="JobSearchCard"]')
        if not cards:
            cards = soup.select('section[class*="job"]')
        if not cards:
            return jobs
        for card in cards[:limit]:
            title_elem = card.select_one('a[class*="title"], h2 a, h3 a, a[data-test*="job-title"]')
            company_elem = card.select_one('span[class*="client"], div[class*="client"]')
            link_elem = card.select_one('a[class*="title"], a[data-test*="job-title"], h2 a')
            link = link_elem.get('href', '#') if link_elem else '#'
            if link and not link.startswith('http'):
                link = "https://www.upwork.com" + link
            if title_elem:
                jobs.append({
                    "titre": title_elem.get_text(strip=True),
                    "entreprise": "Upwork",
                    "lien": link,
                    "date": "",
                    "source": "Upwork"
                })
    except Exception as e:
        logger.error(f"Upwork scraper error: {e}")
    return jobs[:limit]

def scrape_codeur(job_title: str, limit: int = 10) -> List[dict]:
    """Web scraper for Codeur.com freelance projects."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    jobs = []
    try:
        url = f"https://www.codeur.com/projects?search={query}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code != 200:
            return jobs
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('div[class*="project"], article, li[class*="project"]')
        if not cards:
            cards = soup.select('div[class*="card"]')
        if not cards:
            return jobs
        for card in cards[:limit]:
            title_elem = card.select_one('h2 a, h3 a, a[class*="title"], a[class*="project"]')
            company_elem = card.select_one('span[class*="client"], div[class*="client"], span[class*="budget"]')
            link_elem = card.select_one('a[href*="/project"], h2 a, a[class*="project"]')
            link = link_elem.get('href', '#') if link_elem else '#'
            if link and not link.startswith('http'):
                link = "https://www.codeur.com" + link
            if title_elem:
                jobs.append({
                    "titre": title_elem.get_text(strip=True),
                    "entreprise": "Codeur.com",
                    "lien": link,
                    "date": "",
                    "source": "Codeur.com"
                })
    except Exception as e:
        logger.error(f"Codeur.com scraper error: {e}")
    return jobs[:limit]

def scrape_freelance_informatique(job_title: str, limit: int = 10) -> List[dict]:
    """Web scraper for Freelance-Informatique.fr."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    jobs = []
    try:
        url = f"https://www.freelance-informatique.fr/offres?q={query}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code != 200:
            return jobs
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('div[class*="offer"], article, div[class*="card"]')
        if not cards:
            return jobs
        for card in cards[:limit]:
            title_elem = card.select_one('h2 a, h3 a, a[class*="title"]')
            link_elem = card.select_one('a[href*="/offre"], h2 a')
            link = link_elem.get('href', '#') if link_elem else '#'
            if link and not link.startswith('http'):
                link = "https://www.freelance-informatique.fr" + link
            if title_elem:
                jobs.append({
                    "titre": title_elem.get_text(strip=True),
                    "entreprise": "Freelance Informatique",
                    "lien": link,
                    "date": "",
                    "source": "FreelanceInformatique"
                })
    except Exception as e:
        logger.error(f"Freelance-Informatique scraper error: {e}")
    return jobs[:limit]

def scrape_cremedelacreme(job_title: str, limit: int = 10) -> List[dict]:
    """Web scraper for Crème de la Crème freelance."""
    clean_title = clean_job_title(job_title)
    query = urllib.parse.quote(clean_title)
    jobs = []
    try:
        url = f"https://cremedelacreme.io/fr/missions?query={query}"
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        if response.status_code != 200:
            return jobs
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('div[class*="card"], article, div[class*="mission"]')
        if not cards:
            return jobs
        for card in cards[:limit]:
            title_elem = card.select_one('h2 a, h3 a, a[class*="title"]')
            company_elem = card.select_one('span[class*="company"], div[class*="company"]')
            link_elem = card.select_one('a[href*="/missions"], h2 a')
            link = link_elem.get('href', '#') if link_elem else '#'
            if link and not link.startswith('http'):
                link = "https://cremedelacreme.io" + link
            if title_elem:
                jobs.append({
                    "titre": title_elem.get_text(strip=True),
                    "entreprise": company_elem.get_text(strip=True) if company_elem else "Crème de la Crème",
                    "lien": link,
                    "date": "",
                    "source": "CrèmeDeLaCrème"
                })
    except Exception as e:
        logger.error(f"Crème de la Crème scraper error: {e}")
    return jobs[:limit]

def get_apify_jobs(job_title: str, location: str = "France", limit: int = 10) -> List[dict]:
    if not apify_api_key or apify_api_key == "votre_cle_apify_ici":
        return []
    # Use Apify LinkedIn Jobs Scraper actor
    url = f"https://api.apify.com/v2/acts/apify~linkedin-jobs-scraper/run-sync-get-dataset-items"
    params = {"token": apify_api_key}
    payload = {
        "searchKeywords": job_title,
        "location": location,
        "maxItems": limit,
        "sort": "recent"
    }
    try:
        response = requests.post(url, params=params, json=payload, timeout=60)
        if response.status_code != 200:
            logger.error(f"Apify returned status {response.status_code}: {response.text[:200]}")
            return []
        results = response.json()
        if not isinstance(results, list):
            results = results.get("data", {}).get("items", [])
        return [{
            "titre": res.get("title") or res.get("jobTitle", "N/A"),
            "entreprise": res.get("companyName") or res.get("company", "N/C"),
            "lien": res.get("url") or res.get("jobUrl", "#"),
            "location": res.get("location") or res.get("jobLocation", ""),
            "source": "LinkedIn"
        } for res in results[:limit]]
    except Exception as e:
        logger.error(f"Apify API error: {e}")
        return []

def rank_jobs_with_ai(cv_data: dict, jobs: List[dict], filters: dict, ranking_engine: str = "Groq / Llama 3.3", custom_gemini_key: Optional[str] = None) -> List[dict]:
    """Wrapper pour utiliser la fonction partagée."""
    return shared_rank_jobs(
        cv_data=cv_data,
        jobs=jobs,
        filters=filters,
        target_lang="français",
        selected_model=ranking_engine,
        gemini_api_key=gemini_api_key,
        xai_api_key=xai_api_key,
        groq_api_key=api_key,
        ollama_url=ollama_url,
        custom_gemini_key=custom_gemini_key
    )

def get_cache_key(params: Dict[str, Any]) -> str:
    """Generate cache key from request parameters."""
    param_str = json.dumps(params, sort_keys=True)
    return f"job_search:{hashlib.md5(param_str.encode()).hexdigest()}"

# FastAPI schemas
class CvAnalysisRequest(BaseModel):
    selected_model: str = "Groq / Llama 3.3"
    custom_gemini_key: Optional[str] = None
    lang_label: str = "français"

class JobSearchRequest(BaseModel):
    query: str
    location: str = "Paris, France"
    num_ads: int = 10
    contract: str = "CDI"
    remote: bool = False
    global_search: bool = False
    selected_sources: List[str] = []
    sort_option: str = "Pertinence (IA)"
    ranking_engine: str = "Groq / Llama 3.3"
    custom_gemini_key: Optional[str] = None
    lang_code: str = "fr"
    lang_label: str = "français"
    cv_data: Optional[dict] = None
    is_freelance: Optional[bool] = False
    tjm_min: Optional[int] = None
    tjm_max: Optional[int] = None

class CoverLetterRequest(BaseModel):
    cv_data: dict
    job_title: str
    company: str
    job_description: Optional[str] = ""
    ranking_engine: str = "Groq / Llama 3.3"
    custom_gemini_key: Optional[str] = None
    lang_label: str = "français"
    is_freelance: Optional[bool] = False

class WorkloadEstimationRequest(BaseModel):
    mission_title: str
    mission_description: str
    cv_data: Optional[dict] = None
    ranking_engine: str = "Groq / Llama 3.3"
    custom_gemini_key: Optional[str] = None
    lang_label: str = "français"

# Endpoints
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "ollama_online": is_ollama_online()
    }

@app.get("/api/diagnostic")
def diagnostic():
    """Diagnostic endpoint to check API key configuration."""
    return {
        "groq_key_configured": bool(api_key and api_key.startswith("gsk_")),
        "gemini_key_configured": bool(gemini_api_key),
        "xai_key_configured": bool(xai_api_key),
        "ollama_configured": bool(ollama_url),
        "france_travail_configured": bool(ft_client_id and ft_client_secret),
        "adzuna_configured": bool(adzuna_app_id and adzuna_app_key),
        "serpapi_configured": bool(serpapi_key),
        "jooble_configured": bool(jooble_api_key),
        "apify_configured": bool(apify_api_key),
        "default_model": "Groq / Llama 3.3",
        "recommendation": "Configure GROQ_API_KEY in Railway environment variables, or switch to Gemini with a custom key in the UI."
    }

@app.post("/api/analyze-cv")
@limiter.limit("10/minute")  # Max 10 CV analyses per minute per IP
async def api_analyze_cv(
    request: Request,
    file: UploadFile = File(...),
    selected_model: str = Form("Groq / Llama 3.3"),
    custom_gemini_key: Optional[str] = Form(None),
    lang_label: str = Form("français")
):
    try:
        logger.info(f"Received CV upload request: filename={file.filename}, content_type={file.content_type}, model={selected_model}")
        
        # Check file extension (more permissive)
        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"Rejected file: not a PDF (filename={file.filename})")
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
        # Read PDF text
        try:
            contents = await file.read()
            logger.info(f"Read {len(contents)} bytes from PDF")
            
            if len(contents) == 0:
                raise HTTPException(status_code=400, detail="Le fichier PDF est vide.")
            
            import io
            pdf_file = io.BytesIO(contents)
            text = extract_text_from_pdf(pdf_file)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading PDF: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to read PDF file: {str(e)}")

        if not text or len(text) <= 50:
            logger.warning(f"Insufficient text extracted from PDF (length={len(text) if text else 0})")
            raise HTTPException(status_code=400, detail="Could not extract sufficient text from PDF. Please ensure your PDF contains readable text.")

        logger.info(f"Extracted {len(text)} characters from PDF, calling AI analysis...")
        
        # Call AI CV analysis with automatic fallback using shared function
        active_gemini_key = (custom_gemini_key or gemini_api_key or "").strip()
        fallback_used = None
        
        # Try the selected model first, then fallback
        models_to_try = []
        
        if "(Local/dev)" in selected_model:
            models_to_try.append(("local", selected_model))
            # Fallback: try Gemini if user provided a key
            if active_gemini_key:
                models_to_try.append(("gemini", "Gemini 3.5"))
            # Final fallback: try Groq if key exists
            if api_key and api_key.startswith("gsk_"):
                models_to_try.append(("groq", "Groq / Llama 3.3"))
        elif "Grok" in selected_model:
            if xai_api_key:
                models_to_try.append(("grok", selected_model))
            if active_gemini_key:
                models_to_try.append(("gemini", "Gemini 3.5"))
            if api_key and api_key.startswith("gsk_"):
                models_to_try.append(("groq", "Groq / Llama 3.3"))
        elif "Gemini" in selected_model:
            if active_gemini_key:
                models_to_try.append(("gemini", selected_model))
            if api_key and api_key.startswith("gsk_"):
                models_to_try.append(("groq", "Groq / Llama 3.3"))
        else:  # Groq / Llama 3.3 (default)
            if api_key and api_key.startswith("gsk_"):
                models_to_try.append(("groq", selected_model))
            if active_gemini_key:
                models_to_try.append(("gemini", "Gemini 3.5"))

        if not models_to_try:
            missing_keys = []
            if not active_gemini_key:
                missing_keys.append("- Clé Gemini (ajoutez votre clé personnelle dans le panneau latéral)")
            if not api_key:
                missing_keys.append("- Clé Groq (GROQ_API_KEY manquante sur le serveur)")
            error_msg = "Aucune clé API disponible pour l'analyse.\n" + "\n".join(missing_keys)
            raise HTTPException(status_code=500, detail=error_msg)

        data = None
        last_error = ""
        for provider, model in models_to_try:
            try:
                logger.info(f"Trying CV analysis with {provider} ({model})")
                data = shared_analyze_cv(
                    text=text,
                    target_lang=lang_label,
                    selected_model=model,
                    gemini_api_key=gemini_api_key,
                    xai_api_key=xai_api_key,
                    groq_api_key=api_key,
                    ollama_url=ollama_url,
                    custom_gemini_key=custom_gemini_key
                )
                if data:
                    if model != selected_model:
                        fallback_used = model
                    break
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Fallback {model} failed: {e}")
                continue

        if not data:
            logger.error("All CV analysis attempts failed")
            raise HTTPException(
                status_code=500,
                detail=f"L'analyse CV a échoué avec tous les modèles disponibles. Dernière erreur: {last_error}"
            )

        if fallback_used:
            data["_fallback"] = fallback_used
            logger.info(f"CV analysis succeeded with fallback model: {fallback_used}")
        else:
            logger.info(f"CV analysis successful: metier={data.get('metier')}")
            
        return data
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in api_analyze_cv: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/api/search-jobs")
@limiter.limit("20/minute")  # Max 20 searches per minute per IP
def api_search_jobs(request: Request, req: JobSearchRequest):
    all_results = []
    
    # Check cache first
    cache_key = None
    if REDIS_AVAILABLE:
        cache_key = get_cache_key(req.dict())
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for query: {req.query}")
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
    
    # Track source status (per source: success count or error)
    source_status = {}
    for s in req.selected_sources:
        source_status[s] = {"status": "pending", "count": 0, "error": ""}

    # Log which sources are being queried
    logger.info(f"🔍 SEARCH START: query='{req.query}', location='{req.location}', num_ads={req.num_ads}")
    logger.info(f"📡 REQUESTED SOURCES: {req.selected_sources}")

    # Concurrency using ThreadPool - increased workers for more parallel scraping
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = {}
        
        js_sites = ["Indeed", "LinkedIn", "Google Jobs", "Glassdoor", "ZipRecruiter", "Simplyhired", "Careerbuilder", "Monster"]
        # If any of the Jobspy sites are selected
        selected_for_jobspy = [s for s in req.selected_sources if s in js_sites]
        if selected_for_jobspy:
            logger.info(f"📡 Launching JobSpy for: {selected_for_jobspy}")
            for s in selected_for_jobspy:
                source_status[s]["status"] = "scraping"
            futures['jobspy'] = executor.submit(chercher_offres_jobspy, req.query, req.location, req.num_ads, req.selected_sources)
        
        if "Adzuna" in req.selected_sources:
            logger.info("📡 Launching Adzuna scraper...")
            source_status["Adzuna"]["status"] = "scraping"
            futures['adzuna'] = executor.submit(get_adzuna_jobs, req.query, req.location, req.num_ads)
            
        if "Google Jobs" in req.selected_sources:
            logger.info("📡 Launching SerpApi (Google Jobs)...")
            source_status["Google Jobs"]["status"] = "scraping"
            futures['serpapi'] = executor.submit(get_serpapi_jobs, req.query, req.location, req.num_ads)
            
        if "Jooble" in req.selected_sources:
            logger.info("📡 Launching Jooble scraper...")
            source_status["Jooble"]["status"] = "scraping"
            futures['jooble'] = executor.submit(get_jooble_jobs, req.query, req.location, req.num_ads)
            
        # Always use Apify as a fallback/enrichment for LinkedIn if key is available
        if "LinkedIn" in req.selected_sources and apify_api_key:
            logger.info("📡 Launching Apify LinkedIn scraper (enrichment)...")
            futures['apify'] = executor.submit(get_apify_jobs, req.query, req.location, req.num_ads)

        # Web scrapers as fallback for sources that often fail with JobSpy
        # We run web scrapers in parallel with JobSpy to get more results
        if "Indeed" in req.selected_sources:
            logger.info("📡 Launching Indeed web scraper...")
            futures['indeed_scrape'] = executor.submit(scrape_indeed, req.query, req.location, req.num_ads)
        
        if "LinkedIn" in req.selected_sources:
            logger.info("📡 Launching LinkedIn web scraper...")
            futures['linkedin_scrape'] = executor.submit(scrape_linkedin, req.query, req.location, req.num_ads)
        
        if "Monster" in req.selected_sources:
            logger.info("📡 Launching Monster web scraper...")
            futures['monster_scrape'] = executor.submit(scrape_monster, req.query, req.location, req.num_ads)
        
        if "Careerbuilder" in req.selected_sources:
            logger.info("📡 Launching Careerbuilder web scraper...")
            futures['careerbuilder_scrape'] = executor.submit(scrape_careerbuilder, req.query, req.location, req.num_ads)
        
        if "Simplyhired" in req.selected_sources:
            logger.info("📡 Launching Simplyhired web scraper...")
            futures['simplyhired_scrape'] = executor.submit(scrape_simplyhired, req.query, req.location, req.num_ads)

        # ─── ENHANCED FREE SCRAPERS v2.0 (RSS + Free APIs + International + French) ──
        # These provide additional coverage from 40+ free sources
        enhanced_sources = ["Indeed", "LinkedIn", "Simplyhired", "Careerbuilder", 
                            "France Travail", "Google Jobs", "Remotive", "RemoteOK",
                            "Welcome to the Jungle", "HelloWork", "Emploi Public",
                            "Reed", "StepStone", "Xing", "InfoJobs", "Dice",
                            "Naukri", "Bayt", "Seek",
                            "RégionsJob", "ChooseYourBoss", "LesJeudis", "Talent.io",
                            "Jobijoba", "Glassdoor", "ZipRecruiter",
                            "Freelance.com", "Malt"]
        enhanced_needed = [s for s in req.selected_sources if s in enhanced_sources]
        if enhanced_needed:
            logger.info(f"📡 Launching enhanced free scrapers (parallel) for: {enhanced_needed}")
            futures['enhanced_scrapers'] = executor.submit(
                search_all_free_sources, req.query, req.location, req.num_ads, enhanced_needed
            )

        # ─── New French job sources (Welcome to the Jungle, HelloWork, APEC, JobTeaser) ──
        if "Welcome to the Jungle" in req.selected_sources:
            logger.info("📡 Launching Welcome to the Jungle scraper...")
            futures['welcometothejungle'] = executor.submit(scrape_welcometothejungle, req.query, req.location, req.num_ads)
        if "HelloWork" in req.selected_sources:
            logger.info("📡 Launching HelloWork scraper...")
            futures['hellowork'] = executor.submit(scrape_hellowork, req.query, req.location, req.num_ads)
        if "APEC" in req.selected_sources:
            logger.info("📡 Launching APEC scraper...")
            futures['apec'] = executor.submit(scrape_apec, req.query, req.location, req.num_ads)
        if "JobTeaser" in req.selected_sources:
            logger.info("📡 Launching JobTeaser scraper...")
            futures['jobteaser'] = executor.submit(scrape_jobteaser, req.query, req.location, req.num_ads)

        # ─── Freelance-specific scrapers (when is_freelance=true) ──────────────
        if req.is_freelance:
            if "FreelanceInformatique" in req.selected_sources or "Freelance Informatique" in req.selected_sources:
                logger.info("📡 Launching Freelance-Informatique scraper...")
                futures['freelance_informatique'] = executor.submit(scrape_freelance_informatique, req.query, req.num_ads)
            if "CrèmeDeLaCrème" in req.selected_sources or "Crème de la Crème" in req.selected_sources:
                logger.info("📡 Launching Crème de la Crème scraper...")
                futures['cremedelacreme'] = executor.submit(scrape_cremedelacreme, req.query, req.num_ads)
            if "Codeur.com" in req.selected_sources:
                logger.info("📡 Launching Codeur.com scraper...")
                futures['codeurcom'] = executor.submit(scrape_codeur, req.query, req.num_ads)
            if "Malt" in req.selected_sources:
                logger.info("📡 Launching Malt scraper...")
                futures['malt'] = executor.submit(scrape_malt, req.query, req.num_ads)
            if "Upwork" in req.selected_sources:
                logger.info("📡 Launching Upwork scraper...")
                futures['upwork'] = executor.submit(scrape_upwork, req.query, req.num_ads)

        # ─── Collect JobSpy results ─────────────────────────────────────────
        if 'jobspy' in futures:
            try:
                jobspy_res = futures['jobspy'].result()
                logger.info(f"✅ JobSpy returned {len(jobspy_res)} results")
                
                site_counts = {}
                for row in jobspy_res:
                    site = str(row.get('site', 'Jobspy')).lower()
                    if site == "linkedin": source_label = "LinkedIn"
                    elif site == "glassdoor": source_label = "Glassdoor"
                    elif site == "zip_recruiter": source_label = "ZipRecruiter"
                    elif site == "careerbuilder": source_label = "Careerbuilder"
                    elif site == "monster": source_label = "Monster"
                    elif site == "simplyhired": source_label = "Simplyhired"
                    else: source_label = site.capitalize()
                    site_counts[source_label] = site_counts.get(source_label, 0) + 1
                    all_results.append({
                        "title": row.get('title', 'N/A'),
                        "company": row.get('company', 'N/A'),
                        "link": row.get('job_url', '#'),
                        "source": source_label,
                        "date": str(row.get('date_posted', '')),
                        "location": row.get('location', ''),
                        "desc": row.get('description', ''),
                        "id": f"js_{len(all_results)}_{hash(row.get('job_url'))}"
                    })
                for src, cnt in site_counts.items():
                    logger.info(f"   JobSpy -> {src}: {cnt} results")
                    if src in source_status:
                        source_status[src] = {"status": "success", "count": cnt, "error": ""}
                # Mark JobSpy sources that returned 0 as "no_results"
                for s in selected_for_jobspy:
                    if s in site_counts:
                        source_status[s] = {"status": "success", "count": site_counts[s], "error": ""}
                    elif source_status[s]["status"] != "success":
                        source_status[s] = {"status": "no_results", "count": 0, "error": "Aucun résultat trouvé"}
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ JobSpy Thread failed: {e}")
                for s in selected_for_jobspy:
                    source_status[s] = {"status": "error", "count": 0, "error": error_msg[:100]}

        # ─── Collect web scraper results (deduplicated) ─────────────────────
        scrapers = {
            'indeed_scrape': 'Indeed',
            'linkedin_scrape': 'LinkedIn',
            'monster_scrape': 'Monster',
            'careerbuilder_scrape': 'Careerbuilder',
            'simplyhired_scrape': 'Simplyhired'
        }
        
        existing_links = set()
        for r in all_results:
            if r.get('link'):
                existing_links.add(r['link'])
        
        for future_key, source_name in scrapers.items():
            if future_key in futures:
                try:
                    scrape_res = futures[future_key].result()
                    count = len(scrape_res)
                    logger.info(f"✅ Web {source_name} returned {count} results")
                    
                    # Only update status if JobSpy didn't already succeed for this source
                    if source_status.get(source_name, {}).get("status") in ["pending", "error", "no_results"]:
                        source_status[source_name] = {"status": "success" if count > 0 else "no_results", "count": count, "error": "" if count > 0 else "Aucun résultat"}
                    
                    new_count = 0
                    for ad in scrape_res:
                        link = ad.get('lien', '') or ad.get('link', '')
                        if link and link not in existing_links:
                            existing_links.add(link)
                            all_results.append({
                                "title": ad.get('titre') or ad.get('title', 'N/A'),
                                "company": ad.get('entreprise') or ad.get('company', 'N/A'),
                                "link": link,
                                "source": source_name,
                                "date": ad.get('date', ''),
                                "location": ad.get('location', ''),
                                "desc": ad.get('desc', ''),
                                "id": f"web_{source_name.lower()}_{len(all_results)}_{hash(link)}"
                            })
                            new_count += 1
                    logger.info(f"   Web {source_name}: {new_count} new unique results added")
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"❌ Web {source_name} Thread failed: {e}")
                    if source_status.get(source_name, {}).get("status") in ["pending", "error", "no_results"]:
                        source_status[source_name] = {"status": "error", "count": 0, "error": error_msg[:100]}

        # Collect Adzuna results
        if 'adzuna' in futures:
            try:
                adzuna_res = futures['adzuna'].result()
                count = len(adzuna_res)
                logger.info(f"✅ Adzuna returned {count} results")
                source_status["Adzuna"] = {"status": "success" if count > 0 else "no_results", "count": count, "error": "" if count > 0 else "Aucun résultat"}
                for i, ad in enumerate(adzuna_res):
                    link = ad.get('lien', '')
                    if link and link not in existing_links:
                        existing_links.add(link)
                        all_results.append({
                            "title": ad.get('titre'),
                            "company": ad.get('entreprise'),
                            "link": link,
                            "source": "Adzuna",
                            "date": ad.get('date', ''),
                            "location": ad.get('location', ''),
                            "desc": "",
                            "id": f"api_adzuna_{len(all_results)}_{hash(link)}"
                        })
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Adzuna Thread failed: {e}")
                source_status["Adzuna"] = {"status": "error", "count": 0, "error": error_msg[:100]}

        # Collect SerpApi results
        if 'serpapi' in futures:
            try:
                serpapi_res = futures['serpapi'].result()
                count = len(serpapi_res)
                logger.info(f"✅ SerpApi (Google Jobs) returned {count} results")
                source_status["Google Jobs"] = {"status": "success" if count > 0 else "no_results", "count": count, "error": "" if count > 0 else "Aucun résultat"}
                for i, ad in enumerate(serpapi_res):
                    link = ad.get('lien', '')
                    if link and link not in existing_links:
                        existing_links.add(link)
                        all_results.append({
                            "title": ad.get('titre'),
                            "company": ad.get('entreprise'),
                            "link": link,
                            "source": "Google Jobs",
                            "date": ad.get('date', ''),
                            "location": ad.get('location', ''),
                            "desc": "",
                            "id": f"api_googlejobs_{len(all_results)}_{hash(link)}"
                        })
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ SerpApi Thread failed: {e}")
                source_status["Google Jobs"] = {"status": "error", "count": 0, "error": error_msg[:100]}

        # Collect Jooble results
        if 'jooble' in futures:
            try:
                jooble_res = futures['jooble'].result()
                count = len(jooble_res)
                logger.info(f"✅ Jooble returned {count} results")
                source_status["Jooble"] = {"status": "success" if count > 0 else "no_results", "count": count, "error": "" if count > 0 else "Aucun résultat"}
                for i, ad in enumerate(jooble_res):
                    link = ad.get('lien', '')
                    if link and link not in existing_links:
                        existing_links.add(link)
                        all_results.append({
                            "title": ad.get('titre'),
                            "company": ad.get('entreprise'),
                            "link": link,
                            "source": "Jooble",
                            "date": ad.get('date', ''),
                            "location": ad.get('location', ''),
                            "desc": "",
                            "id": f"api_jooble_{len(all_results)}_{hash(link)}"
                        })
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Jooble Thread failed: {e}")
                source_status["Jooble"] = {"status": "error", "count": 0, "error": error_msg[:100]}

    # ─── Collect new French source results (Welcome to the Jungle, HelloWork, APEC, JobTeaser) ─
    new_french_sources = {
        'welcometothejungle': 'Welcome to the Jungle',
        'hellowork': 'HelloWork',
        'apec': 'APEC',
        'jobteaser': 'JobTeaser'
    }
    for future_key, source_name in new_french_sources.items():
        if future_key in futures:
            try:
                pw_res = futures[future_key].result()
                count = len(pw_res)
                logger.info(f"✅ {source_name} returned {count} results")
                source_status[source_name] = {"status": "success" if count > 0 else "no_results", "count": count, "error": "" if count > 0 else "Aucun résultat"}
                for ad in pw_res:
                    link = ad.get('lien', '') or ad.get('link', '')
                    if link and link not in existing_links:
                        existing_links.add(link)
                        all_results.append({
                            "title": ad.get('titre') or ad.get('title', 'N/A'),
                            "company": ad.get('entreprise') or ad.get('company', 'N/A'),
                            "link": link,
                            "source": source_name,
                            "date": ad.get('date', ''),
                            "location": ad.get('location', ''),
                            "desc": "",
                            "id": f"pw_{source_name.lower().replace(' ', '_')}_{len(all_results)}_{hash(link)}"
                        })
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ {source_name} Thread failed: {e}")
                source_status[source_name] = {"status": "error", "count": 0, "error": error_msg[:100]}

    # ─── Playwright Fallback ────────────────────────────────────────────────
    # When requests-based scrapers return 0 results (due to anti-bot detection),
    # run Playwright scrapers as a fallback. These use a real browser engine
    # to execute JavaScript and bypass bot detection.
    if PLAYWRIGHT_AVAILABLE and all_results:
        # Only run Playwright fallback if we have very few results (< num_ads)
        # and some sources returned 0 results
        low_result_sources = [s for s in req.selected_sources
                             if source_status.get(s, {}).get("count", 0) == 0
                             and s in ["Indeed", "LinkedIn", "Monster", "Careerbuilder", "Simplyhired"]]

        if low_result_sources and len(all_results) < req.num_ads * 2:
            logger.info(f"📡 Launching Playwright fallback for: {low_result_sources}")
            try:
                pw_jobs = scrape_all_playwright(req.query, req.location, req.num_ads)
                pw_added = 0
                for job in pw_jobs:
                    link = job.get('lien', '') or job.get('link', '')
                    if link and link not in existing_links:
                        existing_links.add(link)
                        source_label = job.get('source', 'Playwright')
                        all_results.append({
                            "title": job.get('titre') or job.get('title', 'N/A'),
                            "company": job.get('entreprise') or job.get('company', 'N/A'),
                            "link": link,
                            "source": source_label,
                            "date": job.get('date', ''),
                            "location": job.get('location', ''),
                            "desc": "",
                            "id": f"pw_{source_label.lower().replace(' ', '_')}_{len(all_results)}_{hash(link)}"
                        })
                        pw_added += 1
                        if source_label in source_status:
                            source_status[source_label] = {"status": "success", "count": source_status[source_label].get("count", 0) + 1, "error": ""}
                logger.info(f"✅ Playwright fallback added {pw_added} new unique results")
            except Exception as e:
                logger.error(f"❌ Playwright fallback failed: {e}")

    # France Travail search (outside thread pool for simplicity)
    if "France Travail" in req.selected_sources:
        ft_results = []
        if ft_client_id and ft_client_secret:
            ft_results = get_france_travail_jobs_api(req.query, limit=req.num_ads)
        if not ft_results:
            ft_results = scrape_france_travail_jobs(req.query, limit=req.num_ads)
        existing_links_ft = set(r.get('link', '') for r in all_results)
        new_ft_count = 0
        for i, ad in enumerate(ft_results):
            link = ad.get('link') or ad.get('lien', '')
            if link and link not in existing_links_ft:
                existing_links_ft.add(link)
                all_results.append({
                    "title": ad.get('title') or ad.get('titre'),
                    "company": ad.get('company') or ad.get('entreprise'),
                    "link": link,
                    "source": "France Travail",
                    "date": "",
                    "location": "",
                    "desc": "",
                    "id": f"api_francetravail_{i}_{hash(link)}"
                })
                new_ft_count += 1
        source_status["France Travail"] = {"status": "success" if new_ft_count > 0 else "no_results", "count": new_ft_count, "error": "" if new_ft_count > 0 else "Aucun résultat"}

    # ─── Collect enhanced free scraper results (from parallel execution) ────
    if 'enhanced_scrapers' in futures:
        try:
            enhanced_jobs = futures['enhanced_scrapers'].result()
            enhanced_added = 0
            for job in enhanced_jobs:
                link = job.get("lien", "")
                if link and link not in existing_links:
                    existing_links.add(link)
                    source_name = job.get("source", "Enhanced")
                    all_results.append({
                        "title": job.get("titre", "N/A"),
                        "company": job.get("entreprise", "N/A"),
                        "link": link,
                        "source": source_name,
                        "date": job.get("date", ""),
                        "location": job.get("location", ""),
                        "desc": "",
                        "id": f"enh_{source_name.lower().replace(' ', '_')}_{len(all_results)}_{hash(link)}"
                    })
                    enhanced_added += 1
                    if source_name in source_status:
                        source_status[source_name] = {"status": "success", "count": source_status[source_name].get("count", 0) + 1, "error": ""}
            logger.info(f"✅ Enhanced scrapers (parallel) added {enhanced_added} new unique results")
        except Exception as e:
            logger.error(f"❌ Enhanced scrapers (parallel) failed: {e}")

    # ─── DEDUPLICATION & ENRICHMENT ────────────────────────────────────────
    # Use AI modules to remove near-duplicates and enrich job data
    if AI_MODULES_AVAILABLE and len(all_results) > 1:
        try:
            # First deduplicate
            from ai_modules.deduplication import deduplicate_jobs
            from ai_modules.enrichment import enrich_jobs_batch
            
            before_count = len(all_results)
            all_results = deduplicate_jobs(all_results, threshold=0.88)
            logger.info(f"📊 Deduplication: {before_count} -> {len(all_results)} jobs")
            
            # Then enrich with quality scores, salary estimates, tags
            all_results = enrich_jobs_batch(all_results)
            logger.info(f"✨ Enriched {len(all_results)} jobs with quality scores and tags")
        except Exception as e:
            logger.warning(f"⚠️ Deduplication/Enrichment failed: {e}")
    else:
        # Simple quality score fallback
        for job in all_results:
            score = 50
            if job.get('title') and job.get('title') != 'N/A': score += 10
            if job.get('company') and job.get('company') != 'N/A': score += 10
            if job.get('location'): score += 10
            if job.get('desc'): score += 10
            if job.get('date'): score += 10
            job['quality_score'] = min(score, 100)

    # Sort results
    if req.sort_option in ["Plus récentes", "Most recent", "Más recientes", "Neueste", "الأحدث", "最新順", "最新发布"]:
        all_results.sort(key=lambda x: x.get('date', ''), reverse=True)
    elif req.sort_option in ["Plus proches", "Closest", "Más cercanos", "Am nächsten", "الأقرب", "近い順", "距离最近"] and req.location:
        user_loc = req.location.lower()
        all_results.sort(key=lambda x: user_loc in x.get('location', '').lower(), reverse=True)
    elif req.sort_option in ["Pertinence (IA)", "Relevance (AI)", "Relevancia (AI)", "Relevanz (KI)", "الأكثر ملاءمة (ذكاء اصطnaعي)", "関連性 (AI)", "相关性 (AI)"] and req.cv_data and all_results:
        filters = {"contrat": req.contract, "remote": req.remote}
        all_results = rank_jobs_with_ai(
            req.cv_data, 
            all_results, 
            filters, 
            ranking_engine=req.ranking_engine, 
            custom_gemini_key=req.custom_gemini_key
        )

    # Collect source statistics
    source_counts = {}
    for res in all_results:
        src = res.get('source', 'Inconnue')
        source_counts[src] = source_counts.get(src, 0) + 1

    result = {
        "results": all_results,
        "source_counts": source_counts
    }

    # Cache result for 1 hour
    if REDIS_AVAILABLE and all_results and cache_key:
        try:
            redis_client.setex(cache_key, 3600, json.dumps(result))
            logger.info(f"Cached result for query: {req.query}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    return result

@app.post("/api/generate-letter")
@limiter.limit("30/minute")  # Max 30 letter generations per minute per IP
def api_generate_letter(request: Request, req: CoverLetterRequest):
    try:
        letter = shared_generate_letter(
            cv_data=req.cv_data,
            job_title=req.job_title,
            company=req.company,
            job_description=req.job_description or "",
            target_lang=req.lang_label,
            selected_model=req.ranking_engine,
            gemini_api_key=gemini_api_key,
            xai_api_key=xai_api_key,
            groq_api_key=api_key,
            ollama_url=ollama_url,
            custom_gemini_key=req.custom_gemini_key
        )
        if not letter:
            raise HTTPException(status_code=500, detail="Cover letter generation failed.")
        return {"letter": letter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/estimate-workload")
@limiter.limit("20/minute")  # Max 20 workload estimations per minute per IP
def api_estimate_workload(request: Request, req: WorkloadEstimationRequest):
    try:
        workload = shared_estimate_workload(
            mission_description=req.mission_description,
            mission_title=req.mission_title,
            cv_data=req.cv_data,
            target_lang=req.lang_label,
            selected_model=req.ranking_engine,
            gemini_api_key=gemini_api_key,
            xai_api_key=xai_api_key,
            groq_api_key=api_key,
            ollama_url=ollama_url,
            custom_gemini_key=req.custom_gemini_key
        )
        return {"workload": workload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MockInterviewRequest(BaseModel):
    job_title: str
    job_description: str
    company: str
    cv_data: Optional[dict] = None
    interview_stage: str = "débutant"  # débutant, intermédiaire, avancé
    question_type: str = "technique"  # technique, comportemental, situationnel
    ranking_engine: str = "Groq / Llama 3.3"
    custom_gemini_key: Optional[str] = None
    lang_label: str = "français"

class MockInterviewAnswer(BaseModel):
    question: str
    answer: str
    job_title: str
    job_description: str
    cv_data: Optional[dict] = None
    ranking_engine: str = "Groq / Llama 3.3"
    custom_gemini_key: Optional[str] = None
    lang_label: str = "français"

@app.post("/api/mock-interview/question")
@limiter.limit("30/minute")
def api_mock_interview_question(request: Request, req: MockInterviewRequest):
    """Generate a personalized interview question based on job and CV."""
    try:
        prompt = f"""Tu es un recruteur expérimenté qui prépare un entretien d'embauche.
        
Poste : {req.job_title}
Entreprise : {req.company}
Description du poste : {req.job_description}

Niveau de l'entretien : {req.interview_stage}
Type de question : {req.question_type}

{f"Profil du candidat : {req.cv_data.get('metier', '')}" if req.cv_data else ""}
{f"Expérience : {req.cv_data.get('experience', '')}" if req.cv_data else ""}
{f"Compétences : {', '.join(req.cv_data.get('mots_cles', []))}" if req.cv_data else ""}

Génère UNE SEULE question d'entretien pertinente et personnalisée.
- Sois précis et contextuel
- Évite les questions génériques
- Adapte le niveau de difficulté ({req.interview_stage})
- Type : {req.question_type}

Format de réponse : juste la question, sans introduction ni explication."""

        response = call_ai_provider(
            prompt=prompt,
            selected_model=req.ranking_engine,
            gemini_api_key=gemini_api_key,
            xai_api_key=xai_api_key,
            groq_api_key=api_key,
            ollama_url=ollama_url,
            custom_gemini_key=req.custom_gemini_key
        )
        
        if not response:
            raise HTTPException(status_code=500, detail="AI provider returned empty response")
        
        return {"question": response.strip()}
    except Exception as e:
        logger.error(f"Mock interview question error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mock-interview/evaluate")
@limiter.limit("30/minute")
def api_mock_interview_evaluate(request: Request, req: MockInterviewAnswer):
    """Evaluate the candidate's answer and provide feedback."""
    try:
        prompt = f"""Tu es un recruteur expérimenté qui évalue une réponse à une question d'entretien.

Poste : {req.job_title}
Description : {req.job_description}

Question : {req.question}
Réponse du candidat : {req.answer}

{f"Profil du candidat : {req.cv_data.get('metier', '')}" if req.cv_data else ""}

Évalue cette réponse de manière constructive et détaillée :
1. Score global sur 10
2. Points forts (2-3 points)
3. Points à améliorer (2-3 points)
4. Conseil spécifique pour mieux répondre
5. Exemple de meilleure réponse (si pertinent)

Sois bienveillant mais professionnel."""

        response = call_ai_provider(
            prompt=prompt,
            selected_model=req.ranking_engine,
            gemini_api_key=gemini_api_key,
            xai_api_key=xai_api_key,
            groq_api_key=api_key,
            ollama_url=ollama_url,
            custom_gemini_key=req.custom_gemini_key
        )
        
        if not response:
            raise HTTPException(status_code=500, detail="AI provider returned empty response")
        
        return {"evaluation": response.strip()}
    except Exception as e:
        logger.error(f"Mock interview evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-cv-shared")
@limiter.limit("30/minute")
def api_analyze_cv_shared(request: Request, req: CvAnalysisRequest):
    """Analyze CV from already extracted text (shared from frontend)."""
    raise HTTPException(status_code=501, detail="Not implemented yet. Use file upload endpoint.")

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)