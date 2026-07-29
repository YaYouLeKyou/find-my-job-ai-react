"""
Custom Exceptions - Core Layer
Part of Clean Architecture - Domain Exceptions
"""
class JobSearchError(Exception):
    """Base exception for job search related errors"""

    def __init__(self, message: str, original_exception: Exception | None = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(message)

    def __str__(self) -> str:
        if self.original_exception:
            return f"{self.message} (Caused by: {str(self.original_exception)})"
        return self.message

class ValidationError(JobSearchError):
    """Exception for validation failures"""

    def __init__(self, field: str, message: str):
        super().__init__(f"Validation failed for {field}: {message}")

class SourceUnavailableError(JobSearchError):
    """Exception when a job source is unavailable"""

    def __init__(self, source_name: str, reason: str = "Unknown"):
        super().__init__(f"Source '{source_name}' is unavailable: {reason}")

class QuotaExceededError(JobSearchError):
    """Exception when API quota is exceeded"""

    def __init__(self, source_name: str, quota_type: str = "requests"):
        super().__init__(f"API quota exceeded for {source_name} ({quota_type})")