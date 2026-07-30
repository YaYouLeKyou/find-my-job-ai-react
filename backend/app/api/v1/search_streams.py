"""
Backend endpoints for Freelance and Worker search streams.
Extends the existing job search stream with agent-specific endpoints.
"""
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.scrapers.bypass_strategies import (
    generate_relaxed_queries,
    get_rotated_headers,
    get_jitter_delay,
    optimize_location_for_api,
    get_optimal_limit,
    search_with_query_relaxation,
    normalize_and_deduplicate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])

# =============================================================================
# FREELANCE SEARCH STREAM
# =============================================================================

@router.get("/search-freelance-stream")
async def freelance_search_stream(
    request: Request,
    query: str = Query(...),
    location: str = Query("France"),
    num_ads: int = Query(50),
    contract: str = Query("Freelance"),
    remote: bool = Query(False),
    global_search: bool = Query(False),
    selected_sources: str = Query(""),
    sort_option: str = Query("Pertinence (IA)"),
    ranking_engine: str = Query("Groq / Llama 3.3"),
    custom_gemini_key: str = Query(None),
    cv_data: str = Query(None),
    tjm_min: Optional[int] = Query(None),
    tjm_max: Optional[int] = Query(None),
):
    """
    SSE stream for freelance mission search.
    Uses the same resilient search logic as job search but with freelance-specific optimizations.
    """
    from app.main import _stream_jobs

    # Build freelance-optimized query
    freelance_query = f"freelance mission {query}"
    
    # Map freelance sources to backend-supported sources
    source_map = {
        'Malt': 'Indeed',
        'Upwork': 'LinkedIn',
        'Freelancer': 'Monster',
        'Toptal': 'Google Jobs',
        'Codeur.com': 'Jooble',
    }
    
    sources_list = [s.strip() for s in selected_sources.split(",") if s.strip()]
    mapped_sources = []
    for s in sources_list:
        if s in source_map:
            mapped_sources.append(source_map[s])
        else:
            mapped_sources.append(s)
    # Add original freelance names for backend matching
    for s in sources_list:
        if s not in mapped_sources:
            mapped_sources.append(s)
    
    mapped_sources_str = ",".join(mapped_sources)

    # Delegate to the main streaming function with freelance params
    return await _stream_jobs(
        query=freelance_query,
        location=location,
        num_ads=num_ads,
        contract="Freelance",
        remote=remote,
        selected_sources=mapped_sources_str,
        ranking_engine=ranking_engine,
        custom_gemini_key=custom_gemini_key,
        cv_data=cv_data,
    )


# =============================================================================
# WORKER SEARCH STREAM
# =============================================================================

@router.get("/search-worker-stream")
async def worker_search_stream(
    request: Request,
    query: str = Query(...),
    location: str = Query("France"),
    num_ads: int = Query(50),
    contract: str = Query("CDI"),
    remote: bool = Query(False),
    global_search: bool = Query(False),
    selected_sources: str = Query(""),
    sort_option: str = Query("Pertinence (IA)"),
    ranking_engine: str = Query("Groq / Llama 3.3"),
    custom_gemini_key: str = Query(None),
    cv_data: str = Query(None),
    experience: Optional[str] = Query(None),
    salary_min: Optional[int] = Query(None),
    salary_max: Optional[int] = Query(None),
):
    """
    SSE stream for worker/candidate search.
    Uses the same resilient search logic as job search but with worker-specific optimizations.
    """
    from app.main import _stream_jobs

    # Build worker-optimized query
    worker_query = f"recrute {query} {contract}"
    if experience:
        worker_query += f" {experience}"

    # Worker sources map to backend-supported sources
    source_map = {
        'Apec': 'Indeed',
        'LinkedIn': 'LinkedIn',
        'Indeed': 'Indeed',
        'France Travail': 'France Travail',
        'Monster': 'Monster',
    }
    
    sources_list = [s.strip() for s in selected_sources.split(",") if s.strip()]
    mapped_sources = []
    for s in sources_list:
        if s in source_map:
            mapped_sources.append(source_map[s])
        else:
            mapped_sources.append(s)
    
    mapped_sources_str = ",".join(mapped_sources)

    # Delegate to the main streaming function with worker params
    return await _stream_jobs(
        query=worker_query,
        location=location,
        num_ads=num_ads,
        contract=contract,
        remote=remote,
        selected_sources=mapped_sources_str,
        ranking_engine=ranking_engine,
        custom_gemini_key=custom_gemini_key,
        cv_data=cv_data,
    )