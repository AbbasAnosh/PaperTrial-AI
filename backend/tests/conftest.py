import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import uuid
from datetime import datetime, timezone
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Mock the app module and its components
sys.modules['app'] = Mock()
sys.modules['app.db'] = Mock()
sys.modules['app.db.supabase'] = Mock()
sys.modules['app.core'] = Mock()
sys.modules['app.core.config'] = Mock()

# Mock Supabase client
class MockSupabaseClient:
    def __init__(self):
        self.tables = {}
        self.rpc_calls = {}
        self.submissions = {}  # Store submissions for RPC functions
        logger.debug("Initialized MockSupabaseClient")
    
    def table(self, table_name):
        logger.debug(f"Accessing table: {table_name}")
        if table_name not in self.tables:
            self.tables[table_name] = MockTable(self)
        return self.tables[table_name]
    
    def rpc(self, function_name, params=None):
        logger.debug(f"Calling RPC: {function_name} with params: {params}")
        if function_name not in self.rpc_calls:
            self.rpc_calls[function_name] = MockRPC(self, function_name)
        self.rpc_calls[function_name].params = params
        return self.rpc_calls[function_name]

class MockTable:
    def __init__(self, client):
        self.data = []
        self.filters = {}
        self.client = client
        logger.debug("Initialized MockTable")
    
    def insert(self, data):
        logger.debug(f"Inserting data: {data}")
        if isinstance(data, dict):
            # Only generate a new ID if one isn't provided
            if 'id' not in data:
                data['id'] = str(uuid.uuid4())
            
            # Add timestamps if not provided
            if 'created_at' not in data:
                data['created_at'] = datetime.now(timezone.utc).isoformat()
            if 'updated_at' not in data:
                data['updated_at'] = datetime.now(timezone.utc).isoformat()
                
            self.data.append(data)
            
            # Store submission for RPC functions
            if 'form_template_id' in data and 'user_id' in data:
                self.client.submissions[data['id']] = data.copy()
                logger.debug(f"Stored submission in RPC storage: {data['id']}")
                
            return self
        return self
    
    def select(self, *args):
        logger.debug(f"Select with args: {args}")
        return self
    
    def eq(self, field, value):
        logger.debug(f"Adding filter: {field} = {value}")
        self.filters[field] = value
        return self
    
    def execute(self):
        logger.debug(f"Executing with filters: {self.filters}")
        filtered_data = self.data
        for field, value in self.filters.items():
            filtered_data = [item for item in filtered_data if item.get(field) == value]
        return MockResponse(filtered_data)
    
    def update(self, data):
        logger.debug(f"Updating with data: {data}")
        updated_items = []
        for item in self.data:
            if all(item.get(k) == v for k, v in self.filters.items()):
                item.update(data)
                item['updated_at'] = datetime.now(timezone.utc).isoformat()
                updated_items.append(item)
                
                # Update submission in RPC storage
                if 'id' in item and item['id'] in self.client.submissions:
                    self.client.submissions[item['id']].update(data)
                    logger.debug(f"Updated submission in RPC storage: {item['id']} with data: {data}")
                    logger.debug(f"Updated submission in RPC storage now has status: {self.client.submissions[item['id']].get('status')}")
                    
        return self
    
    def delete(self):
        logger.debug("Deleting records")
        # Remove from RPC storage
        for item in self.data:
            if all(item.get(k) == v for k, v in self.filters.items()):
                if 'id' in item and item['id'] in self.client.submissions:
                    del self.client.submissions[item['id']]
                    logger.debug(f"Removed submission from RPC storage: {item['id']}")
        return self

class MockRPC:
    def __init__(self, client, function_name):
        self.client = client
        self.function_name = function_name
        self.params = None
        logger.debug(f"Initialized MockRPC for {function_name}")
    
    def execute(self):
        logger.debug(f"Executing RPC {self.function_name} with params: {self.params}")
        
        if self.function_name == "get_submission_status" and self.params and "p_submission_id" in self.params:
            submission_id = self.params["p_submission_id"]
            logger.debug(f"Looking for submission with ID: {submission_id}")
            logger.debug(f"Available submissions: {list(self.client.submissions.keys())}")
            
            if submission_id in self.client.submissions:
                submission = self.client.submissions[submission_id]
                logger.debug(f"Found submission: {submission}")
                
                # Get template name
                template_id = submission.get("form_template_id")
                template_name = "Unknown Template"
                
                # Try to find the template in the form_templates table
                form_templates = self.client.tables.get("form_templates", MockTable(self.client))
                for template in form_templates.data:
                    if template.get("id") == template_id:
                        template_name = template.get("name", "Unknown Template")
                        logger.debug(f"Found template name: {template_name}")
                        break
                
                # Create status response
                status_data = {
                    "submission_id": submission_id,
                    "template_name": template_name,
                    "status": submission.get("status", "submitted")  # Use "submitted" as default
                }
                logger.debug(f"Returning status data: {status_data}")
                return MockResponse([status_data])
            else:
                logger.debug(f"Submission not found in RPC storage: {submission_id}")
        
        logger.debug("Returning empty response")
        return MockResponse([])

class MockResponse:
    def __init__(self, data):
        self.data = data
        logger.debug(f"Created MockResponse with data: {data}")

@pytest.fixture(scope="session")
def supabase_client():
    """Create a mock Supabase client for testing."""
    logger.debug("Creating supabase_client fixture")
    return MockSupabaseClient()

@pytest.fixture(scope="session")
def test_user(supabase_client):
    """Create a test user for the test session."""
    logger.debug("Creating test_user fixture")
    user_data = {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "hashed_password": "test_password_hash",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Insert test user
    supabase_client.table("users").insert(user_data).execute()
    
    yield user_data
    
    # Cleanup
    supabase_client.table("users").delete().eq("id", user_data["id"]).execute()

@pytest.fixture(scope="session")
def test_form_template(supabase_client, test_user):
    """Create a test form template for the test session."""
    logger.debug("Creating test_form_template fixture")
    template_data = {
        "id": str(uuid.uuid4()),
        "name": "Test Template",
        "description": "Test Description",
        "fields": {
            "field1": {"type": "text", "required": True},
            "field2": {"type": "number", "required": False}
        },
        "validation_rules": {
            "field1": {"min_length": 3, "max_length": 50},
            "field2": {"min": 0, "max": 100}
        },
        "user_id": test_user["id"],
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Insert test template
    supabase_client.table("form_templates").insert(template_data).execute()
    
    yield template_data
    
    # Cleanup
    supabase_client.table("form_templates").delete().eq("id", template_data["id"]).execute()

@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    logger.debug("Setting up test environment variables")
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
    logger.debug("Setting up torch mock")
    import torch
    torch.save = Mock()
    torch.load = Mock(return_value=Mock())
    return torch

@pytest.fixture(autouse=True)
def mock_transformers():
    """Mock transformers library for testing."""
    logger.debug("Setting up transformers mock")
    import transformers
    transformers.AutoTokenizer.from_pretrained = Mock(return_value=Mock())
    transformers.AutoModel.from_pretrained = Mock(return_value=Mock())
    return transformers 