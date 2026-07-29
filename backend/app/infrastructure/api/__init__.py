"""
API Infrastructure Package
Contains FastAPI controllers, routes, and API-related components
"""

# Export main router for easy importing
from .routes import main_router

__all__ = ['main_router']