import pytest
import os
from unittest.mock import Mock
from supabase import create_client, Client

@pytest.fixture(scope="session")
def supabase_client():
    """Create a mock Supabase client for testing."""
    mock_client = Mock(spec=Client)
    
    # Mock storage operations
    mock_storage = Mock()
    mock_storage.from_ = Mock(return_value=mock_storage)
    mock_storage.upload = Mock(return_value={"path": "test/path"})
    mock_storage.download = Mock(return_value=b"test_data")
    mock_client.storage = mock_storage
    
    # Mock database operations
    mock_table = Mock()
    mock_table.insert = Mock(return_value=mock_table)
    mock_table.select = Mock(return_value=mock_table)
    mock_table.update = Mock(return_value=mock_table)
    mock_table.delete = Mock(return_value=mock_table)
    mock_table.execute = Mock(return_value=Mock(data=[]))
    mock_client.table = Mock(return_value=mock_table)
    
    return mock_client

@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    os.environ["SUPABASE_URL"] = "http://test.supabase.co"
    os.environ["SUPABASE_KEY"] = "test_key"
    os.environ["ML_MODELS_BUCKET"] = "test-ml-models"
    os.environ["ML_CACHE_DIR"] = "test_cache"
    
    yield
    
    # Clean up
    del os.environ["SUPABASE_URL"]
    del os.environ["SUPABASE_KEY"]
    del os.environ["ML_MODELS_BUCKET"]
    del os.environ["ML_CACHE_DIR"]

@pytest.fixture(autouse=True)
def mock_torch():
    """Mock PyTorch operations for testing."""
    import torch
    torch.save = Mock()
    torch.load = Mock(return_value=Mock())
    return torch

@pytest.fixture(autouse=True)
def mock_transformers():
    """Mock transformers library for testing."""
    import transformers
    transformers.AutoTokenizer.from_pretrained = Mock(return_value=Mock())
    transformers.AutoModel.from_pretrained = Mock(return_value=Mock())
    return transformers 