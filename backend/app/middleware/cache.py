from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.cache_service import CacheService
from app.config.redis import get_redis_client
import hashlib
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for caching responses"""
    
    def __init__(self, app):
        super().__init__(app)
        redis_client = get_redis_client()
        self.cache_service = CacheService(redis_client) if redis_client else None
        
    async def dispatch(self, request: Request, call_next):
        if not self.cache_service:
            return await call_next(request)
            
        # Skip caching for non-GET requests
        if request.method != "GET":
            return await call_next(request)
            
        # Generate cache key
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items()))
        ]
        cache_key = hashlib.md5(
            ":".join(key_parts).encode()
        ).hexdigest()
        
        # Try to get from cache
        cached = self.cache_service.get(cache_key)
        if cached is not None:
            return Response(
                content=cached["content"],
                status_code=cached["status_code"],
                headers=cached["headers"],
                media_type=cached["media_type"]
            )
            
        # Get response
        response = await call_next(request)
        
        # Cache response if successful
        if 200 <= response.status_code < 300:
            # Add tags based on path segments
            tags = self._get_tags_from_path(request.url.path)
            
            # Store response in cache
            self.cache_service.set(
                cache_key,
                {
                    "content": response.body.decode(),
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type
                },
                ttl=3600  # 1 hour
            )
            
            # Add tags to the cache key
            if tags:
                self.cache_service.tags.add_tags(cache_key, tags)
                
            # Broadcast update to other instances
            self.cache_service.distributed.broadcast_update(
                cache_key,
                {
                    "content": response.body.decode(),
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type
                },
                ttl=3600
            )
            
        return response
        
    def _get_tags_from_path(self, path: str) -> List[str]:
        """Extract tags from URL path segments"""
        # Remove leading slash and split path
        segments = path.strip('/').split('/')
        
        # Create tags from path segments
        tags = []
        for i, segment in enumerate(segments):
            if segment:
                # Add individual segment as tag
                tags.append(f"path:{segment}")
                
                # Add path hierarchy as tags
                if i > 0:
                    hierarchy = '/'.join(segments[:i+1])
                    tags.append(f"path_hierarchy:{hierarchy}")
                    
        return tags 