"""
Authentication routes for user login, registration, and token management.
"""

from fastapi import Depends, HTTPException, status, APIRouter
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
from app.models.auth import UserLogin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate) -> Any:
    """
    Register a new user.
    
    This endpoint creates a new user account with the provided credentials.
    
    Args:
        user_data (UserCreate): User registration data including email and password
        
    Returns:
        Token: JWT access token and token type
        
    Raises:
        HTTPException: 
            - 400: If email is already registered
            - 422: If validation fails
    """
    auth_service = AuthService()
    return await auth_service.register_user(user_data)

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    Authenticate user and return JWT token.
    
    This endpoint authenticates a user with their email and password,
    returning a JWT token for subsequent authenticated requests.
    
    Args:
        form_data (OAuth2PasswordRequestForm): Login credentials
        
    Returns:
        Token: JWT access token and token type
        
    Raises:
        HTTPException:
            - 401: If credentials are invalid
            - 422: If validation fails
    """
    auth_service = AuthService()
    return await auth_service.authenticate_user(form_data.username, form_data.password)

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)) -> Any:
    """
    Refresh JWT token.
    
    This endpoint generates a new JWT token for an authenticated user,
    extending their session.
    
    Args:
        current_user (User): Currently authenticated user
        
    Returns:
        Token: New JWT access token and token type
        
    Raises:
        HTTPException:
            - 401: If user is not authenticated
    """
    auth_service = AuthService()
    return await auth_service.refresh_token(current_user)

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)) -> Any:
    """
    Logout user and invalidate token.
    
    This endpoint invalidates the current user's JWT token,
    effectively logging them out.
    
    Args:
        current_user (User): Currently authenticated user
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException:
            - 401: If user is not authenticated
    """
    auth_service = AuthService()
    await auth_service.logout_user(current_user)
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current user information.
    
    This endpoint retrieves the profile information of the currently authenticated user.
    
    Args:
        current_user (Dict[str, Any]): Currently authenticated user
        
    Returns:
        User: Current user's profile information
        
    Raises:
        HTTPException:
            - 401: If user is not authenticated
    """
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