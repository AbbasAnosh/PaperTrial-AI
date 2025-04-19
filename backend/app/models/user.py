from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None
    preferences: Optional[Dict] = {}

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserInDB(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    is_superuser: bool = False

    class Config:
        from_attributes = True 