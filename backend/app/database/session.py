"""
Database session management.
"""

from supabase import create_client, Client
from redis.asyncio import Redis
from typing import AsyncGenerator
from app.core.config import settings

# Supabase client
def get_supabase() -> Client:
    """Get Supabase client."""
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY
    )

# Redis connection
async def get_redis() -> AsyncGenerator:
    """Get Redis connection."""
    try:
        redis = Redis.from_url(settings.REDIS_URL)
        yield redis
    finally:
        await redis.close() 