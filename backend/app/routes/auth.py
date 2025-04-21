"""
Authentication routes for user login, registration, and token management.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Dict, Any
from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_client
from app.models.user import User, UserCreate
from app.models.token import Token
from app.services.auth_service import AuthService
from app.core.errors import (
    AuthenticationError,
    ValidationError
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """Login user and return access token."""
    try:
        supabase = get_supabase_client()
        auth_response = supabase.auth.sign_in_with_password({
            "email": form_data.username,
            "password": form_data.password
        })
        
        if not auth_response.session:
            raise AuthenticationError("Invalid credentials")
            
        return Token(
            access_token=auth_response.session.access_token,
            token_type="bearer"
        )
    except Exception as e:
        logger.error(f"Error logging in: {str(e)}")
        raise AuthenticationError(str(e))

@router.post("/register", response_model=User)
async def register(
    user_create: UserCreate
):
    """Register a new user."""
    try:
        # Create user in Supabase
        supabase = get_supabase_client()
        auth_response = supabase.auth.sign_up({
            "email": user_create.email,
            "password": user_create.password
        })
        
        if not auth_response.user:
            raise ValidationError("Failed to create user")
            
        # Create user in database
        user_service = UserService(supabase)
        user = await user_service.create_user(user_create)
        
        return user
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        raise ValidationError(str(e))

@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user information."""
    try:
        supabase = get_supabase_client()
        user_service = UserService(supabase)
        user = await user_service.get_user_by_id(current_user["user_id"])
        if not user:
            raise AuthenticationError("User not found")
        return user
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise AuthenticationError(str(e)) 