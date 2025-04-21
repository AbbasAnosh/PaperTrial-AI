"""
User management routes for user profile and settings.
"""

from fastapi import Depends, HTTPException, status, Path
from typing import Dict, Any, List
from app.core.auth import get_current_user
from app.database.session import get_supabase
from app.api.base import BaseRouter
from app.models.user import User, UserUpdate
from app.services.user_service import UserService
import logging

logger = logging.getLogger(__name__)
router = BaseRouter(prefix="", tags=["users"])

@router.get("/me", response_model=User)
async def get_current_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user profile."""
    return current_user

@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Update current user profile."""
    user_service = UserService(supabase)
    try:
        updated_user = await user_service.update_user(current_user["user_id"], user_update)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return updated_user
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str = Path(..., description="The ID of the user to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    supabase = Depends(get_supabase)
):
    """Get a user by ID."""
    user_service = UserService(supabase)
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        return user
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 