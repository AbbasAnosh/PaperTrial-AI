from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

SupabaseClient = get_supabase_client 