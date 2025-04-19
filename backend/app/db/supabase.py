from supabase import create_client, Client
import os
from typing import Optional

class SupabaseClient:
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not url or not key:
                raise ValueError("Supabase credentials not found in environment variables")
            
            cls._instance = create_client(url, key)
        
        return cls._instance

# Create a singleton instance
supabase_client = SupabaseClient.get_client() 