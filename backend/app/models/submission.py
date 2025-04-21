from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

class SubmissionBase(BaseModel):
    user_id: str
    form_id: str
    form_data: Dict[str, Any]
    status: str = Field(default="queued")
    message: Optional[str] = None
    events: list = Field(default_factory=list)

class SubmissionCreate(SubmissionBase):
    pass

class SubmissionInDB(SubmissionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 