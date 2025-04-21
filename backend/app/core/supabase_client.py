from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    # Use the anon key for client-side auth
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# For admin operations, use a separate client with service role key
def get_admin_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

SupabaseClient = get_supabase_client 