from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    """Standard error response model"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class APIError(HTTPException):
    """Base API error class"""
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status_code,
            detail=ErrorResponse(
                code=code,
                message=message,
                details=details
            ).dict()
        )

class AuthenticationError(APIError):
    """Authentication related errors"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTH_ERROR",
            message=message,
            details=details
        )

class AuthorizationError(APIError):
    """Authorization related errors"""
    def __init__(self, message: str = "Not authorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message,
            details=details
        )

class ValidationError(APIError):
    """Validation related errors"""
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message=message,
            details=details
        )

class NotFoundError(APIError):
    """Resource not found errors"""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=message,
            details=details
        )

# Alias for NotFoundError for backward compatibility
NotFoundException = NotFoundError

class ProcessingError(APIError):
    """Document processing related errors"""
    def __init__(self, message: str = "Processing failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="PROCESSING_ERROR",
            message=message,
            details=details
        )

class DatabaseError(APIError):
    """Database related errors"""
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="DATABASE_ERROR",
            message=message,
            details=details
        ) 