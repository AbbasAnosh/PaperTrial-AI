import pytest
from datetime import datetime, timedelta
from app.services.security_service import SecurityService
from redis import Redis
import time
import json
import hmac
import hashlib

@pytest.fixture
def redis_client():
    """Create a Redis client for testing"""
    client = Redis(host='localhost', port=6379, db=1)  # Use DB 1 for testing
    yield client
    client.flushdb()  # Clean up after tests
    client.close()

@pytest.fixture
def security_service(redis_client):
    """Create a SecurityService instance"""
    return SecurityService(redis_client)

def test_api_key_validation(security_service):
    """Test API key validation"""
    # Create API key
    success, api_key, error = security_service.create_api_key("test_user")
    assert success
    assert api_key
    assert not error
    
    # Validate API key
    is_valid, error = security_service.validate_api_key(api_key)
    assert is_valid
    assert not error
    
    # Test invalid key
    is_valid, error = security_service.validate_api_key("invalid_key")
    assert not is_valid
    assert error == "Invalid API key"
    
    # Test expired key
    success, api_key, error = security_service.create_api_key("test_user", expires_in_days=0)
    assert success
    time.sleep(1)  # Wait for key to expire
    is_valid, error = security_service.validate_api_key(api_key)
    assert not is_valid
    assert error == "API key has expired"
    
    # Test revoked key
    success, api_key, error = security_service.create_api_key("test_user")
    assert success
    revoke_success, error = security_service.revoke_api_key(api_key)
    assert revoke_success
    assert not error
    is_valid, error = security_service.validate_api_key(api_key)
    assert not is_valid
    assert error == "API key has been revoked"

def test_request_signature_validation(security_service):
    """Test request signature validation"""
    # Create API key
    success, api_key, error = security_service.create_api_key("test_user")
    assert success
    
    # Get key data for signing
    key_data = security_service.redis.hgetall(security_service._get_api_key_key(api_key))
    secret = key_data[b'secret']
    
    # Create valid signature
    timestamp = datetime.utcnow().isoformat()
    method = "POST"
    path = "/api/v1/test"
    body = {"test": "data"}
    
    message = f"{method}:{path}:{timestamp}:{json.dumps(body, sort_keys=True)}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Validate signature
    is_valid, error = security_service.validate_request_signature(
        api_key=api_key,
        timestamp=timestamp,
        signature=signature,
        method=method,
        path=path,
        body=body
    )
    assert is_valid
    assert not error
    
    # Test invalid signature
    is_valid, error = security_service.validate_request_signature(
        api_key=api_key,
        timestamp=timestamp,
        signature="invalid_signature",
        method=method,
        path=path,
        body=body
    )
    assert not is_valid
    assert error == "Invalid signature"
    
    # Test expired timestamp
    old_timestamp = (datetime.utcnow() - timedelta(minutes=6)).isoformat()
    is_valid, error = security_service.validate_request_signature(
        api_key=api_key,
        timestamp=old_timestamp,
        signature=signature,
        method=method,
        path=path,
        body=body
    )
    assert not is_valid
    assert error == "Request timestamp expired"
    
    # Test replay attack
    is_valid, error = security_service.validate_request_signature(
        api_key=api_key,
        timestamp=timestamp,
        signature=signature,
        method=method,
        path=path,
        body=body
    )
    assert not is_valid
    assert error == "Signature already used"

def test_ip_blacklisting(security_service):
    """Test IP blacklisting"""
    ip = "192.168.1.1"
    
    # Check initial state
    assert not security_service.is_ip_blacklisted(ip)
    
    # Blacklist IP
    assert security_service.blacklist_ip(ip)
    assert security_service.is_ip_blacklisted(ip)
    
    # Test expiration
    assert security_service.blacklist_ip(ip, duration_minutes=1)
    time.sleep(61)  # Wait for blacklist to expire
    assert not security_service.is_ip_blacklisted(ip)
    
    # Test invalid IP
    assert not security_service.is_ip_blacklisted(None)
    assert not security_service.blacklist_ip(None)

def test_error_handling(security_service):
    """Test error handling"""
    # Test with invalid Redis client
    security_service.redis = None
    
    # API key validation
    is_valid, error = security_service.validate_api_key("test_key")
    assert not is_valid
    assert error == "Internal server error"
    
    # Request signature validation
    is_valid, error = security_service.validate_request_signature(
        api_key="test_key",
        timestamp=datetime.utcnow().isoformat(),
        signature="test_signature",
        method="GET",
        path="/test"
    )
    assert not is_valid
    assert error == "Internal server error"
    
    # IP blacklisting
    assert not security_service.blacklist_ip("192.168.1.1")
    assert not security_service.is_ip_blacklisted("192.168.1.1") 