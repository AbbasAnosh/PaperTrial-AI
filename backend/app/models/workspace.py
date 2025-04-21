from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4

class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"

class WorkspaceMember(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    workspace_id: str
    user_id: str
    role: WorkspaceRole
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Workspace(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class WorkspaceInvite(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    workspace_id: str
    email: str
    role: WorkspaceRole
    invited_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    status: str = "pending"  # pending, accepted, rejected, expired
    metadata: Dict[str, Any] = Field(default_factory=dict)

class WorkspaceInviteCreate(BaseModel):
    email: str
    role: WorkspaceRole
    expires_at: datetime
    metadata: Optional[Dict[str, Any]] = None 