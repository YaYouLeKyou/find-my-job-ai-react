"""
Jobs Controller - Clean Architecture Implementation
Handles job search endpoints with proper security and validation
"""

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import constr, conint
from typing import Optional
import logging
import json
import asyncio

from backend.app.config.settings import settings
from backend.app.core.services.job_search_service import JobSearchService
from backend.app.core.dto.search_params import SearchParams
from backend.app.core.exceptions import JobSearchError, ValidationError
from backend.app.infrastructure.repositories.job_repository import JobRepository

# Configure logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

# Initialize service with dependency injection
job_repository = JobRepository()
job_search_service = JobSearchService(job_repository)

@router.get("/stream")
async def stream_jobs(
    request: Request,
    query: constr(min_length=3, max_length=100, strip_whitespace=True) = Query(..., description="Search query"),
    location: constr(min_length=2, max_length=50, strip_whitespace=True) = Query("France", description="Location"),
    limit: conint(ge=10, le=100) = Query(50, description="Maximum results per source"),
    contract: str = Query("CDI", description="Contract type"),
    remote: bool = Query(False, description="Remote jobs only"),
    selected_sources: str = Query("LinkedIn,France Travail,Google Jobs", description="Comma-separated list of sources"),
    ranking_engine: str = Query("Groq / Llama 3.3", description="AI ranking engine"),
    cv_data: Optional[str] = Query(None, description="JSON string of CV data")
):
    """
    Stream job search results using Server-Sent Events (SSE) with proper validation

    Args:
        query: Search query (min 3 chars, max 100)
        location: Location for job search
        limit: Maximum results per source (10-100)
        contract: Contract type filter
        remote: Remote jobs only filter
        selected_sources: Comma-separated list of sources
        ranking_engine: AI ranking engine
        cv_data: Optional CV data for AI scoring

    Returns:
        StreamingResponse with SSE events
    """
    try:
        # Parse CV data if provided
        cv_data_dict = None
        if cv_data:
            try:
                cv_data_dict = json.loads(cv_data)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid CV data JSON: {str(e)}")

        # Build search parameters
        sources_list = [s.strip() for s in selected_sources.split(",") if s.strip()]
        params = SearchParams(
            query=query,
            location=location,
            sources=sources_list,
            limit=limit,
            contract=contract,
            remote=remote,
            cv_data=cv_data_dict,
            ranking_engine=ranking_engine
        )

        # Stream jobs using the service
        return await _stream_jobs_response(params)

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return StreamingResponse(
            _error_stream(f"Validation error: {str(e)}"),
            media_type="text/event-stream"
        )
    except JobSearchError as e:
        logger.error(f"Job search failed: {e}")
        return StreamingResponse(
            _error_stream(f"Job search failed: {str(e)}"),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.exception("Unexpected error in job search")
        return StreamingResponse(
            _error_stream("An unexpected error occurred"),
            media_type="text/event-stream"
        )

async def _stream_jobs_response(params: SearchParams):
    """Generate SSE stream response for job search"""
    async def event_generator():
        try:
            logger.info(f"[SSE] Starting job search: query={params.query!r} location={params.location!r}")

            # Send started event
            yield f"data: {json.dumps({'type': 'STARTED', 'query': params.query, 'sources': params.sources})}\n\n"
            await asyncio.sleep(0.1)

            # Search jobs using the service
            jobs = await job_search_service.search_jobs(params)

            # Send progress events
            yield f"data: {json.dumps({'type': 'PROGRESS', 'progress': 50, 'message': 'Searching sources...'})}\n\n"
            await asyncio.sleep(0.1)

            # Send results
            yield f"data: {json.dumps({'type': 'COMPLETED', 'jobs': [job.dict() for job in jobs], 'progress': 100})}\n\n"
            yield "data: [DONE]\n\n"

            logger.info(f"[SSE] Completed job search: {len(jobs)} results found")

        except Exception as e:
            logger.error(f"[SSE] Error: {e}")
            yield f"data: {json.dumps({'type': 'ERROR', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

async def _error_stream(message: str):
    """Generate error stream"""
    yield f"data: {json.dumps({'type': 'ERROR', 'message': message})}\n\n"
    yield "data: [DONE]\n\n"