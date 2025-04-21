from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import os
import logging
from functools import lru_cache
from pydantic import validator, Field
import secrets

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = Field(default="Paper Trail Automator", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Paper Trail Automator API"
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="SECRET_KEY")
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 7, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SESSION_EXPIRE_MINUTES: int = Field(default=60 * 24, env="SESSION_EXPIRE_MINUTES")  # 1 day
    
    # Hosts
    ALLOWED_HOSTS: List[str] = Field(
        default=["*"],
        env="ALLOWED_HOSTS"
    )
    
    # Supabase
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(..., env="SUPABASE_KEY")
    SUPABASE_SERVICE_KEY: str = Field(..., env="SUPABASE_SERVICE_KEY")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        env="CORS_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_MAX_AGE: int = 600
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_SSL: bool = Field(default=False, env="REDIS_SSL")
    REDIS_TIMEOUT: int = 5
    
    # WebSocket
    WS_PING_INTERVAL: int = Field(default=30, env="WS_PING_INTERVAL")
    WS_PING_TIMEOUT: int = Field(default=10, env="WS_PING_TIMEOUT")
    WS_MAX_MESSAGE_SIZE: int = Field(default=1024 * 1024, env="WS_MAX_MESSAGE_SIZE")  # 1MB
    
    # PDF Processing
    PDF_MAX_SIZE_MB: int = Field(default=10, env="PDF_MAX_SIZE_MB")
    PDF_ALLOWED_TYPES: List[str] = ["application/pdf"]
    PDF_PROCESSING_TIMEOUT: int = Field(default=300, env="PDF_PROCESSING_TIMEOUT")
    PDF_CACHE_TTL: int = Field(default=3600, env="PDF_CACHE_TTL")
    
    # File Upload
    UPLOAD_DIR: str = Field(default="uploads", env="UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = Field(default=10 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 10MB
    ALLOWED_EXTENSIONS: List[str] = Field(default=["pdf"], env="ALLOWED_EXTENSIONS")
    
    # Cache
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")
    CACHE_MAX_SIZE: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_STRATEGY: str = Field(default="fixed-window", env="RATE_LIMIT_STRATEGY")
    
    # API Keys
    UNSTRUCTURED_API_KEY: str = Field(..., env="UNSTRUCTURED_API_KEY")
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    
    # Validation
    @validator("JWT_SECRET")
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")
        return v
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("REDIS_PASSWORD")
    def validate_redis_password(cls, v, values):
        if values.get("ENVIRONMENT") == "production" and not v:
            raise ValueError("REDIS_PASSWORD must be set in production")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def is_production(self) -> bool:
        """Check if the application is running in production mode"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if the application is running in development mode"""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if the application is running in testing mode"""
        return self.ENVIRONMENT.lower() == "testing"
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration as a dictionary"""
        return {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "db": self.REDIS_DB,
            "password": self.REDIS_PASSWORD,
            "ssl": self.REDIS_SSL
        }

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    try:
        return Settings()
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        raise  # In development/testing, we want to fail fast if settings are misconfigured

# Create a global settings instance
settings = get_settings() 