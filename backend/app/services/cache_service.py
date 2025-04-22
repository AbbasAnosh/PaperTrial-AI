import logging
from typing import Dict, Any, Optional, Callable, TypeVar, Generic, Union, List, Set
from redis import Redis, ConnectionPool, ResponseError
from redis.exceptions import ConnectionError, TimeoutError
import json
import hashlib
import time
from datetime import datetime, timedelta
from functools import wraps
import pickle
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from prometheus_client import Counter, Histogram, Gauge
import threading
from concurrent.futures import ThreadPoolExecutor
import signal
import sys
import uuid
from enum import Enum
import zlib

logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheVersion:
    """Cache versioning functionality"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.version_key = "cache:version"
        self._current_version = None
        self._lock = threading.Lock()
        
    def get_version(self) -> str:
        """Get current cache version"""
        with self._lock:
            if self._current_version is None:
                self._current_version = self.redis.get(self.version_key) or str(uuid.uuid4())
                self.redis.set(self.version_key, self._current_version)
            return self._current_version
            
    def increment_version(self) -> str:
        """Increment cache version"""
        with self._lock:
            new_version = str(uuid.uuid4())
            self.redis.set(self.version_key, new_version)
            self._current_version = new_version
            return new_version
            
    def invalidate_by_version(self, old_version: str) -> bool:
        """Invalidate cache entries from old version"""
        pattern = f"cache:v{old_version}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
        return True

class CacheTags:
    """Cache tagging functionality"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.tag_prefix = "cache:tag:"
        
    def add_tags(self, key: str, tags: List[str]) -> bool:
        """Add tags to a cache key"""
        try:
            pipeline = self.redis.pipeline()
            for tag in tags:
                tag_key = f"{self.tag_prefix}{tag}"
                pipeline.sadd(tag_key, key)
            pipeline.execute()
            return True
        except Exception as e:
            logger.error(f"Error adding tags: {str(e)}")
            return False
            
    def remove_tags(self, key: str, tags: List[str]) -> bool:
        """Remove tags from a cache key"""
        try:
            pipeline = self.redis.pipeline()
            for tag in tags:
                tag_key = f"{self.tag_prefix}{tag}"
                pipeline.srem(tag_key, key)
            pipeline.execute()
            return True
        except Exception as e:
            logger.error(f"Error removing tags: {str(e)}")
            return False
            
    def get_keys_by_tag(self, tag: str) -> List[str]:
        """Get all keys with a specific tag"""
        try:
            tag_key = f"{self.tag_prefix}{tag}"
            return list(self.redis.smembers(tag_key))
        except Exception as e:
            logger.error(f"Error getting keys by tag: {str(e)}")
            return []
            
    def invalidate_by_tag(self, tag: str) -> bool:
        """Invalidate all keys with a specific tag"""
        try:
            keys = self.get_keys_by_tag(tag)
            if keys:
                self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Error invalidating by tag: {str(e)}")
            return False

