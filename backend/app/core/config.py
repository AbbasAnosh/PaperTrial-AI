"""
Configuration module.

This module handles all configuration settings for the application,
including environment-specific settings and feature flags.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, PostgresDsn, RedisDsn, validator
from pathlib import Path

class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "Paper Trail Automator"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_url(cls, v: Optional[str], values: dict) -> str:
        if v:
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=f"/{values.get('POSTGRES_DB')}"
        )
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_URL: Optional[RedisDsn] = None
    
    @validator("REDIS_URL", pre=True)
    def assemble_redis_url(cls, v: Optional[str], values: dict) -> str:
        if v:
            return v
        return RedisDsn.build(
            scheme="redis",
            host=values.get("REDIS_HOST"),
            port=str(values.get("REDIS_PORT")),
            password=values.get("REDIS_PASSWORD"),
            path=f"/{values.get('REDIS_DB')}"
        )
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_ANONYMOUS: str = "20/minute"
    RATE_LIMIT_AUTHENTICATED: str = "1000/hour"
    
    # File Storage
    UPLOAD_DIR: Path = Path("uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "jpg", "jpeg", "png"]
    
    # Email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    SMTP_FROM_EMAIL: str = "noreply@example.com"
    SMTP_FROM_NAME: str = "Paper Trail Automator"
    
    # Webhooks
    WEBHOOK_SECRET: str
    WEBHOOK_TIMEOUT: int = 5
    WEBHOOK_MAX_RETRIES: int = 3
    
    # Feature Flags
    FEATURE_USER_REGISTRATION: bool = True
    FEATURE_EMAIL_VERIFICATION: bool = True
    FEATURE_PASSWORD_RESET: bool = True
    FEATURE_OAUTH: bool = False
    FEATURE_WEBHOOKS: bool = True
    FEATURE_ANALYTICS: bool = True
    
    # Cache
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 300  # 5 minutes
    CACHE_KEY_PREFIX: str = "paper_trail:"
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    HEALTH_CHECK_INTERVAL: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Create required directories
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Environment-specific settings
if settings.ENVIRONMENT == "production":
    settings.DEBUG = False
    settings.CORS_ORIGINS = [
        "https://app.example.com",
        "https://api.example.com"
    ]
    settings.LOG_LEVEL = "INFO"
    settings.LOG_FILE = "logs/app.log"
    settings.RATE_LIMIT_ENABLED = True
    settings.FEATURE_USER_REGISTRATION = False
    settings.FEATURE_EMAIL_VERIFICATION = True
    settings.SMTP_TLS = True
    settings.CACHE_ENABLED = True
    settings.ENABLE_METRICS = True

elif settings.ENVIRONMENT == "staging":
    settings.DEBUG = True
    settings.CORS_ORIGINS = [
        "https://staging.example.com",
        "https://api-staging.example.com"
    ]
    settings.LOG_LEVEL = "DEBUG"
    settings.LOG_FILE = "logs/staging.log"
    settings.RATE_LIMIT_ENABLED = True
    settings.FEATURE_USER_REGISTRATION = True
    settings.FEATURE_EMAIL_VERIFICATION = True
    settings.SMTP_TLS = True
    settings.CACHE_ENABLED = True
    settings.ENABLE_METRICS = True

else:  # development
    settings.DEBUG = True
    settings.CORS_ORIGINS = ["http://localhost:3000"]
    settings.LOG_LEVEL = "DEBUG"
    settings.LOG_FILE = "logs/development.log"
    settings.RATE_LIMIT_ENABLED = False
    settings.FEATURE_USER_REGISTRATION = True
    settings.FEATURE_EMAIL_VERIFICATION = False
    settings.SMTP_TLS = False
    settings.CACHE_ENABLED = False
    settings.ENABLE_METRICS = True 