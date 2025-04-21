import pytest
import torch
from app.services.ml_service import MLService
from app.models.ml import FieldSuggestion

@pytest.fixture
def ml_service(supabase_client):
    return MLService(supabase_client)

@pytest.fixture
def sample_training_data():
    return [
        {
            "source_field": "invoice_number",
            "target_field": "invoice_id",
            "document_type": "invoice",
            "confidence": 0.95
        },
        {
            "source_field": "total_amount",
            "target_field": "amount",
            "document_type": "invoice",
            "confidence": 0.88
        }
    ]

@pytest.fixture
def sample_test_data():
    return [
        {
            "source_field": "invoice_number",
            "target_field": "invoice_id",
            "document_type": "invoice"
        },
        {
            "source_field": "total_amount",
            "target_field": "amount",
            "document_type": "invoice"
        }
    ]

async def test_train_model(ml_service, sample_training_data):
    """Test model training functionality."""
    model_name = "test_model"
    workspace_id = "test_workspace"
    
    result = await ml_service.train_model(
        model_name=model_name,
        workspace_id=workspace_id,
        training_data=sample_training_data
    )
    
    assert result["model_name"] == model_name
    assert result["workspace_id"] == workspace_id
    assert "accuracy" in result
    assert "training_samples" in result
    assert result["training_samples"] == len(sample_training_data)

async def test_evaluate_model(ml_service, sample_training_data, sample_test_data):
    """Test model evaluation functionality."""
    model_name = "test_model"
    workspace_id = "test_workspace"
    
    # First train the model
    await ml_service.train_model(
        model_name=model_name,
        workspace_id=workspace_id,
        training_data=sample_training_data
    )
    
    # Then evaluate it
    result = await ml_service.evaluate_model(
        model_name=model_name,
        workspace_id=workspace_id,
        test_data=sample_test_data
    )
    
    assert "accuracy" in result
    assert "precision" in result
    assert "recall" in result
    assert "f1_score" in result
    assert all(0 <= score <= 1 for score in [result["accuracy"], result["precision"], result["recall"], result["f1_score"]])

async def test_get_suggestions(ml_service, sample_training_data):
    """Test field mapping suggestions."""
    model_name = "test_model"
    workspace_id = "test_workspace"
    
    # First train the model
    await ml_service.train_model(
        model_name=model_name,
        workspace_id=workspace_id,
        training_data=sample_training_data
    )
    
    # Get suggestions
    suggestions = await ml_service.get_suggestions(
        source_field="invoice_number",
        document_type="invoice",
        model_name=model_name,
        workspace_id=workspace_id
    )
    
    assert isinstance(suggestions, list)
    assert all(isinstance(s, FieldSuggestion) for s in suggestions)
    assert len(suggestions) > 0
    assert all(0 <= s.confidence <= 1 for s in suggestions)

async def test_list_models(ml_service):
    """Test listing trained models."""
    workspace_id = "test_workspace"
    
    models = await ml_service.list_models(workspace_id)
    
    assert isinstance(models, list)
    assert all(isinstance(m, dict) for m in models)
    assert all("model_name" in m for m in models)
    assert all("workspace_id" in m for m in models)

async def test_load_model(ml_service, sample_training_data):
    """Test loading a trained model."""
    model_name = "test_model"
    workspace_id = "test_workspace"
    
    # First train the model
    await ml_service.train_model(
        model_name=model_name,
        workspace_id=workspace_id,
        training_data=sample_training_data
    )
    
    # Load the model
    model = await ml_service.load_model(
        model_name=model_name,
        workspace_id=workspace_id
    )
    
    assert model is not None
    assert isinstance(model, torch.nn.Module) 