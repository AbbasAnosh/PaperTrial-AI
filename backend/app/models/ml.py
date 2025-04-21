"""
ML models for request and response validation.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class MLModelBase(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    model_type: str
    storage_path: str
    hyperparameters: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    is_active: bool = True

class MLModelCreate(MLModelBase):
    workspace_id: UUID

class MLModel(MLModelBase):
    id: UUID
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True

class MLTrainingDataBase(BaseModel):
    source_field: str
    target_field: str
    document_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MLTrainingDataCreate(MLTrainingDataBase):
    workspace_id: UUID
    model_id: UUID

class MLTrainingData(MLTrainingDataBase):
    id: UUID
    workspace_id: UUID
    model_id: UUID
    created_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True

class MLModelEvaluationBase(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: List[List[int]]
    test_data_size: int

class MLModelEvaluationCreate(MLModelEvaluationBase):
    model_id: UUID

class MLModelEvaluation(MLModelEvaluationBase):
    id: UUID
    model_id: UUID
    evaluation_date: datetime
    created_by: UUID

    class Config:
        from_attributes = True

class ModelEvaluationResult(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: List[List[int]]
    feature_importance: Dict[str, float]

class ModelTrainingRequest(BaseModel):
    """Request model for training a new ML model."""
    workspace_id: str = Field(..., description="ID of the workspace")
    model_name: str = Field(..., description="Name of the model")
    training_data: List[Dict[str, Any]] = Field(..., description="Training data for the model")

class ModelEvaluationRequest(BaseModel):
    """Request model for evaluating a trained ML model."""
    model_id: str = Field(..., description="ID of the model to evaluate")
    test_data: List[Dict[str, Any]] = Field(..., description="Test data for evaluation")

class ModelSuggestionRequest(BaseModel):
    """Request model for getting field mapping suggestions."""
    model_id: str = Field(..., description="ID of the model to use for suggestions")
    source_fields: List[str] = Field(..., description="List of source fields to get suggestions for")

class ModelResponse(BaseModel):
    """Response model for model details."""
    id: str = Field(..., description="ID of the model")
    name: str = Field(..., description="Name of the model")
    workspace_id: str = Field(..., description="ID of the workspace")
    created_by: str = Field(..., description="ID of the user who created the model")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metrics: Dict[str, float] = Field(..., description="Model performance metrics")
    status: str = Field(..., description="Status of the model (training, trained, failed)")
    version: str = Field(..., description="Version of the model")

class ModelEvaluationResponse(BaseModel):
    """Response model for model evaluation results."""
    model_id: str = Field(..., description="ID of the evaluated model")
    accuracy: float = Field(..., description="Accuracy score")
    precision: float = Field(..., description="Precision score")
    recall: float = Field(..., description="Recall score")
    f1_score: float = Field(..., description="F1 score")
    confusion_matrix: List[List[int]] = Field(..., description="Confusion matrix")
    evaluation_timestamp: datetime = Field(..., description="Evaluation timestamp")

class FieldSuggestion(BaseModel):
    """Response model for field mapping suggestions."""
    source_field: str = Field(..., description="Source field name")
    target_field: str = Field(..., description="Suggested target field name")
    confidence: float = Field(..., description="Confidence score of the suggestion")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the suggestion")

class MLTrainingData(BaseModel):
    source_field: str
    target_field: str
    document_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None 