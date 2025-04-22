from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.security_service import SecurityService
from app.config.redis import get_redis_client
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for handling API key authentication and request signing"""
    
    def __init__(self, app):
        super().__init__(app)
        redis_client = get_redis_client()
        self.security_service = SecurityService(redis_client) if redis_client else None
        
    async def dispatch(self, request: Request, call_next):
        if not self.security_service:
            return await call_next(request)
            
        # Get client IP
        client_ip = request.client.host if request.client else None
        
        # Check IP blacklist
        if client_ip and self.security_service.is_ip_blacklisted(client_ip):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "IP address is blacklisted"}
            )
            
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "API key is required"}
            )
            
        # Validate API key
        is_valid, error = self.security_service.validate_api_key(api_key)
        if not is_valid:
            # Blacklist IP after multiple failed attempts
            if client_ip:
                self.security_service.blacklist_ip(client_ip)
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": error or "Invalid API key"}
            )
            
        # Check if request signing is required
        if request.headers.get("X-Require-Signature") == "true":
            # Get signature headers
            timestamp = request.headers.get("X-Timestamp")
            signature = request.headers.get("X-Signature")
            
            if not timestamp or not signature:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Request signature is required"}
                )
                
            # Get request body
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.json()
                except:
                    body = {}
                    
            # Validate signature
            is_valid, error = self.security_service.validate_request_signature(
                api_key=api_key,
                timestamp=timestamp,
                signature=signature,
                method=request.method,
                path=request.url.path,
                body=body
            )
            
            if not is_valid:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": error or "Invalid request signature"}
                )
                
        # Process request
        response = await call_next(request)
        return response 