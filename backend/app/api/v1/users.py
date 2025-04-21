from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.user import User, UserCreate, UserUpdate
from app.services.user_service import UserService
from app.core.auth import get_current_user
from app.core.config import settings

router = APIRouter()
user_service = UserService()

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user

@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Get user by ID."""
    user = await user_service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/", response_model=List[User])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """List users with pagination."""
    return await user_service.list_users(skip=skip, limit=limit)

@router.post("/", response_model=User)
async def create_user(user: UserCreate):
    """Create a new user."""
    try:
        return await user_service.create(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update user information."""
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")
    
    user = await user_service.update(user_id, user_update)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a user."""
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")
    
    success = await user_service.delete(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"} 