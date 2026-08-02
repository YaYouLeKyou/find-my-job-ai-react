"""
Cache Management API Endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import logging
from typing import Optional

# Import configuration and services
from app.config import get_settings
from app.services.cache import clear_search_cache, get_cache_stats

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["cache"])

@router.delete("/")
async def clear_cache():
    """
    Clear the search cache - both local and server-side.

    This endpoint:
    1. Clears local cache (if any)
    2. Clears server-side cache (Redis/BDD)
    3. Returns success status
    """
    try:
        logger.info("[CACHE] Clearing search cache...")

        # Clear server-side cache
        settings = get_settings()
        cache_cleared = clear_search_cache()

        if cache_cleared:
            logger.info("[CACHE] Search cache cleared successfully")
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Cache vidé avec succès",
                    "cache_cleared": cache_cleared
                },
                status_code=200
            )
        else:
            logger.warning("[CACHE] No cache found to clear")
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Aucun cache trouvé à vider",
                    "cache_cleared": False
                },
                status_code=200
            )

    except Exception as e:
        logger.error(f"[CACHE] Error clearing cache: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du vidage du cache: {str(e)}"
        )

@router.get("/stats")
async def get_cache_stats_endpoint():
    """
    Get cache statistics - number of cached items, size, etc.
    """
    try:
        stats = get_cache_stats()
        return JSONResponse(
            content={
                "success": True,
                "stats": stats
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"[CACHE] Error getting cache stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération des statistiques du cache: {str(e)}"
        )