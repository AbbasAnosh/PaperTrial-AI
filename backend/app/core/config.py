from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    NEXT_PUBLIC_SUPABASE_URL: str
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str

    # API Keys
    UNSTRUCTURED_API_KEY: str
    OPENAI_API_KEY: str

    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"

    @property
    def cors_origins(self) -> List[str]:
        """Get the CORS origins as a list"""
        origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
        if isinstance(origins, str):
            if origins.startswith("[") and origins.endswith("]"):
                # Parse JSON array string
                import json
                return json.loads(origins)
            # Split comma-separated string
            return [origin.strip() for origin in origins.split(",")]
        return origins

settings = Settings() 