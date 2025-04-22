"""
Error handling module for the application.

This module defines custom exceptions and error handlers for the application.
It provides structured error responses and logging for different types of errors.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
import traceback
import json
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base exception class for application errors."""
    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class ValidationError(AppError):
    """Exception raised for validation errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class AuthenticationError(AppError):
    """Exception raised for authentication errors."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class AuthorizationError(AppError):
    """Exception raised for authorization errors."""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN
        )

class NotFoundError(AppError):
    """Exception raised when a resource is not found."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND
        )

class RateLimitError(AppError):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {"retry_after": retry_after} if retry_after else None
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )

class DatabaseError(AppError):
    """Exception raised for database errors."""
    def __init__(self, message: str = "Database error occurred"):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ExternalServiceError(AppError):
    """Exception raised for external service errors."""
    def __init__(self, message: str, service: str):
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"service": service}
        )

def log_error(error: Exception, request: Request, include_traceback: bool = True) -> None:
    """Log error details with structured format."""
    error_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else None,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    if isinstance(error, AppError):
        error_data.update({
            "error_code": error.code,
            "status_code": error.status_code,
            "details": error.details
        })

    if include_traceback:
        error_data["traceback"] = traceback.format_exc()

    # Log as JSON for better parsing
    logger.error(json.dumps(error_data))

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle application-specific errors."""
    log_error(exc, request)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors."""
    log_error(exc, request, include_traceback=False)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation error",
                "details": exc.errors()
            }
        }
    )

async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    log_error(exc, request, include_traceback=False)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.detail,
                "message": str(exc.detail),
                "details": {}
            }
        }
    )

async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions."""
    log_error(exc, request)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {"type": type(exc).__name__}
            }
        }
    )

def setup_exception_handlers(app):
    """Set up exception handlers for the FastAPI application."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.add_exception_handler(Exception, general_error_handler) 