"""
Custom exceptions for the FindMyJobAI application
"""

class JobSearchError(Exception):
    """Raised when job search fails"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class ValidationError(Exception):
    """Raised when input validation fails"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class APIError(Exception):
    """Raised when external API calls fail"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(f"{message} (Status: {status_code})" if status_code else message)

class RateLimitExceededError(Exception):
    """Raised when rate limits are exceeded"""
    def __init__(self, message: str = "Rate limit exceeded"):
        self.message = message
        super().__init__(message)

class AuthenticationError(Exception):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(message)