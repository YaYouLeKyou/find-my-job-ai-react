"""
FindMyJobAI Backend - Main FastAPI Application
Endpoint: /api/jobs/stream (StreamingResponse)
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Ensure the parent directory is in sys.path so 'shared' module is found
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

# Import scrapers
from app.scrapers.api_sources import get_france_travail_source, get_france_travail_rss_source, get_adzuna_source, get_google_jobs_source, get_jooble_source, get_apify_source
from app.scrapers.web_sources import (
    scrape_indeed,
    scrape_linkedin,
    scrape_monster,
    scrape_hellowork,
    scrape_google_jobs,
    scrape_jobspy,
    scrape_enhanced,
)

from shared.ai import call_ai_provider, analyze_cv_with_fallback, generate_cover_letter
from shared.utils import extract_text_from_pdf
import io

import httpx


import logging
import json
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load settings
settings = get_settings()

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

# CORS middleware
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS.split(",")
logger.info(f"[CORS] Configured allowed origins: {ALLOWED_ORIGINS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helper Functions ────────────────────────────────────────────────────────

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
                    result = await asyncio.to_thread(adzuna_source.search_jobs, q, l, n)
                    logger.info(f"[SSE] Adzuna returned {len(result)} jobs")
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
                result = scrape_google_jobs(q, l, n, settings.SERPAPI_KEY)
                logger.info(f"[SSE] Google Jobs returned {len(result)} jobs")
                return result
            except Exception as e:
                logger.error(f"[SSE] Google Jobs search error: {e}", exc_info=True)
                return []
        source_registry['Google Jobs'] = _google_jobs_search

    if "JobSpy" in selected_sources:
        async def _jobspy_search(q: str, l: str, n: int):
            try:
                logger.info(f"[SSE] JobSpy search start query={q!r} location={l!r} limit={n}")
                result = scrape_jobspy(q, l, n)
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
                return await asyncio.to_thread(jooble_source.search_jobs, q, l, n)
            source_registry['Jooble'] = _jooble_search

    if "Apify" in selected_sources:
        apify_source = get_apify_source()
        if apify_source:
            async def _apify_search(q, l, n):
                return await asyncio.to_thread(apify_source.search_jobs, q, l, n)
            source_registry['Apify'] = _apify_search

    return source_registry


# ─── Main Streaming Endpoint ─────────────────────────────────────────────────

@app.get("/api/jobs/stream")
async def api_jobs_stream(
    request: Request,
    query: str = Query(...),
    location: str = Query("Paris, France"),
    num_ads: int = Query(10),
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
    num_ads: int = Query(10),
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
    """Compatibility route for the legacy frontend."""
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
    num_ads: int,
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

    # Clamp num_ads to 5-100 per source (default 10)
    per_source_limit = max(5, min(num_ads, 100))

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
            async for result in aggregator.search_parallel_streaming(
                sources=source_registry,
                query=query,
                location=location,
                limit=per_source_limit,
                target_jobs=target_total,
                source_timeouts=source_timeouts,
            ):
                if result.jobs:
                    all_jobs.extend(result.jobs)

                source_results[result.source_name] = result
                sources_done += 1

                status = "completed" if result.success else "error"
                jobs_count = len(result.jobs) if result.jobs else 0
                progress = min(100, int(sources_done / total_sources * 100)) if total_sources > 0 else 100
                source_progress = min(100, int(sources_done / total_sources * 100)) if total_sources > 0 else 100

                logger.info(
                    f"[SSE] source={result.source_name} status={status} jobs={jobs_count} duration={result.execution_time} error={result.error} progress={progress} sources_done={sources_done}/{total_sources}"
                )

                if result.jobs and jobs_count > 0:
                    logger.info(f"[SSE] source={result.source_name} sample_job={result.jobs[0].get('titre', 'N/A')}")

                yield f"data: {json.dumps({'type': 'PROGRESS', 'progress': progress, 'total_so_far': len(all_jobs), 'target': per_source_limit, 'source': result.source_name, 'status': status, 'jobs': result.jobs, 'sources_done': sources_done, 'total_sources': total_sources, 'source_progress': source_progress, 'execution_time': result.execution_time})}\n\n"
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
                            sig = f"{(job.get('title') or job.get('titre') or '').lower().strip()}|{(job.get('company') or job.get('entreprise') or '').lower().strip()}|{(job.get('link') or job.get('lien') or '').lower().strip()}"
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
                }

            # Build final jobs list with scores (if CV data was provided)
            if cv_data_dict and scored_jobs_map:
                final_jobs = []
                for job in all_jobs:
                    sig = f"{(job.get('title') or job.get('titre') or '').lower().strip()}|{(job.get('company') or job.get('entreprise') or '').lower().strip()}|{(job.get('link') or job.get('lien') or '').lower().strip()}"
                    if sig in scored_jobs_map:
                        final_jobs.append(scored_jobs_map[sig])
                    else:
                        final_jobs.append(job)
                final_jobs.sort(key=lambda x: x.get('pertinence_ai', 0), reverse=True)
            else:
                final_jobs = all_jobs

            # Normalize all jobs for frontend
            normalized_jobs = normalize_jobs_for_frontend(final_jobs)

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


# ─── Run with Uvicorn ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
