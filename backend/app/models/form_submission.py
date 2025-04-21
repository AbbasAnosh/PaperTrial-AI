"""
Pydantic model for form submissions with robust validation.
"""

from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator
import uuid

class FormSubmission(BaseModel):
    """Model representing a form submission with robust validation"""
    
    id: Optional[str] = Field(None, description="Unique identifier for the submission")
    user_id: str = Field(..., description="ID of the user who created the submission")
    form_id: str = Field(..., description="ID of the form being submitted")
    form_data: Dict[str, Any] = Field(default_factory=dict, description="The form data to be submitted")
    screenshots: Dict[str, Any] = Field(default_factory=dict, description="Screenshots taken during form filling")
    status: Literal["queued", "processing", "submitted", "completed", "failed", "cancelled"] = Field(
        "queued", 
        description="Current status of the submission"
    )
    message: Optional[str] = Field(None, description="Status message or error description")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="History of events for the submission")
    created_at: Optional[datetime] = Field(None, description="Timestamp when the submission was created")
    updated_at: Optional[datetime] = Field(None, description="Timestamp when the submission was last updated")
    confirmation_number: Optional[str] = Field(None, description="Confirmation number from the form submission")
    error: Optional[str] = Field(None, description="Error message if submission failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the submission")
    document_id: Optional[str] = Field(None, description="ID of the associated document")
    response_data: Dict[str, Any] = Field(default_factory=dict, description="Response data from the form submission")
    retry_count: int = Field(0, description="Number of retry attempts for failed submissions")
    max_retries: int = Field(3, description="Maximum number of retry attempts")
    last_retry_at: Optional[datetime] = Field(None, description="Timestamp of the last retry attempt")
    is_deleted: bool = Field(False, description="Soft delete flag")
    deleted_at: Optional[datetime] = Field(None, description="Timestamp when the submission was soft deleted")
    
    @validator("id", pre=True, always=True)
    def set_id(cls, v):
        """Generate UUID if id is not provided"""
        return v if v else str(uuid.uuid4())
    
    @validator("created_at", pre=True, always=True)
    def set_created_at(cls, v):
        """Set created_at to current time if not provided"""
        return v if v else datetime.utcnow()
    
    @validator("updated_at", pre=True, always=True)
    def set_updated_at(cls, v, values):
        """Set updated_at to current time if not provided or if status changes"""
        if "status" in values and values["status"] != "queued":
            return datetime.utcnow()
        return v if v else values.get("created_at", datetime.utcnow())
    
    @validator("events")
    def validate_events(cls, v):
        """Validate event structure"""
        for event in v:
            if not isinstance(event, dict):
                raise ValueError("Each event must be a dictionary")
            if "type" not in event:
                raise ValueError("Each event must have a 'type' field")
            if "timestamp" not in event:
                event["timestamp"] = datetime.utcnow().isoformat()
        return v
    
    @root_validator
    def validate_status_transitions(cls, values):
        """Validate status transitions and set appropriate fields"""
        status = values.get("status")
        error = values.get("error")
        message = values.get("message")
        
        # Set error message if status is failed
        if status == "failed" and not error:
            values["error"] = message or "Submission failed without specific error"
        
        # Set confirmation number if status is completed
        if status == "completed" and not values.get("confirmation_number"):
            values["confirmation_number"] = f"CONF-{uuid.uuid4().hex[:8].upper()}"
        
        # Update retry count for failed submissions
        if status == "failed" and values.get("retry_count", 0) < values.get("max_retries", 3):
            values["retry_count"] = values.get("retry_count", 0) + 1
            values["last_retry_at"] = datetime.utcnow()
            values["status"] = "queued"  # Reset to queued for retry
        
        return values
    
    def add_event(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """Add an event to the submission history"""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {}
        }
        self.events.append(event)
        self.updated_at = datetime.utcnow()
    
    def mark_as_deleted(self) -> None:
        """Soft delete the submission"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.add_event("deleted", {"deleted_at": self.deleted_at.isoformat()})
    
    def can_retry(self) -> bool:
        """Check if the submission can be retried"""
        return (
            self.status in ["failed", "cancelled"] and 
            self.retry_count < self.max_retries
        )
    
    def prepare_for_retry(self) -> bool:
        """Prepare the submission for a retry attempt"""
        if not self.can_retry():
            return False
        
        self.status = "queued"
        self.error = None
        self.message = f"Retry attempt {self.retry_count + 1} of {self.max_retries}"
        self.add_event("retry_attempt", {
            "attempt": self.retry_count + 1,
            "max_attempts": self.max_retries
        })
        return True

    class Config:
        """Pydantic model configuration"""
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "user123",
                "form_id": "form456",
                "form_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "message": "Hello world"
                },
                "screenshots": {
                    "form": "base64_encoded_image_data",
                    "confirmation": "base64_encoded_image_data"
                },
                "status": "completed",
                "message": "Form submitted successfully",
                "events": [
                    {
                        "type": "form_filled",
                        "timestamp": "2024-03-24T12:00:00Z",
                        "data": {"field": "name", "value": "John Doe"}
                    }
                ],
                "created_at": "2024-03-24T11:59:00Z",
                "updated_at": "2024-03-24T12:00:00Z",
                "confirmation_number": "CONF123456",
                "error": None,
                "metadata": {
                    "browser": "Chrome",
                    "os": "Windows",
                    "ip": "192.168.1.1"
                },
                "document_id": "doc789",
                "response_data": {
                    "status": "success",
                    "confirmation": "CONF123456",
                    "timestamp": "2024-03-24T12:00:00Z"
                },
                "retry_count": 0,
                "max_retries": 3,
                "last_retry_at": None,
                "is_deleted": False,
                "deleted_at": None
            }
        } 