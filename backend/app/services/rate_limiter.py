from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, List, Union
from redis import Redis
import json
import hashlib
from enum import Enum
import time
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    FIXED_WINDOW = "fixed-window"
    SLIDING_WINDOW = "sliding-window"
    TOKEN_BUCKET = "token-bucket"
    LEAKY_BUCKET = "leaky-bucket"

class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.window_size = 60  # 1 minute window
        self.max_requests = 100  # Default max requests per window
        
        # Metrics
        self.rate_limit_hits = Counter(
            'rate_limit_hits_total',
            'Total number of rate limit hits',
            ['client_id', 'action']
        )
        self.rate_limit_latency = Histogram(
            'rate_limit_operation_latency_seconds',
            'Rate limit operation latency'
        )
        self.active_limits = Gauge(
            'rate_limit_active',
            'Number of active rate limits',
            ['client_id']
        )
        
    def _get_key(self, client_id: str, action: str) -> str:
        """Generate Redis key for rate limit"""
        return f"rate:limit:{client_id}:{action}"
        
    def _get_window_key(self, client_id: str, action: str, window: int) -> str:
        """Generate Redis key for rate limit window"""
        return f"rate:limit:{client_id}:{action}:{window}"
        
    def is_rate_limited(
        self,
        client_id: str,
        action: str,
        max_requests: Optional[int] = None
    ) -> bool:
        """
        Check if client is rate limited
        
        Args:
            client_id: Client identifier (e.g., IP, user ID)
            action: Action being rate limited
            max_requests: Maximum requests per window (optional)
            
        Returns:
            bool: True if rate limited, False otherwise
        """
        try:
            with self.rate_limit_latency.time():
                # Use provided max_requests or default
                limit = max_requests or self.max_requests
                
                # Get current window
                now = int(time.time())
                window = now // self.window_size
                
                # Get window key
                window_key = self._get_window_key(client_id, action, window)
                
                # Get current count
                count = int(self.redis.get(window_key) or 0)
                
                # Check if rate limited
                if count >= limit:
                    self.rate_limit_hits.labels(
                        client_id=client_id,
                        action=action
                    ).inc()
                    return True
                    
                # Increment count
                pipe = self.redis.pipeline()
                pipe.incr(window_key)
                pipe.expire(window_key, self.window_size)
                pipe.execute()
                
                # Update active limits gauge
                self.active_limits.labels(client_id=client_id).inc()
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return False
            
    def get_remaining_requests(
        self,
        client_id: str,
        action: str,
        max_requests: Optional[int] = None
    ) -> Optional[int]:
        """
        Get remaining requests for client
        
        Args:
            client_id: Client identifier
            action: Action being rate limited
            max_requests: Maximum requests per window (optional)
            
        Returns:
            Optional[int]: Remaining requests or None if error
        """
        try:
            # Use provided max_requests or default
            limit = max_requests or self.max_requests
            
            # Get current window
            now = int(time.time())
            window = now // self.window_size
            
            # Get window key
            window_key = self._get_window_key(client_id, action, window)
            
            # Get current count
            count = int(self.redis.get(window_key) or 0)
            
            return max(0, limit - count)
            
        except Exception as e:
            logger.error(f"Error getting remaining requests: {str(e)}")
            return None
            
    def get_reset_time(
        self,
        client_id: str,
        action: str
    ) -> Optional[datetime]:
        """
        Get time when rate limit resets
        
        Args:
            client_id: Client identifier
            action: Action being rate limited
            
        Returns:
            Optional[datetime]: Reset time or None if error
        """
        try:
            # Get current window
            now = int(time.time())
            window = now // self.window_size
            
            # Calculate next window start
            next_window = (window + 1) * self.window_size
            
            return datetime.fromtimestamp(next_window)
            
        except Exception as e:
            logger.error(f"Error getting reset time: {str(e)}")
            return None
            
    def reset_limits(self, client_id: str, action: Optional[str] = None) -> bool:
        """
        Reset rate limits for client
        
        Args:
            client_id: Client identifier
            action: Action to reset (optional)
            
        Returns:
            bool: Success status
        """
        try:
            # Get pattern for keys
            pattern = f"rate:limit:{client_id}"
            if action:
                pattern += f":{action}"
            pattern += "*"
            
            # Get matching keys
            keys = self.redis.keys(pattern)
            
            if keys:
                # Delete keys
                self.redis.delete(*keys)
                
            # Update active limits gauge
            self.active_limits.labels(client_id=client_id).dec()
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting rate limits: {str(e)}")
            return False
            
    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics
        
        Returns:
            Dict[str, Any]: Rate limiter statistics
        """
        try:
            # Get all rate limit keys
            keys = self.redis.keys("rate:limit:*")
            
            # Count active limits by client
            client_counts = {}
            for key in keys:
                parts = key.decode().split(":")
                if len(parts) >= 4:
                    client_id = parts[2]
                    client_counts[client_id] = client_counts.get(client_id, 0) + 1
                    
            return {
                "total_keys": len(keys),
                "active_clients": len(client_counts),
                "client_counts": client_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting rate limiter stats: {str(e)}")
            return {
                "total_keys": 0,
                "active_clients": 0,
                "client_counts": {}
            } 