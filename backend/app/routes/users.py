"""
User management routes for user profile and settings.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import Dict, Any, List
from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_client
from app.models.user import User, UserUpdate, UserCreate
from app.services.user_service import UserService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])

@router.post("", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create a new user.
    
    This endpoint creates a new user account with the provided information.
    Only administrators can create new users.
    
    Args:
        user (UserCreate): User data including email, password, and profile information
        current_user (User): Currently authenticated user (must be admin)
        
    Returns:
        User: Created user account
        
    Raises:
        HTTPException:
            - 400: If user data validation fails
            - 401: If user is not authenticated
            - 403: If user is not an administrator
            - 409: If email already exists
    """
    user_service = UserService()
    return await user_service.create_user(user, current_user)

@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current user information.
    
    This endpoint retrieves the profile information of the currently authenticated user.
    
    Args:
        current_user (User): Currently authenticated user
        
    Returns:
        User: Current user's profile information
        
    Raises:
        HTTPException:
            - 401: If user is not authenticated
    """
    return current_user

@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update current user information.
    
    This endpoint updates the profile information of the currently authenticated user.
    
    Args:
        user_update (UserUpdate): Updated user data
        current_user (User): Currently authenticated user
        
    Returns:
        User: Updated user profile
        
    Raises:
        HTTPException:
            - 400: If update data validation fails
            - 401: If user is not authenticated
            - 422: If validation fails
    """
    user_service = UserService()
    return await user_service.update_user(current_user.id, user_update, current_user)

@router.get("", response_model=List[User])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    List all users.
    
    This endpoint retrieves a paginated list of all users.
    Only administrators can access this endpoint.
    
    Args:
        skip (int): Number of users to skip
        limit (int): Maximum number of users to return
        current_user (User): Currently authenticated user (must be admin)
        
    Returns:
        List[User]: List of users
        
    Raises:
        HTTPException:
            - 401: If user is not authenticated
            - 403: If user is not an administrator
    """
    user_service = UserService()
    return await user_service.list_users(skip, limit, current_user)

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get user by ID.
    
    This endpoint retrieves a specific user's profile by ID.
    Only administrators can access other users' profiles.
    
    Args:
        user_id (str): ID of the user to retrieve
        current_user (User): Currently authenticated user (must be admin)
        
    Returns:
        User: Requested user's profile
        
    Raises:
        HTTPException:
            - 401: If user is not authenticated
            - 403: If user is not an administrator
            - 404: If user is not found
    """
    user_service = UserService()
    return await user_service.get_user(user_id, current_user)

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update user by ID.
    
    This endpoint updates a specific user's profile by ID.
    Only administrators can update other users' profiles.
    
    Args:
        user_id (str): ID of the user to update
        user_update (UserUpdate): Updated user data
        current_user (User): Currently authenticated user (must be admin)
        
    Returns:
        User: Updated user profile
        
    Raises:
        HTTPException:
            - 400: If update data validation fails
            - 401: If user is not authenticated
            - 403: If user is not an administrator
            - 404: If user is not found
            - 422: If validation fails
    """
    user_service = UserService()
    return await user_service.update_user(user_id, user_update, current_user)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete user by ID.
    
    This endpoint deletes a specific user account by ID.
    Only administrators can delete user accounts.
    
    Args:
        user_id (str): ID of the user to delete
        current_user (User): Currently authenticated user (must be admin)
        
    Raises:
        HTTPException:
            - 401: If user is not authenticated
            - 403: If user is not an administrator
            - 404: If user is not found
    """
    user_service = UserService()
    await user_service.delete_user(user_id, current_user) 