"""
ML models and configurations.

This module defines the data models for ML features including
model configurations, metrics, and training data.
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

class ModelMetrics(BaseModel):
    """Model performance metrics."""
    accuracy: float = Field(..., ge=0.0, le=1.0)
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)
    training_time: Optional[float] = None
    inference_time: Optional[float] = None

class TrainingConfig(BaseModel):
    """Model training configuration."""
    model_name: str
    base_model: str = "bert-base-uncased"
    num_labels: int
    learning_rate: float = 1e-5
    batch_size: int = 32
    epochs: int = 10
    max_length: int = 512
    warmup_steps: int = 0
    weight_decay: float = 0.01
    early_stopping: bool = True
    early_stopping_patience: int = 3

class MLModel(BaseModel):
    """ML model metadata and configuration."""
    id: Optional[str] = None
    name: str
    base_model: str
    version: str = "1.0.0"
    metrics: ModelMetrics
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    parameters: Dict[str, any] = Field(default_factory=dict)

    class Config:
        schema_extra = {
            "example": {
                "name": "document-classifier",
                "base_model": "bert-base-uncased",
                "version": "1.0.0",
                "metrics": {
                    "accuracy": 0.95,
                    "precision": 0.94,
                    "recall": 0.93,
                    "f1_score": 0.935,
                    "training_time": 3600.0,
                    "inference_time": 0.1
                },
                "description": "Document classification model for form processing",
                "tags": ["document", "classification", "forms"],
                "parameters": {
                    "max_length": 512,
                    "batch_size": 32
                }
            }
        }

class TrainingData(BaseModel):
    """Training data for model training."""
    id: Optional[str] = None
    model_id: str
    text: str
    labels: List[str]
    metadata: Dict[str, any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "model_id": "doc-classifier-1",
                "text": "Sample document text for training",
                "labels": ["invoice", "receipt"],
                "metadata": {
                    "source": "manual",
                    "verified": True
                }
            }
        }

class FieldMapping(BaseModel):
    """Field mapping configuration."""
    id: Optional[str] = None
    template_id: str
    field_name: str
    patterns: List[str]
    confidence_threshold: float = 0.8
    validation_rules: Dict[str, any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "template_id": "invoice-template-1",
                "field_name": "total_amount",
                "patterns": [
                    r"total:?\s*\$?\d+(\.\d{2})?",
                    r"amount:?\s*\$?\d+(\.\d{2})?"
                ],
                "confidence_threshold": 0.85,
                "validation_rules": {
                    "type": "number",
                    "min": 0,
                    "max": 1000000
                }
            }
        } 