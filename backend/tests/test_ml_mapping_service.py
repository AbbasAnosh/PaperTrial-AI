import pytest
import torch
from app.services.ml_mapping_service import MLMappingService
from app.models.ml import FieldSuggestion

@pytest.fixture
def ml_mapping_service(supabase_client):
    return MLMappingService(supabase_client)

@pytest.fixture
def sample_mapping_data():
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

async def test_train_model(ml_mapping_service, sample_mapping_data):
    """Test model training functionality."""
    model_name = "test_model"
    workspace_id = "test_workspace"
    
    result = await ml_mapping_service.train_model(
        model_name=model_name,
        workspace_id=workspace_id,
        training_data=sample_mapping_data
    )
    
    assert result["model_name"] == model_name
    assert result["workspace_id"] == workspace_id
    assert "accuracy" in result
    assert "training_samples" in result
    assert result["training_samples"] == len(sample_mapping_data)

async def test_add_training_data(ml_mapping_service, sample_mapping_data):
    """Test adding training data."""
    model_name = "test_model"
    workspace_id = "test_workspace"
    
    # First train the model
    await ml_mapping_service.train_model(
        model_name=model_name,
        workspace_id=workspace_id,
        training_data=sample_mapping_data
    )
    
    # Add more training data
    new_data = [
        {
            "source_field": "customer_name",
            "target_field": "client_name",
            "document_type": "invoice",
            "confidence": 0.92
        }
    ]
    
    result = await ml_mapping_service.add_training_data(
        model_name=model_name,
        workspace_id=workspace_id,
        training_data=new_data
    )
    
    assert result["model_name"] == model_name
    assert result["workspace_id"] == workspace_id
    assert "accuracy" in result
    assert "training_samples" in result
    assert result["training_samples"] == len(sample_mapping_data) + len(new_data)

async def test_get_suggestions(ml_mapping_service, sample_mapping_data):
    """Test field mapping suggestions."""
    model_name = "test_model"
    workspace_id = "test_workspace"
    
    # First train the model
    await ml_mapping_service.train_model(
        model_name=model_name,
        workspace_id=workspace_id,
        training_data=sample_mapping_data
    )
    
    # Get suggestions
    suggestions = await ml_mapping_service.get_suggestions(
        source_field="invoice_number",
        document_type="invoice",
        model_name=model_name,
        workspace_id=workspace_id
    )
    
    assert isinstance(suggestions, list)
    assert all(isinstance(s, FieldSuggestion) for s in suggestions)
    assert len(suggestions) > 0
    assert all(0 <= s.confidence <= 1 for s in suggestions)

async def test_save_and_load_model(ml_mapping_service, sample_mapping_data):
    """Test saving and loading a trained model."""
    model_name = "test_model"
    workspace_id = "test_workspace"
    
    # First train the model
    await ml_mapping_service.train_model(
        model_name=model_name,
        workspace_id=workspace_id,
        training_data=sample_mapping_data
    )
    
    # Save the model
    await ml_mapping_service.save_model(
        model_name=model_name,
        workspace_id=workspace_id
    )
    
    # Load the model
    model = await ml_mapping_service.load_model(
        model_name=model_name,
        workspace_id=workspace_id
    )
    
    assert model is not None
    assert isinstance(model, torch.nn.Module)

async def test_text_encoder(ml_mapping_service):
    """Test the text encoder functionality."""
    texts = ["invoice number", "total amount", "customer name"]
    
    # Get embeddings
    embeddings = await ml_mapping_service._encode_texts(texts)
    
    assert isinstance(embeddings, torch.Tensor)
    assert embeddings.shape[0] == len(texts)
    assert embeddings.shape[1] == 768  # DeBERTa-v3-small embedding size 