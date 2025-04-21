"""
User models for authentication and user management.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None

class UserBase(BaseModel):
    """Base user model with common attributes."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True
    is_admin: bool = False

class UserCreate(UserBase):
    """Model for creating a new user."""
    password: str = Field(..., min_length=8)

    @validator('password')
    def validate_password(cls, v):
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$', v):
            raise ValueError('Password must contain at least one letter and one number')
        return v

class UserUpdate(BaseModel):
    """Model for updating user information."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

    @validator('password')
    def validate_password(cls, v):
        if v is not None and not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$', v):
            raise ValueError('Password must contain at least one letter and one number')
        return v

class User(UserBase):
    """Model for user responses."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserInDB(UserBase):
    """User model with hashed password."""
    id: str = Field(..., alias="_id")
    hashed_password: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        allow_population_by_field_name = True

class UserResponse(UserBase):
    """User model for API responses."""
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True 