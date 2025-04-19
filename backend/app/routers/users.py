from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from app.routers.auth import get_current_user
from app.services.user_profile import UserProfileService

router = APIRouter(prefix="/users", tags=["users"])

class UserProfile(BaseModel):
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    preferences: Optional[dict] = None

class Document(BaseModel):
    id: str
    filename: str
    upload_date: str
    status: str
    extracted_fields: Optional[dict] = None
    submission_history: Optional[List[dict]] = None

@router.get("/me", response_model=UserProfile)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    user_service = UserProfileService()
    try:
        return await user_service.get_user_profile(current_user["email"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.put("/me", response_model=UserProfile)
async def update_my_profile(
    profile: UserProfile,
    current_user: dict = Depends(get_current_user)
):
    user_service = UserProfileService()
    try:
        return await user_service.update_user_profile(current_user["email"], profile.dict())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me/documents", response_model=List[Document])
async def get_my_documents(current_user: dict = Depends(get_current_user)):
    user_service = UserProfileService()
    try:
        return await user_service.get_user_documents(current_user["email"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/me/documents/{document_id}", response_model=Document)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_service = UserProfileService()
    try:
        return await user_service.get_document(current_user["email"], document_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) 