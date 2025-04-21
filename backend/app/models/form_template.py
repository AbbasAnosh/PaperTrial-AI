"""
Form template models for managing form definitions and field mappings.
"""

from pydantic import BaseModel, Field, validator, HttpUrl
from typing import List, Optional, Dict, Any, Union, Set
from datetime import datetime
from enum import Enum
import re

class FieldType(str, Enum):
    """Types of form fields."""
    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SELECT = "select"
    TEXTAREA = "textarea"
    FILE = "file"
    HIDDEN = "hidden"

class ValidationRule(BaseModel):
    """Validation rule for a form field."""
    rule_type: str = Field(..., description="Type of validation rule")
    value: Optional[Any] = Field(None, description="Value for the validation rule")
    message: str = Field(..., description="Error message for validation failure")

class FormField(BaseModel):
    """Definition of a form field."""
    id: str = Field(..., description="Unique identifier for the field")
    name: str = Field(..., description="Field name for form submission")
    label: str = Field(..., description="Display label for the field")
    field_type: FieldType = Field(..., description="Type of the field")
    required: bool = Field(False, description="Whether the field is required")
    placeholder: Optional[str] = Field(None, description="Placeholder text")
    default_value: Optional[Any] = Field(None, description="Default value for the field")
    options: Optional[List[Dict[str, Any]]] = Field(None, description="Options for select/radio fields")
    validation_rules: Optional[List[ValidationRule]] = Field(None, description="Validation rules for the field")
    mapping_key: Optional[str] = Field(None, description="Key for mapping extracted data to this field")
    confidence_threshold: Optional[float] = Field(0.7, description="Minimum confidence score for auto-filling")
    help_text: Optional[str] = Field(None, description="Help text for the field")
    order: int = Field(0, description="Display order of the field")
    dependencies: Optional[List[str]] = Field(None, description="Fields this field depends on")
    conditional_logic: Optional[Dict[str, Any]] = Field(None, description="Conditional logic for field visibility")

class SubmissionMethod(str, Enum):
    """Methods for form submission."""
    HTTP_POST = "http_post"
    API = "api"
    EMAIL = "email"
    FILE = "file"
    CUSTOM = "custom"
    WEB_AUTOMATION = "web_automation"

class TemplateCategory(BaseModel):
    """Category for organizing form templates."""
    id: str = Field(..., description="Unique identifier for the category")
    name: str = Field(..., description="Name of the category")
    description: Optional[str] = Field(None, description="Description of the category")
    parent_id: Optional[str] = Field(None, description="ID of the parent category")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="User ID of the creator")

class TemplateSharing(BaseModel):
    """Sharing settings for a form template."""
    is_public: bool = Field(False, description="Whether the template is publicly accessible")
    shared_with: Set[str] = Field(default_factory=set, description="Set of user IDs the template is shared with")
    permissions: Dict[str, List[str]] = Field(
        default_factory=lambda: {"view": [], "edit": [], "share": []},
        description="Permissions for shared users"
    )

class FormTemplate(BaseModel):
    """Template for a form with fields and submission settings."""
    id: str = Field(..., description="Unique identifier for the template")
    name: str = Field(..., description="Name of the form template")
    description: Optional[str] = Field(None, description="Description of the form")
    fields: List[FormField] = Field(..., description="Fields in the form")
    submission_method: SubmissionMethod = Field(..., description="Method for form submission")
    submission_url: Optional[HttpUrl] = Field(None, description="URL for form submission")
    submission_headers: Optional[Dict[str, str]] = Field(None, description="Headers for API submission")
    submission_auth: Optional[Dict[str, Any]] = Field(None, description="Authentication for submission")
    submission_params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for submission")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    created_by: str = Field(..., description="User ID of the creator")
    is_active: bool = Field(True, description="Whether the template is active")
    version: int = Field(1, description="Template version number")
    category_id: Optional[str] = Field(None, description="ID of the template category")
    tags: List[str] = Field(default_factory=list, description="Tags for the template")
    sharing: TemplateSharing = Field(default_factory=TemplateSharing, description="Sharing settings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    last_used: Optional[datetime] = Field(None, description="Last time the template was used")
    usage_count: int = Field(0, description="Number of times the template has been used")

class FormTemplateCreate(BaseModel):
    """Model for creating a new form template."""
    name: str = Field(..., description="Name of the form template")
    description: Optional[str] = Field(None, description="Description of the form")
    fields: List[FormField] = Field(..., description="Fields in the form")
    submission_method: SubmissionMethod = Field(..., description="Method for form submission")
    submission_url: Optional[HttpUrl] = Field(None, description="URL for form submission")
    submission_headers: Optional[Dict[str, str]] = Field(None, description="Headers for API submission")
    submission_auth: Optional[Dict[str, Any]] = Field(None, description="Authentication for submission")
    submission_params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for submission")
    category_id: Optional[str] = Field(None, description="ID of the template category")
    tags: List[str] = Field(default_factory=list, description="Tags for the template")
    sharing: Optional[TemplateSharing] = Field(None, description="Sharing settings")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class FormTemplateUpdate(BaseModel):
    """Model for updating a form template."""
    name: Optional[str] = Field(None, description="Name of the form template")
    description: Optional[str] = Field(None, description="Description of the form")
    fields: Optional[List[FormField]] = Field(None, description="Fields in the form")
    submission_method: Optional[SubmissionMethod] = Field(None, description="Method for form submission")
    submission_url: Optional[HttpUrl] = Field(None, description="URL for form submission")
    submission_headers: Optional[Dict[str, str]] = Field(None, description="Headers for API submission")
    submission_auth: Optional[Dict[str, Any]] = Field(None, description="Authentication for submission")
    submission_params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters for submission")
    is_active: Optional[bool] = Field(None, description="Whether the template is active")
    category_id: Optional[str] = Field(None, description="ID of the template category")
    tags: Optional[List[str]] = Field(None, description="Tags for the template")
    sharing: Optional[TemplateSharing] = Field(None, description="Sharing settings")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class FormSubmission(BaseModel):
    """Model for a form submission."""
    id: str = Field(..., description="Unique identifier for the submission")
    template_id: str = Field(..., description="ID of the form template")
    data: Dict[str, Any] = Field(..., description="Submitted form data")
    status: str = Field(..., description="Submission status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Submission timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    created_by: str = Field(..., description="User ID of the submitter")
    source_document_id: Optional[str] = Field(None, description="ID of the source document")
    error_message: Optional[str] = Field(None, description="Error message if submission failed")
    response_data: Optional[Dict[str, Any]] = Field(None, description="Response data from submission")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    processing_time: Optional[float] = Field(None, description="Time taken to process the submission")
    retry_count: int = Field(0, description="Number of retry attempts")
    last_retry: Optional[datetime] = Field(None, description="Timestamp of last retry")

class FormSubmissionCreate(BaseModel):
    """Model for creating a new form submission."""
    template_id: str = Field(..., description="ID of the form template")
    data: Dict[str, Any] = Field(..., description="Submitted form data")
    source_document_id: Optional[str] = Field(None, description="ID of the source document")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata") 