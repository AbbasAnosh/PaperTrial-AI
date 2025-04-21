import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import torch
import json

from app.services.ml_service import MLService
from app.services.ml_db_service import MLDatabaseService
from app.services.ml_storage_service import MLStorageService
from app.services.ml_monitoring_service import MLMonitoringService
from app.models.ml import (
    MLModel, MLModelCreate, MLModelEvaluation, MLModelEvaluationCreate,
    MLTrainingData, MLTrainingDataCreate, ModelEvaluationResult, FieldSuggestion
)
from app.core.errors import ProcessingError, DatabaseError, StorageError, MonitoringError

@pytest.fixture
def ml_service():
    return MLService()

@pytest.fixture
def ml_db_service():
    return MLDatabaseService()

@pytest.fixture
def ml_storage_service():
    return MLStorageService()

@pytest.fixture
def ml_monitoring_service():
    return MLMonitoringService()

@pytest.fixture
def sample_training_data():
    return [
        MLTrainingData(
            source_field="invoice_number",
            target_field="invoice_id",
            document_type="invoice"
        ),
        MLTrainingData(
            source_field="total_amount",
            target_field="amount",
            document_type="invoice"
        )
    ]

@pytest.fixture
def sample_model_metadata():
    return MLModelCreate(
        workspace_id=uuid4(),
        name="test_model",
        version="1.0",
        description="Test model",
        model_type="transformer",
        storage_path="/path/to/model",
        hyperparameters={"learning_rate": 0.001},
        metrics={"accuracy": 0.95}
    )

@pytest.mark.asyncio
async def test_train_model(ml_service, sample_training_data):
    """Test model training."""
    # Mock the necessary dependencies
    with patch("torch.save") as mock_save:
        # Train the model
        metadata = ml_service.train_model(str(uuid4()), sample_training_data)
        
        # Verify the results
        assert isinstance(metadata, MLModelMetadata)
        assert metadata.accuracy > 0
        assert metadata.training_samples == len(sample_training_data)
        mock_save.assert_called_once()

@pytest.mark.asyncio
async def test_evaluate_model(ml_service, sample_training_data):
    """Test model evaluation."""
    # First train a model
    workspace_id = str(uuid4())
    ml_service.train_model(workspace_id, sample_training_data)
    
    # Evaluate the model
    result = ml_service.evaluate_model(sample_training_data)
    
    # Verify the results
    assert isinstance(result, ModelEvaluationResult)
    assert 0 <= result.accuracy <= 1
    assert 0 <= result.precision <= 1
    assert 0 <= result.recall <= 1
    assert 0 <= result.f1_score <= 1
    assert isinstance(result.confusion_matrix, list)

@pytest.mark.asyncio
async def test_get_suggestions(ml_service, sample_training_data):
    """Test getting field mapping suggestions."""
    # First train a model
    workspace_id = str(uuid4())
    ml_service.train_model(workspace_id, sample_training_data)
    
    # Get suggestions
    suggestions = ml_service.get_suggestions("invoice_number", "invoice")
    
    # Verify the results
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    assert all(isinstance(s, FieldSuggestion) for s in suggestions)
    assert all(0 <= s.confidence <= 1 for s in suggestions)

@pytest.mark.asyncio
async def test_create_model(ml_db_service, sample_model_metadata):
    """Test creating a model in the database."""
    # Mock Supabase client
    mock_response = Mock()
    mock_response.data = [sample_model_metadata.dict()]
    ml_db_service.supabase.table().insert().execute = Mock(return_value=mock_response)
    
    # Create the model
    model = await ml_db_service.create_model(sample_model_metadata, uuid4())
    
    # Verify the results
    assert isinstance(model, MLModel)
    assert model.name == sample_model_metadata.name
    assert model.version == sample_model_metadata.version

@pytest.mark.asyncio
async def test_save_model(ml_storage_service):
    """Test saving a model to storage."""
    # Mock Supabase storage
    ml_storage_service.supabase.storage.from_().upload = Mock()
    
    # Create test data
    workspace_id = uuid4()
    model_name = "test_model"
    version = "1.0"
    model_data = torch.randn(10, 10).numpy().tobytes()
    metadata = {"accuracy": 0.95}
    
    # Save the model
    path = await ml_storage_service.save_model(
        workspace_id, model_name, version, model_data, metadata
    )
    
    # Verify the results
    assert isinstance(path, str)
    assert model_name in path
    assert version in path
    ml_storage_service.supabase.storage.from_().upload.assert_called()

@pytest.mark.asyncio
async def test_log_model_metrics(ml_monitoring_service):
    """Test logging model metrics."""
    # Mock Supabase client
    ml_monitoring_service.supabase.table().insert().execute = Mock()
    
    # Create test data
    model_id = uuid4()
    metrics = {
        "accuracy": 0.95,
        "precision": 0.92,
        "recall": 0.94,
        "f1_score": 0.93
    }
    
    # Log the metrics
    await ml_monitoring_service.log_model_metrics(model_id, metrics)
    
    # Verify the results
    ml_monitoring_service.supabase.table().insert().execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_model_performance_summary(ml_monitoring_service):
    """Test getting model performance summary."""
    # Mock Supabase client
    mock_model_metrics = [
        {"metrics": {"accuracy": 0.95, "precision": 0.92, "recall": 0.94, "f1_score": 0.93}},
        {"metrics": {"accuracy": 0.96, "precision": 0.93, "recall": 0.95, "f1_score": 0.94}}
    ]
    mock_inference_metrics = [
        {"latency_ms": 100, "input_size": 1000, "success": True},
        {"latency_ms": 120, "input_size": 2000, "success": True},
        {"latency_ms": 150, "input_size": 1500, "success": False}
    ]
    
    ml_monitoring_service.get_model_metrics = Mock(return_value=mock_model_metrics)
    ml_monitoring_service.get_inference_metrics = Mock(return_value=mock_inference_metrics)
    
    # Get the summary
    summary = await ml_monitoring_service.get_model_performance_summary(uuid4())
    
    # Verify the results
    assert isinstance(summary, dict)
    assert "time_window" in summary
    assert "model_metrics" in summary
    assert "inference_metrics" in summary
    assert summary["inference_metrics"]["success_rate"] == 2/3 