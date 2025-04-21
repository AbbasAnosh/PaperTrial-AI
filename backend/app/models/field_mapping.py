from datetime import datetime
from typing import Optional, List, Dict, Any, Union, Callable
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4
import re

class FieldMappingRule(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    source_field: str
    target_field: str
    confidence_threshold: float = 0.7
    is_active: bool = True
    priority: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('confidence_threshold')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence threshold must be between 0 and 1')
        return v

class FieldMappingCorrection(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    source_field: str
    original_mapping: str
    corrected_mapping: str
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None
    document_id: Optional[UUID] = None

class MappingSuggestion(BaseModel):
    field: str
    confidence: float
    explanation: Optional[str] = None

class FieldMappingSuggestions(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    source_field: str
    suggested_mappings: List[MappingSuggestion]
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    document_id: Optional[UUID] = None
    is_applied: bool = False

class FieldMappingResult(BaseModel):
    source_field: str
    mapped_field: str
    confidence: float
    rule_applied: Optional[UUID] = None
    suggestions: List[MappingSuggestion] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None

class BulkRuleOperation(BaseModel):
    """Model for bulk rule update operations."""
    rule_id: UUID
    updates: Dict[str, Any] = Field(..., description="Dictionary of field names and their new values")

class PatternRule(BaseModel):
    """Model for pattern-based field mapping rules."""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    pattern: str = Field(..., description="Regular expression pattern to match field names")
    target_field: str
    transformation: Optional[str] = Field(None, description="Transformation to apply to matched fields")
    confidence_threshold: float = 0.7
    is_active: bool = True
    priority: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('pattern')
    def validate_pattern(cls, v):
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f'Invalid regular expression pattern: {str(e)}')
        return v

    @validator('confidence_threshold')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence threshold must be between 0 and 1')
        return v

class FieldTransformation(BaseModel):
    """Model for field name transformations."""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    name: str
    description: Optional[str] = None
    transformation_type: str = Field(..., description="Type of transformation (e.g., 'camelCase', 'snake_case', 'custom')")
    transformation_logic: str = Field(..., description="Python code or regex pattern for the transformation")
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None

    @validator('transformation_type')
    def validate_transformation_type(cls, v):
        allowed_types = ['camelCase', 'snake_case', 'kebab-case', 'PascalCase', 'custom']
        if v not in allowed_types:
            raise ValueError(f'Transformation type must be one of: {", ".join(allowed_types)}')
        return v

class ValidationRule(BaseModel):
    """Model for field validation rules."""
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    field_name: str
    validation_type: str = Field(..., description="Type of validation (e.g., 'regex', 'range', 'enum', 'custom')")
    validation_logic: str = Field(..., description="Validation logic (regex pattern, range values, enum values, or custom code)")
    error_message: str = Field(..., description="Error message to display when validation fails")
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[UUID] = None

    @validator('validation_type')
    def validate_validation_type(cls, v):
        allowed_types = ['regex', 'range', 'enum', 'custom']
        if v not in allowed_types:
            raise ValueError(f'Validation type must be one of: {", ".join(allowed_types)}')
        return v

class MLTrainingData(BaseModel):
    id: Optional[UUID] = None
    workspace_id: UUID
    source_field: str
    target_field: str
    document_type: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True

class MLSuggestion(BaseModel):
    target_field: str
    confidence: float
    source_field: str
    context: Dict[str, Any] = Field(default_factory=dict)

class MLModelMetadata(BaseModel):
    id: Optional[UUID] = None
    workspace_id: UUID
    name: str
    version: str
    accuracy: float
    training_data_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    class Config:
        orm_mode = True

class ModelEvaluationResult(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: Dict[str, int]
    test_data_count: int 