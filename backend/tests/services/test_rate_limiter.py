import pytest
from datetime import datetime, timedelta
from app.services.rate_limiter import RateLimiter, RateLimitStrategy
from redis import Redis
import time

@pytest.fixture
def redis_client(mocker):
    mock_redis = mocker.Mock()
    mock_redis.get.return_value = None
    mock_redis.incr.return_value = 1
    mock_redis.pipeline.return_value = mock_redis
    mock_redis.keys.return_value = []
    return mock_redis

@pytest.fixture
def rate_limiter(redis_client):
    """Create a RateLimiter instance"""
    return RateLimiter(redis_client)

def test_fixed_window_strategy(rate_limiter):
    """Test fixed window rate limiting strategy"""
    user_id = "test_user"
    action = "test_action"
    
    # Should allow first request
    assert not rate_limiter.is_rate_limited(user_id, action)
    
    # Should allow requests up to limit
    for _ in range(9):  # 9 more requests (total 10)
        assert not rate_limiter.is_rate_limited(user_id, action)
    
    # Should block next request
    assert rate_limiter.is_rate_limited(user_id, action)
    
    # Should reset after window
    time.sleep(61)  # Wait for window to expire
    assert not rate_limiter.is_rate_limited(user_id, action)

def test_sliding_window_strategy(rate_limiter):
    """Test sliding window rate limiting strategy"""
    user_id = "test_user"
    action = "api_request"  # Uses sliding window strategy
    
    # Should allow first request
    assert not rate_limiter.is_rate_limited(user_id, action)
    
    # Should allow requests up to limit
    for _ in range(99):  # 99 more requests (total 100)
        assert not rate_limiter.is_rate_limited(user_id, action)
    
    # Should block next request
    assert rate_limiter.is_rate_limited(user_id, action)
    
    # Should allow new requests after window slides
    time.sleep(61)  # Wait for window to slide
    assert not rate_limiter.is_rate_limited(user_id, action)

def test_token_bucket_strategy(rate_limiter):
    """Test token bucket rate limiting strategy"""
    user_id = "test_user"
    action = "retry_attempt"  # Uses token bucket strategy
    
    # Should allow first request
    assert not rate_limiter.is_rate_limited(user_id, action)
    
    # Should allow requests up to limit
    for _ in range(2):  # 2 more requests (total 3)
        assert not rate_limiter.is_rate_limited(user_id, action)
    
    # Should block next request
    assert rate_limiter.is_rate_limited(user_id, action)
    
    # Should allow new request after tokens are refilled
    time.sleep(301)  # Wait for tokens to refill
    assert not rate_limiter.is_rate_limited(user_id, action)

def test_leaky_bucket_strategy(rate_limiter):
    """Test leaky bucket rate limiting strategy"""
    # Modify rate limiter to use leaky bucket for testing
    rate_limiter.default_limits['test_action'] = {
        'max_requests': 5,
        'window_seconds': 10,
        'strategy': RateLimitStrategy.LEAKY_BUCKET
    }
    
    user_id = "test_user"
    action = "test_action"
    
    # Should allow first request
    assert not rate_limiter.is_rate_limited(user_id, action)
    
    # Should allow requests up to limit
    for _ in range(4):  # 4 more requests (total 5)
        assert not rate_limiter.is_rate_limited(user_id, action)
    
    # Should block next request
    assert rate_limiter.is_rate_limited(user_id, action)
    
    # Should allow new request after bucket leaks
    time.sleep(11)  # Wait for bucket to leak
    assert not rate_limiter.is_rate_limited(user_id, action)

def test_remaining_requests(rate_limiter):
    """Test remaining requests calculation"""
    user_id = "test_user"
    action = "test_action"
    
    # Should start with max requests
    assert rate_limiter.get_remaining_requests(user_id, action) == 10
    
    # Should decrease with each request
    for i in range(5):
        rate_limiter.is_rate_limited(user_id, action)
        assert rate_limiter.get_remaining_requests(user_id, action) == 10 - (i + 1)
    
    # Should reset after window
    time.sleep(61)
    assert rate_limiter.get_remaining_requests(user_id, action) == 10

def test_reset_time(rate_limiter):
    """Test reset time calculation"""
    user_id = "test_user"
    action = "test_action"
    
    # Should return None before any requests
    assert rate_limiter.get_reset_time(user_id, action) is None
    
    # Should return future time after request
    rate_limiter.is_rate_limited(user_id, action)
    reset_time = rate_limiter.get_reset_time(user_id, action)
    assert reset_time is not None
    assert reset_time > datetime.utcnow()
    
    # Should reset after window
    time.sleep(61)
    assert rate_limiter.get_reset_time(user_id, action) is None

