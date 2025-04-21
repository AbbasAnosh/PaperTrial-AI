from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4

class AnnotationType(str, Enum):
    COMMENT = "comment"
    HIGHLIGHT = "highlight"
    SIGNATURE = "signature"
    APPROVAL = "approval"
    REJECTION = "rejection"
    SUGGESTION = "suggestion"

class AnnotationStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    APPROVED = "approved"

class Annotation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    workspace_id: str
    file_id: str
    user_id: str
    type: AnnotationType
    status: AnnotationStatus = AnnotationStatus.PENDING
    content: str
    position: Dict[str, Any]  # x, y coordinates or page number
    page_number: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AnnotationCreate(BaseModel):
    file_id: str
    type: AnnotationType
    content: str
    position: Dict[str, Any]
    page_number: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class AnnotationUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[AnnotationStatus] = None
    position: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class Comment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    workspace_id: str
    file_id: str
    user_id: str
    parent_id: Optional[str] = None
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CommentCreate(BaseModel):
    file_id: str
    content: str
    parent_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CommentUpdate(BaseModel):
    content: Optional[str] = None
    is_resolved: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None 