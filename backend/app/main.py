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

from shared.ai import call_ai_provider, analyze_cv_with_fallback
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
    """Return timeout in seconds based on source type."""
    return 6.0


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

        def _search_france_travail_with_fallback(q: str, l: str, n: int):
            api_jobs = []
            if ft_source:
                try:
                    api_jobs = asyncio.run(ft_source.search_jobs(q, l, n))
                    if api_jobs:
                        logger.info(f"[SSE] France Travail API returned {len(api_jobs)} jobs")
                        return api_jobs
                except Exception as e:
                    logger.warning(f"[SSE] France Travail API failed, falling back to RSS: {e}")
            if ft_rss_source:
                try:
                    return asyncio.run(ft_rss_source(q, l, n))
                except Exception as e:
                    logger.error(f"[SSE] France Travail RSS fallback failed: {e}")
            return api_jobs

        source_registry['France Travail'] = _search_france_travail_with_fallback
    
    if "Adzuna" in selected_sources:
        adzuna_source = get_adzuna_source()
        if adzuna_source:
            source_registry['Adzuna'] = lambda q, l, n: asyncio.run(
                adzuna_source.search_jobs(q, l, n)
            )
    
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
        source_registry['Google Jobs'] = lambda q, l, n: scrape_google_jobs(q, l, n, settings.SERPAPI_KEY)
    
    if "JobSpy" in selected_sources:
        source_registry['JobSpy'] = lambda q, l, n: scrape_jobspy(q, l, n)
    
    if "Enhanced" in selected_sources:
        source_registry['Enhanced'] = lambda q, l, n: scrape_enhanced(q, l, n)
    
    if "Jooble" in selected_sources:
        jooble_source = get_jooble_source()
        if jooble_source:
            source_registry['Jooble'] = lambda q, l, n: asyncio.run(
                jooble_source.search_jobs(q, l, n)
            )
    
    if "Apify" in selected_sources:
        apify_source = get_apify_source()
        if apify_source:
            source_registry['Apify'] = lambda q, l, n: asyncio.run(
                apify_source.search_jobs(q, l, n)
            )
    
    return source_registry


# ─── Main Streaming Endpoint ─────────────────────────────────────────────────

@app.get("/api/jobs/stream")
async def api_jobs_stream(
    request: Request,
    query: str = Query(...),
    location: str = Query("Paris, France"),
    num_ads: int = Query(100),
    contract: str = Query("CDI"),
    remote: bool = Query(False),
    selected_sources: str = Query(""),
    ranking_engine: str = Query("Groq / Llama 3.3"),
    custom_gemini_key: str = Query(None),
    cv_data: str = Query(None)
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
    )


@app.get("/api/search-jobs-stream")
async def legacy_api_search_jobs_stream(
    request: Request,
    query: str = Query(...),
    location: str = Query("Paris, France"),
    num_ads: int = Query(100),
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
):
    sources_list = [s.strip() for s in selected_sources.split(",") if s.strip()]
    cv_data_dict = None
    if cv_data:
        try:
            cv_data_dict = json.loads(cv_data)
        except Exception:
            pass

    async def event_generator():
        try:
            logger.info(f"[SSE] START query={query!r} location={location!r} sources={sources_list} ranking={ranking_engine}")
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
            
            # STREAMING: Emit results as each source completes
            all_jobs = []
            source_results = {}
            emit_count = 0
            
            async for result in aggregator.search_parallel_streaming(
                sources=source_registry,
                query=query,
                location=location,
                limit=max(num_ads, 50),  # Ensure at least 50 results per source
            ):
                # Add jobs to total
                if result.jobs:
                    all_jobs.extend(result.jobs)
                
                # Store result for final status
                source_results[result.source_name] = result
                
                # Emit PROGRESS event IMMEDIATELY for this source
                status = "completed" if result.success else "error"
                jobs_count = len(result.jobs) if result.jobs else 0
                
                logger.info(
                    f"[SSE] source={result.source_name} status={status} jobs={jobs_count} duration={result.execution_time} error={result.error}"
                )
                
                # Log details for debugging
                if result.jobs and jobs_count > 0:
                    logger.info(f"[SSE] source={result.source_name} sample_job={result.jobs[0].get('titre', 'N/A')}")
                
                # Emit event immediately
                yield f"data: {json.dumps({'type': 'PROGRESS', 'progress': 100, 'source': result.source_name, 'status': status, 'jobs': result.jobs})}\n\n"
                emit_count += 1

            logger.info(f"[SSE] collected total_jobs={len(all_jobs)} sources={emit_count}")

            if all_jobs and cv_data_dict:
                try:
                    if not cv_data_dict.get("is_fallback"):
                        logger.info(f"[SSE] TF-IDF scoring start jobs={len(all_jobs)}")
                        all_jobs = score_jobs(cv_data_dict, all_jobs, fast=True)
                    else:
                        logger.info("[SSE] Fallback mode detected, skipping AI/TF-IDF scoring")
                    logger.info(f"[SSE] TF-IDF scoring done jobs={len(all_jobs)}")
                except Exception as e:
                    logger.error(f"[SSE] TF-IDF scoring failed: {e}")

            normalized_jobs = normalize_jobs_for_frontend(all_jobs, location)
            logger.info(f"[SSE] normalized_jobs={len(normalized_jobs)}")
            yield f"data: {json.dumps({'type': 'SCORES_UPDATED', 'jobs': normalized_jobs, 'progress': 100})}\n\n"

            source_status = {name: result.to_dict() for name, result in source_results.items()}
            yield f"data: {json.dumps({'type': 'COMPLETED', 'jobs': normalized_jobs, 'source_status': source_status, 'progress': 100})}\n\n"
            logger.info(f"[SSE] COMPLETED query={query!r} jobs={len(normalized_jobs)}")
        except Exception as e:
            logger.exception("[SSE] GLOBAL_ERROR")
            yield f"data: {json.dumps({'type': 'ERROR', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
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