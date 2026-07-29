"""
API Routes Configuration
Centralized route management for the application
"""
from fastapi import APIRouter
from .controllers import jobs_controller

# Create main router
main_router = APIRouter()

# Include sub-routers
main_router.include_router(
    jobs_controller.router,
    prefix="/jobs",
    tags=["jobs"]
)

# Health check endpoint
@main_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}