from typing import Dict, List, Optional, Any, Generic, TypeVar
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar('T')

class SubmissionDetails(BaseModel):
    """Detailed information about a form submission."""
    id: UUID
    template_id: UUID
    user_id: UUID
    status: str
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    error_category: Optional[str] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_duration_ms: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None

class SystemMetrics(BaseModel):
    """System-wide metrics."""
    total_submissions: int
    submissions_by_status: Dict[str, int]
    error_counts: Dict[str, int]
    average_processing_time_ms: int

class AdminAction(BaseModel):
    """Record of an admin action."""
    id: UUID
    admin_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    details: Dict[str, Any]
    created_at: datetime

class AdminActionCreate(BaseModel):
    """Data for creating a new admin action."""
    admin_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    details: Dict[str, Any]

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

class SubmissionList(PaginatedResponse):
    """Paginated list of form submissions."""
    items: List[SubmissionDetails]

class AdminActionList(PaginatedResponse):
    """Paginated list of admin actions."""
    items: List[AdminAction] 