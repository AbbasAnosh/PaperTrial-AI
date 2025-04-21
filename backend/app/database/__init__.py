"""
Paper Trail Automator Database

This package contains database configuration and models.
"""

from typing import Generator
from motor.motor_asyncio import AsyncIOMotorClient
from .session import get_supabase, get_redis
from app.core.config import settings

async def get_db() -> Generator:
    """Get database connection"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    try:
        yield client[settings.MONGODB_DB_NAME]
    finally:
        client.close()

__all__ = ["get_supabase", "get_redis", "get_db"] 