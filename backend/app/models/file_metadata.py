from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import uuid4

class FileMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    mime_type: str
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    version: int = 1
    parent_version_id: Optional[str] = None
    is_active: bool = True
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

class FileMetadataCreate(BaseModel):
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    mime_type: str
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None

class FileMetadataUpdate(BaseModel):
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None 