class DistributedSync:
    """Distributed cache synchronization"""
    
    def __init__(self, cache_service: 'CacheService', instance_id: str):
        self.cache_service = cache_service
        self.instance_id = instance_id
        self.sync_channel = "cache:sync"
        self.sync_interval = 60  # 1 minute
        self.sync_thread = None
        self._stop_event = threading.Event()
        self._pubsub = None
        
    def start(self):
        """Start distributed sync"""
        if self.sync_thread:
            return
            
        def sync_worker():
            self._pubsub = self.cache_service.redis.pubsub()
            self._pubsub.subscribe(self.sync_channel)
            
            while not self._stop_event.is_set():
                try:
                    message = self._pubsub.get_message()
                    if message and message['type'] == 'message':
                        self._handle_sync_message(message['data'])
                except Exception as e:
                    logger.error(f"Error in sync worker: {str(e)}")
                finally:
                    time.sleep(0.1)
                    
        self.sync_thread = threading.Thread(target=sync_worker, daemon=True)
        self.sync_thread.start()
        
    def stop(self):
        """Stop distributed sync"""
        if not self.sync_thread:
            return
            
        self._stop_event.set()
        if self._pubsub:
            self._pubsub.unsubscribe()
            self._pubsub.close()
        self.sync_thread.join()
        self.sync_thread = None
        
    def _handle_sync_message(self, message: str):
        """Handle sync message"""
        try:
            data = json.loads(message)
            if data['instance_id'] == self.instance_id:
                return
                
            if data['type'] == 'invalidate':
                self.cache_service.delete(data['key'])
            elif data['type'] == 'update':
                self.cache_service.set(data['key'], data['value'], data.get('ttl'))
                
        except Exception as e:
            logger.error(f"Error handling sync message: {str(e)}")
            
    def broadcast_invalidate(self, key: str):
        """Broadcast invalidation message"""
        self._broadcast_message({
            'type': 'invalidate',
            'key': key,
            'instance_id': self.instance_id
        })
        
    def broadcast_update(self, key: str, value: Any, ttl: Optional[int] = None):
        """Broadcast update message"""
        self._broadcast_message({
            'type': 'update',
            'key': key,
            'value': value,
            'ttl': ttl,
            'instance_id': self.instance_id
        })
        
    def _broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all instances"""
        try:
            self.cache_service.redis.publish(
                self.sync_channel,
                json.dumps(message)
            )
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")

class CacheMetrics:
    """Metrics collection for cache operations"""
    
    def __init__(self):
        self.hits = Counter('cache_hits_total', 'Total number of cache hits')
        self.misses = Counter('cache_misses_total', 'Total number of cache misses')
        self.errors = Counter('cache_errors_total', 'Total number of cache errors')
        self.latency = Histogram('cache_operation_latency_seconds', 'Cache operation latency')
        self.memory_usage = Gauge('cache_memory_usage_bytes', 'Current cache memory usage')
        self.connection_pool_size = Gauge('cache_connection_pool_size', 'Current connection pool size')
        self.warmup_items = Counter('cache_warmup_items_total', 'Total number of items warmed up')
        self.sync_operations = Counter('cache_sync_operations_total', 'Total number of sync operations')
        self.version_changes = Counter('cache_version_changes_total', 'Total number of version changes')
        self.tag_operations = Counter('cache_tag_operations_total', 'Total number of tag operations')

class CacheWarmup:
    """Cache warming functionality"""
    
    def __init__(self, cache_service: 'CacheService'):
        self.cache_service = cache_service
        self.warmup_queue = asyncio.Queue()
        self.is_running = False
        self.warmup_thread = None
        self._stop_event = threading.Event()
        
    async def add_to_warmup(self, key: str, callback: Callable[[], Any], ttl: Optional[int] = None):
        """Add an item to the warmup queue"""
        await self.warmup_queue.put((key, callback, ttl))
        
    async def start(self):
        """Start the warmup process"""
        if self.is_running:
            return
            
        self.is_running = True
        self._stop_event.clear()
        
        async def warmup_worker():
            while not self._stop_event.is_set():
                try:
                    key, callback, ttl = await self.warmup_queue.get()
                    try:
                        value = callback()
                        self.cache_service.set(key, value, ttl)
                        self.cache_service.metrics.warmup_items.inc()
                    except Exception as e:
                        logger.error(f"Error warming up cache for key {key}: {str(e)}")
                    finally:
                        self.warmup_queue.task_done()
                except asyncio.CancelledError:
                    break
                    
        self.warmup_thread = asyncio.create_task(warmup_worker())
        
    async def stop(self):
        """Stop the warmup process"""
        if not self.is_running:
            return
            
        self._stop_event.set()
        if self.warmup_thread:
            await self.warmup_thread
        self.is_running = False

class CacheSync:
    """Cache synchronization functionality"""
    
    def __init__(self, cache_service: 'CacheService'):
        self.cache_service = cache_service
        self.sync_interval = 60  # 1 minute
        self.sync_thread = None
        self._stop_event = threading.Event()
        
    def start(self):
        """Start the sync process"""
        if self.sync_thread:
            return
            
        def sync_worker():
            while not self._stop_event.is_set():
                try:
                    self._sync_cache()
                    self.cache_service.metrics.sync_operations.inc()
                except Exception as e:
                    logger.error(f"Error syncing cache: {str(e)}")
                finally:
                    time.sleep(self.sync_interval)
                    
        self.sync_thread = threading.Thread(target=sync_worker, daemon=True)
        self.sync_thread.start()
        
    def stop(self):
        """Stop the sync process"""
        if not self.sync_thread:
            return
            
        self._stop_event.set()
        self.sync_thread.join()
        self.sync_thread = None
        
    def _sync_cache(self):
        """Synchronize cache with source of truth"""
        # Implement your sync logic here
        # For example, sync with a database or external service
        pass

class CacheService:
    """Service for caching responses and data"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.compression_threshold = 1024  # Compress values larger than 1KB
        self.metrics = CacheMetrics()
        self._setup_connection_pool()
        self._circuit_breaker = CircuitBreaker()
        self.warmup = CacheWarmup(self)
        self.sync = CacheSync(self)
        self.version = CacheVersion(redis_client)
        self.tags = CacheTags(redis_client)
        self.distributed = DistributedSync(self, str(uuid.uuid4()))
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutting down cache service...")
        asyncio.run(self.warmup.stop())
        self.sync.stop()
        self.distributed.stop()
        sys.exit(0)
        
    def _setup_connection_pool(self):
        """Setup Redis connection pool"""
        if isinstance(self.redis, Redis):
            self.pool = ConnectionPool(
                host=self.redis.connection_pool.connection_kwargs['host'],
                port=self.redis.connection_pool.connection_kwargs['port'],
                db=self.redis.connection_pool.connection_kwargs['db'],
                max_connections=10,
                decode_responses=True
            )
            self.redis = Redis(connection_pool=self.pool)
            self.metrics.connection_pool_size.set(10)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute Redis operation with retry logic"""
        try:
            with self.metrics.latency.time():
                result = operation(*args, **kwargs)
                return result
        except (ConnectionError, TimeoutError) as e:
            self.metrics.errors.inc()
            logger.error(f"Cache operation failed: {str(e)}")
            raise
    
    def _get_cache_key(self, key: str) -> str:
        """Generate Redis key for cache"""
        return f"cache:{key}"
        
    def _compress(self, data: str) -> bytes:
        """Compress data if it exceeds threshold"""
        if len(data.encode()) > self.compression_threshold:
            return zlib.compress(data.encode())
        return data.encode()
        
    def _decompress(self, data: bytes) -> str:
        """Decompress data if it's compressed"""
        try:
            return zlib.decompress(data).decode()
        except zlib.error:
            return data.decode()
            
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            bool: Success status
        """
        try:
            # Convert value to JSON string
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)
                
            # Compress if needed
            value_bytes = self._compress(value)
            
            # Store in Redis
            if ttl:
                return self.redis.setex(self._get_cache_key(key), ttl, value_bytes)
            return self.redis.set(self._get_cache_key(key), value_bytes)
            
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            return False
            
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: Cached value or None if not found
        """
        try:
            value = self.redis.get(self._get_cache_key(key))
            if not value:
                return None
                
            # Decompress if needed
            value_str = self._decompress(value)
            
            # Try to parse as JSON
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                return value_str
                
        except Exception as e:
            logger.error(f"Error getting cache: {str(e)}")
            return None
            
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache
        
        Args:
            key: Cache key
            
        Returns:
            bool: Success status
        """
        try:
            return bool(self.redis.delete(self._get_cache_key(key)))
        except Exception as e:
            logger.error(f"Error deleting cache: {str(e)}")
            return False
            
    def clear_pattern(self, pattern: str) -> bool:
        """
        Clear all keys matching a pattern
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            bool: Success status
        """
        try:
            keys = self.redis.keys(self._get_cache_key(pattern))
            if keys:
                return bool(self.redis.delete(*keys))
            return True
        except Exception as e:
            logger.error(f"Error clearing cache pattern: {str(e)}")
            return False
            
    def get_or_set(
        self,
        key: str,
        callback: Callable[[], Any],
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get a value from cache or set it using a callback
        
        Args:
            key: Cache key
            callback: Function to call if value not in cache
            ttl: Time to live in seconds
            
        Returns:
            Any: Cached value or callback result
        """
        value = self.get(key)
        if value is not None:
            return value
            
        value = callback()
        self.set(key, value, ttl)
        return value
        
    def cache_response(
        self,
        ttl: Optional[int] = None,
        key_prefix: Optional[str] = None
    ):
        """
        Decorator for caching function responses
        
        Args:
            ttl: Time to live in seconds
            key_prefix: Prefix for cache key
            
        Returns:
            Callable: Decorated function
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Generate cache key
                key_parts = [key_prefix] if key_prefix else []
                key_parts.extend([
                    func.__name__,
                    str(args),
                    str(sorted(kwargs.items()))
                ])
                cache_key = hashlib.md5(
                    ":".join(key_parts).encode()
                ).hexdigest()
                
                # Try to get from cache
                cached = self.get(cache_key)
                if cached is not None:
                    return cached
                    
                # Call function and cache result
                result = await func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
                
            return wrapper
        return decorator
        
    def invalidate(self, key: str) -> bool:
        """
        Invalidate a cache key
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            bool: Success status
        """
        return self.delete(key)
        
    def invalidate_pattern(self, pattern: str) -> bool:
        """
        Invalidate all keys matching a pattern
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            bool: Success status
        """
        return self.clear_pattern(pattern)
        
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """
        Get cache statistics
        
        Returns:
            Dict[str, Union[int, float]]: Cache statistics
        """
        try:
            info = self.redis.info(section="memory")
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "total_keys": len(self.redis.keys(self._get_cache_key("*"))),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0) /
                    (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                ) * 100
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {
                "used_memory": 0,
                "used_memory_peak": 0,
                "total_keys": 0,
                "hits": 0,
                "misses": 0,
                "hit_rate": 0
            }
    
    def start_distributed_sync(self):
        """Start distributed synchronization"""
        self.distributed.start()
        
    def stop_distributed_sync(self):
        """Stop distributed synchronization"""
        self.distributed.stop()
        
    def get_distributed_stats(self) -> Dict[str, Any]:
        """Get distributed sync statistics"""
        return {
            "instance_id": self.distributed.instance_id,
            "is_running": self.distributed.sync_thread is not None,
            "sync_channel": self.distributed.sync_channel
        }
    
    async def warm_cache(self, items: List[Dict[str, Any]]):
        """Warm up the cache with predefined items"""
        for item in items:
            key = item.get('key')
            callback = item.get('callback')
            ttl = item.get('ttl')
            
            if key and callback:
                await self.warmup.add_to_warmup(key, callback, ttl)
                
        if not self.warmup.is_running:
            await self.warmup.start()
            
    def start_sync(self):
        """Start cache synchronization"""
        self.sync.start()
        
    def stop_sync(self):
        """Stop cache synchronization"""
        self.sync.stop()
        
    def get_warmup_stats(self) -> Dict[str, Any]:
        """Get cache warmup statistics"""
        return {
            "is_running": self.warmup.is_running,
            "queue_size": self.warmup.warmup_queue.qsize(),
            "items_warmed": self.metrics.warmup_items._value.get()
        }
        
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get cache synchronization statistics"""
        return {
            "is_running": self.sync.sync_thread is not None,
            "sync_operations": self.metrics.sync_operations._value.get(),
            "last_sync": getattr(self.sync, 'last_sync_time', None)
        }

class CircuitBreaker:
    """Circuit breaker implementation for cache operations"""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        if self.state == "closed":
            return True
            
        if self.state == "open":
            if self.last_failure_time and \
               time.time() - self.last_failure_time >= self.reset_timeout:
                self.state = "half-open"
                return True
            return False
            
        if self.state == "half-open":
            return True
            
        return True
        
    def record_failure(self):
        """Record a failure"""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning("Circuit breaker opened due to too many failures")
            
    def record_success(self):
        """Record a success"""
        self.failures = 0
        self.state = "closed"
        logger.info("Circuit breaker closed after successful operation") 