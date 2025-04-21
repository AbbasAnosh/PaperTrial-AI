from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    ssn: Optional[str] = None
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfileInDB(UserProfileBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 