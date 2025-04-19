from typing import Dict, Any, Optional
from datetime import datetime
from app.core.supabase_client import SupabaseClient

class AuthService:
    def __init__(self):
        self.supabase = SupabaseClient()

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password using Supabase Auth"""
        try:
            # Use Supabase Auth to sign in
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if not auth_response.user:
                return None
            
            return {
                "user": {
                    "id": auth_response.user.id,
                    "email": auth_response.user.email,
                    "name": auth_response.user.user_metadata.get("name")
                },
                "token": auth_response.session.access_token
            }
        except Exception as e:
            raise Exception(f"Authentication failed: {str(e)}")

    async def authenticate_google(self, token: str) -> Dict[str, Any]:
        """Authenticate user with Google OAuth token using Supabase Auth"""
        try:
            # Exchange Google token for Supabase session
            auth_response = self.supabase.auth.sign_in_with_id_token({
                "provider": "google",
                "token": token
            })
            
            if not auth_response.user:
                raise Exception("Failed to authenticate with Google")
            
            return {
                "user": {
                    "id": auth_response.user.id,
                    "email": auth_response.user.email,
                    "name": auth_response.user.user_metadata.get("name")
                },
                "token": auth_response.session.access_token
            }
        except Exception as e:
            raise Exception(f"Google authentication failed: {str(e)}")

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token using Supabase Auth"""
        try:
            # Get user from session token
            user = self.supabase.auth.get_user(token)
            return {
                "sub": user.id,
                "email": user.email
            }
        except Exception:
            raise Exception("Invalid token") 