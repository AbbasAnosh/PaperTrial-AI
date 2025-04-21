from fastapi import APIRouter, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import logging
from app.core.errors import APIError

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging request/response information"""
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url}")
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Response: {request.method} {request.url} "
                f"Status: {response.status_code} "
                f"Time: {process_time:.2f}s"
            )
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Error: {request.method} {request.url} "
                f"Time: {process_time:.2f}s "
                f"Error: {str(e)}"
            )
            raise

class BaseRouter(APIRouter):
    """Base router with common functionality"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.middleware = [LoggingMiddleware]
    
    def add_api_route(self, path: str, endpoint: Callable, **kwargs):
        """Add route with standard error handling"""
        async def error_handler(*args, **kwargs):
            try:
                return await endpoint(*args, **kwargs)
            except APIError:
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}", exc_info=True)
                raise APIError(
                    status_code=500,
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred",
                    details={"error": str(e)}
                )
        
        return super().add_api_route(path, error_handler, **kwargs) 