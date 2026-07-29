"""
Core Package - Clean Architecture Domain Layer
This package contains the pure business logic and domain models
that are independent of frameworks and external systems.
"""

# Export key components for easy importing
from .models.job import Job
from .repositories.job_repository import JobRepositoryInterface
from .services.job_search_service import JobSearchService
from .exceptions.job_search_error import JobSearchError, ValidationError, SourceUnavailableError, QuotaExceededError
from .dto.search_params import SearchParams

__all__ = [
    'Job',
    'JobRepositoryInterface',
    'JobSearchService',
    'JobSearchError',
    'ValidationError',
    'SourceUnavailableError',
    'QuotaExceededError',
    'SearchParams'
]