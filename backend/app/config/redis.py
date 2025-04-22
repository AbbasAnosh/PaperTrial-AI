import os
import redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_redis_client() -> Optional[redis.Redis]:
    """
    Get a Redis client instance with connection settings from environment variables.
    Returns None if connection fails.
    """
    try:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_db = int(os.getenv('REDIS_DB', 0))
        redis_password = os.getenv('REDIS_PASSWORD', None)
        
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        
        # Test connection
        client.ping()
        logger.info("Successfully connected to Redis")
        return client
        
    except redis.ConnectionError as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error connecting to Redis: {str(e)}")
        return None 