def test_error_handling(rate_limiter):
    """Test error handling in rate limiter"""
    user_id = "test_user"
    action = "test_action"
    
    # Should handle Redis errors gracefully
    rate_limiter.redis = None  # Simulate Redis connection error
    assert not rate_limiter.is_rate_limited(user_id, action)  # Should fail open
    assert rate_limiter.get_remaining_requests(user_id, action) is None
    assert rate_limiter.get_reset_time(user_id, action) is None

def test_rate_limiter_initialization(rate_limiter):
    assert rate_limiter.window_size == 60
    assert rate_limiter.max_requests == 100

def test_is_rate_limited_first_request(rate_limiter, redis_client):
    # First request should not be rate limited
    assert not rate_limiter.is_rate_limited("client1", "action1")
    
    # Verify Redis calls
    redis_client.get.assert_called_once()
    redis_client.pipeline.assert_called_once()
    redis_client.incr.assert_called_once()

def test_is_rate_limited_max_requests(rate_limiter, redis_client):
    # Set current count to max requests
    redis_client.get.return_value = 100
    
    # Request should be rate limited
    assert rate_limiter.is_rate_limited("client1", "action1")
    
    # Verify rate limit hit was recorded
    assert rate_limiter.rate_limit_hits._value.get() == 1

def test_is_rate_limited_custom_limit(rate_limiter, redis_client):
    # Set custom limit
    custom_limit = 5
    redis_client.get.return_value = 4
    
    # Request should not be rate limited
    assert not rate_limiter.is_rate_limited("client1", "action1", max_requests=custom_limit)
    
    # Set count to custom limit
    redis_client.get.return_value = 5
    
    # Request should be rate limited
    assert rate_limiter.is_rate_limited("client1", "action1", max_requests=custom_limit)

def test_get_remaining_requests(rate_limiter, redis_client):
    # Set current count
    redis_client.get.return_value = 75
    
    # Get remaining requests
    remaining = rate_limiter.get_remaining_requests("client1", "action1")
    
    assert remaining == 25

def test_get_remaining_requests_custom_limit(rate_limiter, redis_client):
    # Set current count
    redis_client.get.return_value = 3
    custom_limit = 5
    
    # Get remaining requests
    remaining = rate_limiter.get_remaining_requests("client1", "action1", max_requests=custom_limit)
    
    assert remaining == 2

def test_get_reset_time(rate_limiter):
    # Get reset time
    reset_time = rate_limiter.get_reset_time("client1", "action1")
    
    # Verify reset time is in the future
    assert reset_time > datetime.now()
    
    # Verify reset time is in the next window
    now = int(time.time())
    next_window = (now // 60 + 1) * 60
    assert reset_time.timestamp() == next_window

def test_reset_limits(rate_limiter, redis_client):
    # Set up keys to reset
    redis_client.keys.return_value = [
        b"rate:limit:client1:action1:1",
        b"rate:limit:client1:action2:1"
    ]
    
    # Reset limits for client1
    assert rate_limiter.reset_limits("client1")
    
    # Verify keys were deleted
    redis_client.delete.assert_called_once()
    
    # Verify active limits gauge was updated
    assert rate_limiter.active_limits._value.get() == -1

def test_reset_limits_specific_action(rate_limiter, redis_client):
    # Set up keys to reset
    redis_client.keys.return_value = [b"rate:limit:client1:action1:1"]
    
    # Reset limits for specific action
    assert rate_limiter.reset_limits("client1", "action1")
    
    # Verify only action1 keys were deleted
    redis_client.delete.assert_called_once()

def test_get_stats(rate_limiter, redis_client):
    # Set up keys for stats
    redis_client.keys.return_value = [
        b"rate:limit:client1:action1:1",
        b"rate:limit:client1:action2:1",
        b"rate:limit:client2:action1:1"
    ]
    
    # Get stats
    stats = rate_limiter.get_stats()
    
    assert stats["total_keys"] == 3
    assert stats["active_clients"] == 2
    assert stats["client_counts"]["client1"] == 2
    assert stats["client_counts"]["client2"] == 1

def test_error_handling(rate_limiter, redis_client):
    # Simulate Redis error
    redis_client.get.side_effect = Exception("Redis error")
    
    # Operations should handle errors gracefully
    assert not rate_limiter.is_rate_limited("client1", "action1")
    assert rate_limiter.get_remaining_requests("client1", "action1") is None
    assert rate_limiter.get_reset_time("client1", "action1") is None
    assert not rate_limiter.reset_limits("client1")
    assert rate_limiter.get_stats() == {
        "total_keys": 0,
        "active_clients": 0,
        "client_counts": {}
    } 