from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class TaskType(str, Enum):
    DOCUMENT_PROCESSING = "document_processing"
    DATA_EXTRACTION = "data_extraction"
    REPORT_GENERATION = "report_generation"
    EXPORT = "export"
    IMPORT = "import"

class TaskStep(str, Enum):
    INITIALIZING = "initializing"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    EXTRACTING = "extracting"
    GENERATING = "generating"
    EXPORTING = "exporting"
    COMPLETING = "completing"

class TaskRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    current_step: Optional[TaskStep] = None
    progress: float = 0.0
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True
        
    def update_status(self, status: TaskStatus, step: Optional[TaskStep] = None, progress: Optional[float] = None):
        """Update task status and progress"""
        self.status = status
        if step:
            self.current_step = step
        if progress is not None:
            self.progress = progress
        self.updated_at = datetime.utcnow()
        
    def start_processing(self):
        """Mark task as started processing"""
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
    def complete(self, output_data: Optional[Dict[str, Any]] = None):
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.progress = 1.0
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        if output_data:
            self.output_data = output_data
            
    def fail(self, error_message: str, error_details: Optional[Dict[str, Any]] = None):
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.error_details = error_details
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
    def retry(self):
        """Increment retry count and update status"""
        self.retry_count += 1
        self.status = TaskStatus.RETRYING
        self.updated_at = datetime.utcnow()
        
    def cancel(self):
        """Mark task as cancelled"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow() 

    def update_metadata(self, tags: Optional[list] = None, project_id: Optional[str] = None, expires_at: Optional[datetime] = None):
        """Update metadata"""
        if tags:
            self.metadata['tags'] = tags
        if project_id:
            self.metadata['project_id'] = project_id
        if expires_at:
            self.metadata['expires_at'] = expires_at
        self.updated_at = datetime.utcnow()