class MasscanWebException(Exception):
    """Base exception for all Masscan Web errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code

class ScanError(MasscanWebException):
    """Raised when there's an error during scan execution."""
    pass

class ValidationError(MasscanWebException):
    """Raised when input validation fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class ResourceNotFoundError(MasscanWebException):
    """Raised when a requested resource is not found."""
    def __init__(self, message: str):
        super().__init__(message, status_code=404)

class RateLimitExceededError(MasscanWebException):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)