from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr
from supabase import create_client

from app.core.config import settings
from app.models.user import User, UserCreate
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter()

# Initialize services
user_service = UserService()
supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
auth_service = AuthService(supabase_client=supabase_client, user_service=user_service)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user = await auth_service.get_current_user(token)
        if user is None:
            raise credentials_exception
        return user
    except Exception:
        raise credentials_exception

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint to get access token."""
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/register", response_model=User)
async def register(user: UserCreate):
    """Register a new user."""
    try:
        return await user_service.create(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(auth_service.get_current_user)):
    """Get current user information."""
    return current_user
