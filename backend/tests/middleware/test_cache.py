import pytest
from fastapi import FastAPI, Request, Response
from starlette.testclient import TestClient
from app.middleware.cache import CacheMiddleware
from app.services.cache_service import CacheService
import json

@pytest.fixture
def app():
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
        
    @app.get("/api/v1/users")
    async def users_endpoint():
        return {"users": ["user1", "user2"]}
        
    @app.get("/api/v1/users/{user_id}")
    async def user_detail_endpoint(user_id: str):
        return {"user_id": user_id, "name": f"User {user_id}"}
        
    @app.post("/test")
    async def test_post():
        return {"message": "test"}
        
    return app

@pytest.fixture
def cache_service(mocker):
    mock_cache = mocker.Mock(spec=CacheService)
    mock_cache.get.return_value = None
    mock_cache.tags = mocker.Mock()
    mock_cache.distributed = mocker.Mock()
    return mock_cache

@pytest.fixture
def client(app, cache_service):
    app.add_middleware(CacheMiddleware)
    app.state.cache_service = cache_service
    return TestClient(app)

def test_cache_middleware_get_request(client, cache_service):
    # First request - should not be cached
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "test"}
    
    # Verify cache was set
    cache_service.set.assert_called_once()
    
    # Verify tags were added
    cache_service.tags.add_tags.assert_called_once()
    
    # Verify distributed update was broadcast
    cache_service.distributed.broadcast_update.assert_called_once()
    
    # Second request - should be cached
    cache_service.get.return_value = {
        "content": json.dumps({"message": "cached"}),
        "status_code": 200,
        "headers": {},
        "media_type": "application/json"
    }
    
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "cached"}
    
def test_cache_middleware_path_tags(client, cache_service):
    # Request to a nested path
    response = client.get("/api/v1/users/123")
    assert response.status_code == 200
    
    # Verify tags were added with correct path segments
    cache_service.tags.add_tags.assert_called()
    call_args = cache_service.tags.add_tags.call_args[0]
    cache_key = call_args[0]
    tags = call_args[1]
    
    # Check that tags include path segments and hierarchies
    assert "path:api" in tags
    assert "path:v1" in tags
    assert "path:users" in tags
    assert "path:123" in tags
    assert "path_hierarchy:api/v1" in tags
    assert "path_hierarchy:api/v1/users" in tags
    assert "path_hierarchy:api/v1/users/123" in tags
    
def test_cache_middleware_post_request(client, cache_service):
    # POST request - should not be cached
    response = client.post("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "test"}
    
    # Verify cache was not set
    cache_service.set.assert_not_called()
    
    # Verify tags were not added
    cache_service.tags.add_tags.assert_not_called()
    
    # Verify distributed update was not broadcast
    cache_service.distributed.broadcast_update.assert_not_called()
    
def test_cache_middleware_error_response(client, cache_service):
    # Error response - should not be cached
    response = client.get("/nonexistent")
    assert response.status_code == 404
    
    # Verify cache was not set
    cache_service.set.assert_not_called()
    
    # Verify tags were not added
    cache_service.tags.add_tags.assert_not_called()
    
    # Verify distributed update was not broadcast
    cache_service.distributed.broadcast_update.assert_not_called()
    
def test_cache_middleware_no_cache_service(app):
    # Test without cache service
    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "test"} 