"""
FastAPI SSE Job Search Endpoint
Real-time job search with Server-Sent Events
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
import logging

# Import job sources
from app.scrapers.api_sources import (
    get_france_travail_source, get_france_travail_rss_source,
    get_adzuna_source, get_google_jobs_source,
    get_jooble_source, get_apify_source
)
from app.services.aggregator import SearchAggregator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["jobs"],
    responses={404: {"description": "Not found"}},
)

def generate_job_search_stream(query: str, location: str = "France", limit: int = 50):
    """
    Generate Server-Sent Events stream for job search.
    Simulates the 3-step workflow with proper timing.
    """

    async def event_generator():
        nonlocal query, location, limit

        try:
            # Step 1: Initialize and send start event
            yield f"data: {json.dumps({'type': 'progress', 'stage': 0, 'progress': 0, 'message': 'Initialisation de la recherche...'})}\n\n"
            await asyncio.sleep(0.1)

            # Step 2: Partner APIs (0.5s) - France Travail, Adzuna
            yield f"data: {json.dumps({'type': 'progress', 'stage': 1, 'progress': 10, 'message': 'Interrogation des APIs partenaires...'})}\n\n"

            # Get sources
            ft_source = get_france_travail_source()
            ft_rss_source = get_france_travail_rss_source()
            adzuna_source = get_adzuna_source()
            google_source = get_google_jobs_source()
            jooble_source = get_jooble_source()
            apify_source = get_apify_source()

            # Build source registry
            source_registry = {}
            if ft_source:
                source_registry['France Travail'] = ft_source.search_jobs
            if adzuna_source:
                source_registry['Adzuna'] = adzuna_source.search_jobs

            # Execute partner APIs
            aggregator = SearchAggregator(max_workers=2, timeout_per_source=60.0)
            partner_jobs, partner_results = await aggregator.search_parallel(
                source_registry, query, location, limit
            )

            # Send partner API results
            yield f"data: {json.dumps({'type': 'jobs_data', 'source': 'partners', 'jobs': partner_jobs, 'timestamp': datetime.now().isoformat()})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'stage': 1, 'progress': 30, 'message': 'APIs partenaires terminées!'})}\n\n"
            await asyncio.sleep(0.5)

            # Step 3: Web Scrapers (2.0s) - Google Jobs, Jooble, Apify
            yield f"data: {json.dumps({'type': 'progress', 'stage': 2, 'progress': 40, 'message': 'Scraping des sites web en cours...'})}\n\n"

            # Build scraper registry
            scraper_registry = {}
            if google_source:
                scraper_registry['Google Jobs'] = google_source.search_jobs
            if jooble_source:
                scraper_registry['Jooble'] = jooble_source.search_jobs
            if apify_source:
                scraper_registry['LinkedIn'] = apify_source.search_jobs

            # Execute scrapers
            scraper_jobs, scraper_results = await aggregator.search_parallel(
                scraper_registry, query, location, limit
            )

            # Send scraper results
            yield f"data: {json.dumps({'type': 'jobs_data', 'source': 'scrapers', 'jobs': scraper_jobs, 'timestamp': datetime.now().isoformat()})}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'stage': 2, 'progress': 80, 'message': 'Scraping terminé!'})}\n\n"
            await asyncio.sleep(1.5)

            # Step 4: AI Sorting (2.5s)
            yield f"data: {json.dumps({'type': 'progress', 'stage': 3, 'progress': 85, 'message': 'Optimisation IA en cours...'})}\n\n"

            # Combine all jobs
            all_jobs = partner_jobs + scraper_jobs

            # Simulate AI sorting (in a real app, this would call your AI service)
            await asyncio.sleep(0.5)

            # Create sorted order (simple example: sort by source priority)
            sorted_jobs = sorted(all_jobs, key=lambda x: (
                0 if x.get('source') == 'France Travail' else
                1 if x.get('source') == 'Adzuna' else
                2 if x.get('source') == 'Google Jobs' else
                3
            ))

            # Send sorted order
            sorted_ids = [job.get('id', f"job_{i}") for i, job in enumerate(sorted_jobs)]
            yield f"data: {json.dumps({'type': 'jobs_sorted', 'order': sorted_ids, 'timestamp': datetime.now().isoformat()})}\n\n"
            yield f"data: {json.dumps({'type': 'jobs_data', 'source': 'sorted', 'jobs': sorted_jobs, 'timestamp': datetime.now().isoformat()})}\n\n"

            # Final completion
            yield f"data: {json.dumps({'type': 'progress', 'stage': 3, 'progress': 100, 'message': 'Recherche terminée!'})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'total_jobs': len(all_jobs), 'timestamp': datetime.now().isoformat()})}\n\n"

            logger.info(f"SSE stream completed: {len(all_jobs)} jobs found for '{query}'")

        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            # Close the connection
            yield "data: [DONE]\n\n"

    return event_generator()

@router.get("/stream")
async def stream_jobs(
    request: Request,
    query: str = Query(..., min_length=3, description="Search query"),
    location: str = Query("France", description="Location"),
    limit: int = Query(50, description="Maximum results per source")
):
    """
    Stream job search results using Server-Sent Events.

    The stream follows a 3-step workflow:
    1. [0.5s] Partner APIs (France Travail, Adzuna) - Immediate results
    2. [2.0s] Web Scrapers (Google Jobs, Jooble, Apify) - Progressive results
    3. [2.5s] AI Sorting - Optimized ordering

    Events emitted:
    - progress: Workflow stage updates (0-100%)
    - jobs_data: Job listings as they become available
    - jobs_sorted: Optimized job ordering from AI
    - complete: Stream completion
    - error: Error information
    """
    return StreamingResponse(
        generate_job_search_stream(query, location, limit),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )