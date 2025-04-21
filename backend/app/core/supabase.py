from supabase import create_client
from app.core.config import settings

def get_supabase():
    """Get Supabase client instance."""
    try:
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        return supabase
    except Exception as e:
        raise ConnectionError(f"Failed to connect to Supabase: {str(e)}")

def get_admin_client():
    """Get Supabase admin client instance for database migrations."""
    try:
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        return supabase
    except Exception as e:
        raise ConnectionError(f"Failed to connect to Supabase admin client: {str(e)}") 