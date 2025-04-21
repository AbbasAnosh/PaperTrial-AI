"""
Custom exceptions for the application.
"""

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class NotFoundException(Exception):
    """Raised when a requested resource is not found."""
    pass

class ValidationError(Exception):
    """Raised when data validation fails."""
    pass

class DatabaseError(Exception):
    """Raised when a database operation fails."""
    pass

class PDFProcessingError(Exception):
    """Raised when PDF processing fails."""
    pass

class FormProcessingError(Exception):
    """Raised when form processing fails."""
    pass

class WebSocketError(Exception):
    """Raised when WebSocket operation fails."""
    pass

class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass

class ConfigurationError(Exception):
    """Raised when there is a configuration error."""
    pass 