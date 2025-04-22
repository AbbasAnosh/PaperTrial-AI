import pytest
from app.services.cache_service import CacheService, CircuitBreaker
from redis import Redis, ConnectionPool
import time
import json
import asyncio
from unittest.mock import Mock, patch
from prometheus_client import REGISTRY
import pickle
import zlib
from typing import Dict, Any, List

@pytest.fixture
def redis_client():
    """Create a Redis client for testing"""
    client = Redis(host='localhost', port=6379, db=1)  # Use DB 1 for testing
    yield client
    client.flushdb()  # Clean up after tests
    client.close()

@pytest.fixture
def cache_service(redis_client):
    """Create a CacheService instance"""
    return CacheService(redis_client, pool_size=5)

@pytest.fixture
def mock_redis_client(mocker):
    """Create a mock Redis client for testing error cases"""
    mock_client = mocker.Mock(spec=Redis)
    mock_client.get.side_effect = Exception("Redis connection error")
    return mock_client

@pytest.fixture
def large_data():
    """Create large test data"""
    return {
        "string": "x" * 10000,  # 10KB string
        "list": [{"id": i, "data": "x" * 100} for i in range(100)],  # Large list
        "dict": {f"key{i}": f"value{i}" * 10 for i in range(100)},  # Large dict
        "binary": b"x" * 10000,  # Binary data
    }

def test_set_get(cache_service):
    """Test basic set and get operations"""
    # Test string
    cache_service.set("test_key", "test_value")
    assert cache_service.get("test_key") == "test_value"
    
    # Test dict
    test_dict = {"key": "value"}
    cache_service.set("test_dict", test_dict)
    assert cache_service.get("test_dict") == test_dict
    
    # Test list
    test_list = [1, 2, 3]
    cache_service.set("test_list", test_list)
    assert cache_service.get("test_list") == test_list
    
    # Test non-existent key
    assert cache_service.get("non_existent") is None
    assert cache_service.get("non_existent", "default") == "default"

def test_ttl(cache_service):
    """Test TTL functionality"""
    # Set with 1 second TTL
    cache_service.set("ttl_key", "value", ttl=1)
    assert cache_service.get("ttl_key") == "value"
    
    # Wait for TTL to expire
    time.sleep(1.1)
    assert cache_service.get("ttl_key") is None

def test_delete(cache_service):
    """Test delete operation"""
    cache_service.set("delete_key", "value")
    assert cache_service.get("delete_key") == "value"
    
    cache_service.delete("delete_key")
    assert cache_service.get("delete_key") is None

def test_clear_pattern(cache_service):
    """Test clearing keys by pattern"""
    # Set multiple keys
    cache_service.set("pattern:1", "value1")
    cache_service.set("pattern:2", "value2")
    cache_service.set("other:1", "value3")
    
    # Clear pattern keys
    cache_service.clear_pattern("pattern:*")
    
    assert cache_service.get("pattern:1") is None
    assert cache_service.get("pattern:2") is None
    assert cache_service.get("other:1") == "value3"

def test_get_or_set(cache_service):
    """Test get_or_set functionality"""
    def callback():
        return "callback_value"
    
    # First call should use callback
    value = cache_service.get_or_set("get_or_set_key", callback)
    assert value == "callback_value"
    
    # Second call should use cached value
    value = cache_service.get_or_set("get_or_set_key", callback)
    assert value == "callback_value"

@pytest.mark.asyncio
async def test_cache_response_decorator(cache_service):
    """Test cache_response decorator"""
    call_count = 0
    
    @cache_service.cache_response("test_prefix")
    async def test_function(arg1, arg2):
        nonlocal call_count
        call_count += 1
        return {"arg1": arg1, "arg2": arg2}
    
    # First call
    result1 = await test_function(1, 2)
    assert result1 == {"arg1": 1, "arg2": 2}
    assert call_count == 1
    
    # Second call with same arguments
    result2 = await test_function(1, 2)
    assert result2 == {"arg1": 1, "arg2": 2}
    assert call_count == 1  # Should use cached value
    
    # Call with different arguments
    result3 = await test_function(3, 4)
    assert result3 == {"arg1": 3, "arg2": 4}
    assert call_count == 2

def test_invalidate(cache_service):
    """Test cache invalidation"""
    cache_service.set("invalidate_key", "value")
    assert cache_service.get("invalidate_key") == "value"
    
    cache_service.invalidate("invalidate_key")
    assert cache_service.get("invalidate_key") is None

def test_invalidate_pattern(cache_service):
    """Test pattern-based cache invalidation"""
    cache_service.set("pattern:1", "value1")
    cache_service.set("pattern:2", "value2")
    cache_service.set("other:1", "value3")
    
    cache_service.invalidate_pattern("pattern:*")
    
    assert cache_service.get("pattern:1") is None
    assert cache_service.get("pattern:2") is None
    assert cache_service.get("other:1") == "value3"

def test_compression(cache_service):
    """Test data compression for large values"""
    # Create a large string
    large_data = "x" * 2000  # 2KB
    
    # Set with compression
    cache_service.set("compressed_key", large_data)
    
    # Get and verify
    retrieved = cache_service.get("compressed_key")
    assert retrieved == large_data

def test_connection_pool(cache_service):
    """Test connection pool setup and management"""
    assert isinstance(cache_service.redis.connection_pool, ConnectionPool)
    assert cache_service.redis.connection_pool.max_connections == 5
    
    # Test pool size metric
    pool_size = REGISTRY.get_sample_value('cache_connection_pool_size')
    assert pool_size == 5

def test_circuit_breaker(cache_service):
    """Test circuit breaker functionality"""
    # Test initial state
    assert cache_service._circuit_breaker.state == "closed"
    assert cache_service._circuit_breaker.can_execute() is True
    
    # Test failure threshold
    for _ in range(5):  # Default threshold is 5
        cache_service._circuit_breaker.record_failure()
    
    assert cache_service._circuit_breaker.state == "open"
    assert cache_service._circuit_breaker.can_execute() is False
    
    # Test reset timeout
    cache_service._circuit_breaker.last_failure_time = time.time() - 61  # Default timeout is 60s
    assert cache_service._circuit_breaker.can_execute() is True
    assert cache_service._circuit_breaker.state == "half-open"
    
    # Test successful recovery
    cache_service._circuit_breaker.record_success()
    assert cache_service._circuit_breaker.state == "closed"
    assert cache_service._circuit_breaker.failures == 0

def test_batch_operations(cache_service):
    """Test batch get and set operations"""
    # Test mset
    test_data = {
        "batch_key1": "value1",
        "batch_key2": "value2",
        "batch_key3": {"nested": "value"}
    }
    assert cache_service.mset(test_data) is True
    
    # Test mget
    keys = ["batch_key1", "batch_key2", "batch_key3", "non_existent"]
    results = cache_service.mget(keys)
    
    assert results[0] == "value1"
    assert results[1] == "value2"
    assert results[2] == {"nested": "value"}
    assert results[3] is None
    
    # Test mget with default value
    results = cache_service.mget(keys, default="default")
    assert results[3] == "default"

def test_metrics_collection(cache_service):
    """Test metrics collection"""
    # Perform some operations
    cache_service.set("metric_key", "value")
    cache_service.get("metric_key")  # Hit
    cache_service.get("non_existent")  # Miss
    cache_service.get("metric_key")  # Hit
    
    # Get stats
    stats = cache_service.get_stats()
    
    # Verify metrics
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert "hit_rate" in stats
    assert 0.6 <= stats["hit_rate"] <= 0.7  # 2 hits out of 3 requests
    assert "used_memory" in stats
    assert "connection_pool_size" in stats
    assert "circuit_breaker_state" in stats

def test_retry_mechanism(cache_service, mock_redis_client):
    """Test retry mechanism"""
    cache_service.redis = mock_redis_client
    
    # Test with retry
    with pytest.raises(Exception):
        cache_service.get("test_key")
    
    # Verify retry attempts
    assert mock_redis_client.get.call_count == 3  # Default max attempts

def test_compression_threshold(cache_service):
    """Test compression for large values"""
    # Test with various data sizes
    small_data = "small" * 100  # Should not be compressed
    large_data = "large" * 1000  # Should be compressed
    
    cache_service.set("small_key", small_data)
    cache_service.set("large_key", large_data)
    
    # Verify compression
    small_value = cache_service.redis.get("small_key")
    large_value = cache_service.redis.get("large_key")
    
    assert not small_value.startswith(b'compressed:')
    assert large_value.startswith(b'compressed:')
    
    # Verify retrieval
    assert cache_service.get("small_key") == small_data
    assert cache_service.get("large_key") == large_data

@pytest.mark.asyncio
async def test_concurrent_access(cache_service):
    """Test concurrent access to cache"""
    async def set_value(key: str, value: str):
        cache_service.set(key, value)
        return cache_service.get(key)
    
    # Test concurrent sets
    tasks = [
        set_value(f"concurrent_key_{i}", f"value_{i}")
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)
    
    # Verify all values were set correctly
    for i, result in enumerate(results):
        assert result == f"value_{i}"
        assert cache_service.get(f"concurrent_key_{i}") == f"value_{i}"

def test_error_handling(cache_service, mock_redis_client):
    """Test error handling"""
    cache_service.redis = mock_redis_client
    
    # Test with circuit breaker
    assert cache_service.get("key") is None
    assert cache_service._circuit_breaker.failures > 0
    
    # Test with invalid Redis client
    cache_service.redis = None
    assert cache_service.set("key", "value") is False
    assert cache_service.get("key") is None
    assert cache_service.delete("key") is False
    assert cache_service.clear_pattern("pattern:*") is False

def test_cache_response_decorator_with_circuit_breaker(cache_service):
    """Test cache_response decorator with circuit breaker"""
    call_count = 0
    
    @cache_service.cache_response("test_prefix")
    async def test_function():
        nonlocal call_count
        call_count += 1
        return "value"
    
    # Test normal operation
    asyncio.run(test_function())
    assert call_count == 1
    
    # Test with circuit breaker open
    cache_service._circuit_breaker.state = "open"
    asyncio.run(test_function())
    assert call_count == 2  # Should bypass cache and call function

def test_metrics_in_error_cases(cache_service, mock_redis_client):
    """Test metrics collection in error cases"""
    cache_service.redis = mock_redis_client
    
    # Perform operations that will fail
    cache_service.get("key")
    cache_service.set("key", "value")
    
    # Verify error metrics
    stats = cache_service.get_stats()
    assert stats["errors"] > 0

def test_connection_pool_exhaustion(cache_service):
    """Test behavior when connection pool is exhausted"""
    # Create more connections than pool size
    connections = []
    for i in range(10):  # Pool size is 5
        conn = Redis(connection_pool=cache_service.redis.connection_pool)
        connections.append(conn)
    
    # Verify pool size metric
    pool_size = REGISTRY.get_sample_value('cache_connection_pool_size')
    assert pool_size == 5
    
    # Clean up
    for conn in connections:
        conn.close()

def test_batch_operations_with_circuit_breaker(cache_service):
    """Test batch operations with circuit breaker"""
    # Test mget with circuit breaker open
    cache_service._circuit_breaker.state = "open"
    results = cache_service.mget(["key1", "key2"], default="default")
    assert results == ["default", "default"]
    
    # Test mset with circuit breaker open
    assert cache_service.mset({"key1": "value1"}) is False
    
    # Reset circuit breaker
    cache_service._circuit_breaker.state = "closed"
    
    # Test normal operation
    assert cache_service.mset({"key1": "value1"}) is True
    results = cache_service.mget(["key1"])
    assert results[0] == "value1"

def test_stats(cache_service):
    """Test cache statistics"""
    # Set some test data
    cache_service.set("stats_key1", "value1")
    cache_service.set("stats_key2", "value2")
    
    # Get stats
    stats = cache_service.get_stats()
    
    # Verify stats structure
    assert "used_memory" in stats
    assert "used_memory_peak" in stats
    assert "total_keys" in stats
    assert "hits" in stats
    assert "misses" in stats
    assert "hit_rate" in stats
    
    # Test with invalid Redis
    cache_service.redis = None
    stats = cache_service.get_stats()
    assert "error" in stats

def test_serialization_edge_cases(cache_service):
    """Test serialization of edge cases"""
    # Test with None
    cache_service.set("none_key", None)
    assert cache_service.get("none_key") is None
    
    # Test with boolean values
    cache_service.set("bool_true", True)
    cache_service.set("bool_false", False)
    assert cache_service.get("bool_true") is True
    assert cache_service.get("bool_false") is False
    
    # Test with numeric edge cases
    cache_service.set("int_max", 2**63 - 1)
    cache_service.set("int_min", -2**63)
    cache_service.set("float_inf", float('inf'))
    cache_service.set("float_nan", float('nan'))
    
    assert cache_service.get("int_max") == 2**63 - 1
    assert cache_service.get("int_min") == -2**63
    assert cache_service.get("float_inf") == float('inf')
    assert cache_service.get("float_nan") == float('nan')

def test_complex_data_structures(cache_service):
    """Test caching of complex data structures"""
    # Test with nested structures
    nested_data = {
        "list": [{"key": "value"}, {"key": "value2"}],
        "dict": {"nested": {"key": "value"}},
        "mixed": [1, "string", {"key": "value"}, [1, 2, 3]]
    }
    
    cache_service.set("nested_key", nested_data)
    retrieved = cache_service.get("nested_key")
    assert retrieved == nested_data
    
    # Test with custom objects
    class CustomObject:
        def __init__(self, value):
            self.value = value
            
        def __eq__(self, other):
            return isinstance(other, CustomObject) and self.value == other.value
    
    custom_obj = CustomObject("test")
    cache_service.set("custom_key", custom_obj)
    retrieved = cache_service.get("custom_key")
    assert retrieved == custom_obj

def test_compression_performance(cache_service, large_data):
    """Test compression performance with large data"""
    # Test compression ratio
    for key, value in large_data.items():
        cache_service.set(f"large_{key}", value)
        raw_size = len(pickle.dumps(value))
        compressed_size = len(cache_service.redis.get(f"large_{key}"))
        assert compressed_size < raw_size
        
        # Verify data integrity
        retrieved = cache_service.get(f"large_{key}")
        assert retrieved == value

def test_concurrent_batch_operations(cache_service):
    """Test concurrent batch operations"""
    async def batch_operation(batch_id: int):
        keys = [f"batch_{batch_id}_{i}" for i in range(10)]
        values = {k: f"value_{i}" for i, k in enumerate(keys)}
        
        # Set values
        cache_service.mset(values)
        
        # Get values
        results = cache_service.mget(keys)
        return results
    
    # Run multiple batch operations concurrently
    async def run_concurrent_batches():
        tasks = [batch_operation(i) for i in range(5)]
        return await asyncio.gather(*tasks)
    
    results = asyncio.run(run_concurrent_batches())
    
    # Verify all operations completed successfully
    for batch_id, batch_results in enumerate(results):
        for i, value in enumerate(batch_results):
            assert value == f"value_{i}"

def test_circuit_breaker_recovery_patterns(cache_service, mock_redis_client):
    """Test various circuit breaker recovery patterns"""
    cache_service.redis = mock_redis_client
    
    # Test rapid failures
    for _ in range(10):
        with pytest.raises(Exception):
            cache_service.get("key")
    
    assert cache_service._circuit_breaker.state == "open"
    
    # Test gradual recovery
    cache_service._circuit_breaker.last_failure_time = time.time() - 61
    assert cache_service._circuit_breaker.state == "half-open"
    
    # Test successful recovery
    mock_redis_client.get.side_effect = "value"
    cache_service.get("key")
    assert cache_service._circuit_breaker.state == "closed"
    
    # Test partial recovery
    mock_redis_client.get.side_effect = Exception("Redis error")
    cache_service._circuit_breaker.failures = 3
    cache_service.get("key")
    assert cache_service._circuit_breaker.state == "open"

def test_metrics_accuracy(cache_service):
    """Test accuracy of collected metrics"""
    # Perform operations with known outcomes
    operations = [
        ("hit1", "value1", True),  # (key, value, should_hit)
        ("hit2", "value2", True),
        ("miss1", None, False),
        ("hit3", "value3", True),
        ("error1", None, False)
    ]
    
    for key, value, should_hit in operations:
        if value is not None:
            cache_service.set(key, value)
        try:
            cache_service.get(key)
        except:
            pass
    
    stats = cache_service.get_stats()
    
    # Verify metrics
    assert stats["hits"] == 3  # hit1, hit2, hit3
    assert stats["misses"] == 1  # miss1
    assert stats["errors"] == 1  # error1
    assert 0.6 <= stats["hit_rate"] <= 0.7  # 3 hits out of 5 operations

def test_connection_pool_stress(cache_service):
    """Test connection pool under stress"""
    async def stress_operation(operation_id: int):
        key = f"stress_key_{operation_id}"
        value = f"value_{operation_id}"
        
        # Perform multiple operations
        for _ in range(5):
            cache_service.set(key, value)
            assert cache_service.get(key) == value
            cache_service.delete(key)
    
    # Run multiple stress operations concurrently
    async def run_stress_test():
        tasks = [stress_operation(i) for i in range(20)]
        return await asyncio.gather(*tasks)
    
    asyncio.run(run_stress_test())
    
    # Verify pool metrics
    stats = cache_service.get_stats()
    assert stats["connection_pool_size"] == 5

def test_cache_invalidation_patterns(cache_service):
    """Test various cache invalidation patterns"""
    # Set up test data
    patterns = {
        "user:*": ["user:1", "user:2", "user:3"],
        "session:*": ["session:1", "session:2"],
        "temp:*": ["temp:1"]
    }
    
    # Set values
    for keys in patterns.values():
        for key in keys:
            cache_service.set(key, f"value_{key}")
    
    # Test pattern-based invalidation
    for pattern, keys in patterns.items():
        cache_service.invalidate_pattern(pattern)
        for key in keys:
            assert cache_service.get(key) is None
    
    # Test selective invalidation
    cache_service.set("user:1", "value1")
    cache_service.set("user:2", "value2")
    cache_service.invalidate("user:1")
    assert cache_service.get("user:1") is None
    assert cache_service.get("user:2") == "value2"

def test_ttl_behavior(cache_service):
    """Test TTL behavior in various scenarios"""
    # Test immediate expiration
    cache_service.set("immediate", "value", ttl=0)
    assert cache_service.get("immediate") is None
    
    # Test short TTL
    cache_service.set("short", "value", ttl=1)
    assert cache_service.get("short") == "value"
    time.sleep(1.1)
    assert cache_service.get("short") is None
    
    # Test TTL update
    cache_service.set("update", "value", ttl=2)
    time.sleep(1)
    cache_service.set("update", "new_value", ttl=2)
    time.sleep(1.1)
    assert cache_service.get("update") == "new_value"
    
    # Test TTL with batch operations
    cache_service.mset({"batch1": "value1", "batch2": "value2"}, ttl=1)
    assert cache_service.get("batch1") == "value1"
    time.sleep(1.1)
    assert cache_service.get("batch1") is None

def test_error_recovery_patterns(cache_service, mock_redis_client):
    """Test various error recovery patterns"""
    cache_service.redis = mock_redis_client
    
    # Test retry with success
    mock_redis_client.get.side_effect = [
        Exception("Error 1"),
        Exception("Error 2"),
        "success"
    ]
    assert cache_service.get("key") == "success"
    
    # Test retry with failure
    mock_redis_client.get.side_effect = Exception("Persistent error")
    with pytest.raises(Exception):
        cache_service.get("key")
    
    # Test circuit breaker integration
    assert cache_service._circuit_breaker.state == "open"
    
    # Test recovery after timeout
    cache_service._circuit_breaker.last_failure_time = time.time() - 61
    assert cache_service._circuit_breaker.state == "half-open"

@pytest.mark.asyncio
async def test_cache_warming(cache_service):
    """Test cache warming functionality"""
    # Define warmup items
    warmup_items = [
        {
            "key": "warm_key1",
            "callback": lambda: "value1",
            "ttl": 60
        },
        {
            "key": "warm_key2",
            "callback": lambda: {"data": "value2"},
            "ttl": 120
        }
    ]
    
    # Start warmup process
    await cache_service.warm_cache(warmup_items)
    
    # Wait for warmup to complete
    await asyncio.sleep(1)
    
    # Verify warmed items
    assert cache_service.get("warm_key1") == "value1"
    assert cache_service.get("warm_key2") == {"data": "value2"}
    
    # Verify warmup stats
    stats = cache_service.get_warmup_stats()
    assert stats["is_running"] is True
    assert stats["items_warmed"] == 2
    
    # Stop warmup process
    await cache_service.warmup.stop()
    assert cache_service.warmup.is_running is False

@pytest.mark.asyncio
async def test_cache_warming_error_handling(cache_service):
    """Test cache warming error handling"""
    # Define warmup items with error
    def failing_callback():
        raise Exception("Warmup error")
        
    warmup_items = [
        {
            "key": "error_key",
            "callback": failing_callback,
            "ttl": 60
        }
    ]
    
    # Start warmup process
    await cache_service.warm_cache(warmup_items)
    
    # Wait for warmup to complete
    await asyncio.sleep(1)
    
    # Verify error handling
    assert cache_service.get("error_key") is None
    stats = cache_service.get_warmup_stats()
    assert stats["items_warmed"] == 0

def test_cache_synchronization(cache_service):
    """Test cache synchronization"""
    # Start sync process
    cache_service.start_sync()
    
    # Verify sync is running
    stats = cache_service.get_sync_stats()
    assert stats["is_running"] is True
    
    # Stop sync process
    cache_service.stop_sync()
    assert cache_service.sync.sync_thread is None

def test_cache_sync_error_handling(cache_service):
    """Test cache sync error handling"""
    # Mock sync method to raise error
    def mock_sync():
        raise Exception("Sync error")
        
    cache_service.sync._sync_cache = mock_sync
    
    # Start sync process
    cache_service.start_sync()
    
    # Wait for sync attempt
    time.sleep(1)
    
    # Verify error handling
    stats = cache_service.get_sync_stats()
    assert stats["sync_operations"] == 0

@pytest.mark.asyncio
async def test_concurrent_warmup_and_sync(cache_service):
    """Test concurrent warmup and sync operations"""
    # Start both processes
    await cache_service.warm_cache([
        {"key": "concurrent_key", "callback": lambda: "value", "ttl": 60}
    ])
    cache_service.start_sync()
    
    # Wait for operations
    await asyncio.sleep(1)
    
    # Verify both processes
    assert cache_service.get("concurrent_key") == "value"
    assert cache_service.warmup.is_running is True
    assert cache_service.sync.sync_thread is not None
    
    # Cleanup
    await cache_service.warmup.stop()
    cache_service.stop_sync()

def test_graceful_shutdown(cache_service):
    """Test graceful shutdown handling"""
    # Start processes
    asyncio.run(cache_service.warm_cache([
        {"key": "shutdown_key", "callback": lambda: "value", "ttl": 60}
    ]))
    cache_service.start_sync()
    
    # Simulate shutdown signal
    cache_service._handle_shutdown(None, None)
    
    # Verify cleanup
    assert cache_service.warmup.is_running is False
    assert cache_service.sync.sync_thread is None

def test_warmup_queue_management(cache_service):
    """Test warmup queue management"""
    async def test_queue():
        # Add items to queue
        await cache_service.warmup.add_to_warmup("queue_key1", lambda: "value1")
        await cache_service.warmup.add_to_warmup("queue_key2", lambda: "value2")
        
        # Verify queue size
        assert cache_service.warmup.warmup_queue.qsize() == 2
        
        # Start processing
        await cache_service.warmup.start()
        await asyncio.sleep(1)
        
        # Verify queue is empty
        assert cache_service.warmup.warmup_queue.qsize() == 0
        
        # Stop warmup
        await cache_service.warmup.stop()
        
    asyncio.run(test_queue())

def test_sync_interval_configuration(cache_service):
    """Test sync interval configuration"""
    # Set custom sync interval
    cache_service.sync.sync_interval = 0.1  # 100ms for testing
    
    # Start sync
    cache_service.start_sync()
    time.sleep(0.3)  # Wait for multiple sync attempts
    
    # Verify sync operations
    stats = cache_service.get_sync_stats()
    assert stats["sync_operations"] >= 2
    
    # Cleanup
    cache_service.stop_sync()

@pytest.mark.asyncio
async def test_warmup_with_large_data(cache_service, large_data):
    """Test warmup with large data"""
    # Add large items to warmup queue
    for key, value in large_data.items():
        await cache_service.warmup.add_to_warmup(
            f"large_{key}",
            lambda v=value: v
        )
    
    # Start warmup
    await cache_service.warmup.start()
    await asyncio.sleep(1)
    
    # Verify warmed items
    for key, value in large_data.items():
        assert cache_service.get(f"large_{key}") == value
    
    # Cleanup
    await cache_service.warmup.stop()

def test_cache_versioning(cache_service):
    """Test cache versioning functionality"""
    # Set initial value
    cache_service.set("version_key", "value1")
    initial_version = cache_service.version.get_version()
    
    # Get value with versioning
    assert cache_service.get("version_key") == "value1"
    
    # Increment version
    new_version = cache_service.increment_version()
    assert new_version != initial_version
    
    # Old value should be invalid
    assert cache_service.get("version_key") is None
    
    # Set new value
    cache_service.set("version_key", "value2")
    assert cache_service.get("version_key") == "value2"
    
    # Verify version metrics
    stats = cache_service.get_stats()
    assert stats["version_changes"] == 1

def test_cache_tags(cache_service):
    """Test cache tagging functionality"""
    # Set value with tags
    cache_service.set("tag_key", "value", tags=["tag1", "tag2"])
    
    # Verify tags
    keys = cache_service.tags.get_keys_by_tag("tag1")
    assert len(keys) == 1
    assert cache_service.get("tag_key") == "value"
    
    # Remove tag
    cache_service.tags.remove_tags("tag_key", ["tag1"])
    keys = cache_service.tags.get_keys_by_tag("tag1")
    assert len(keys) == 0
    
    # Invalidate by tag
    cache_service.invalidate_by_tag("tag2")
    assert cache_service.get("tag_key") is None
    
    # Verify tag metrics
    stats = cache_service.get_stats()
    assert stats["tag_operations"] > 0

@pytest.mark.asyncio
async def test_distributed_sync(cache_service):
    """Test distributed synchronization"""
    # Create second cache service instance
    cache_service2 = CacheService(cache_service.redis, instance_id="test_instance_2")
    
    # Start sync on both instances
    cache_service.start_distributed_sync()
    cache_service2.start_distributed_sync()
    
    # Set value on first instance
    cache_service.set("sync_key", "value1")
    
    # Wait for sync
    await asyncio.sleep(0.5)
    
    # Verify value on second instance
    assert cache_service2.get("sync_key") == "value1"
    
    # Delete value on first instance
    cache_service.delete("sync_key")
    
    # Wait for sync
    await asyncio.sleep(0.5)
    
    # Verify deletion on second instance
    assert cache_service2.get("sync_key") is None
    
    # Cleanup
    cache_service.stop_distributed_sync()
    cache_service2.stop_distributed_sync()

def test_versioned_key_pattern(cache_service):
    """Test versioned key pattern handling"""
    # Set values with different patterns
    cache_service.set("pattern:1", "value1")
    cache_service.set("pattern:2", "value2")
    initial_version = cache_service.version.get_version()
    
    # Verify pattern-based operations
    assert cache_service.get("pattern:1") == "value1"
    assert cache_service.get("pattern:2") == "value2"
    
    # Increment version
    cache_service.increment_version()
    
    # Old pattern values should be invalid
    assert cache_service.get("pattern:1") is None
    assert cache_service.get("pattern:2") is None
    
    # Set new values
    cache_service.set("pattern:1", "new_value1")
    cache_service.set("pattern:2", "new_value2")
    
    # Verify new values
    assert cache_service.get("pattern:1") == "new_value1"
    assert cache_service.get("pattern:2") == "new_value2"

def test_tag_based_invalidation(cache_service):
    """Test tag-based cache invalidation"""
    # Set values with multiple tags
    cache_service.set("key1", "value1", tags=["tag1", "common"])
    cache_service.set("key2", "value2", tags=["tag2", "common"])
    
    # Verify initial values
    assert cache_service.get("key1") == "value1"
    assert cache_service.get("key2") == "value2"
    
    # Invalidate by specific tag
    cache_service.invalidate_by_tag("tag1")
    assert cache_service.get("key1") is None
    assert cache_service.get("key2") == "value2"
    
    # Invalidate by common tag
    cache_service.invalidate_by_tag("common")
    assert cache_service.get("key1") is None
    assert cache_service.get("key2") is None

@pytest.mark.asyncio
async def test_concurrent_distributed_sync(cache_service):
    """Test concurrent distributed sync operations"""
    # Create multiple cache service instances
    instances = [
        CacheService(cache_service.redis, instance_id=f"test_instance_{i}")
        for i in range(3)
    ]
    
    # Start sync on all instances
    for instance in instances:
        instance.start_distributed_sync()
    
    # Perform concurrent operations
    async def perform_operations(instance_id: int):
        instance = instances[instance_id]
        for i in range(10):
            key = f"concurrent_key_{instance_id}_{i}"
            value = f"value_{instance_id}_{i}"
            instance.set(key, value)
            await asyncio.sleep(0.1)
    
    # Run concurrent operations
    tasks = [perform_operations(i) for i in range(3)]
    await asyncio.gather(*tasks)
    
    # Wait for sync
    await asyncio.sleep(1)
    
    # Verify values on all instances
    for instance in instances:
        for i in range(3):
            for j in range(10):
                key = f"concurrent_key_{i}_{j}"
                value = f"value_{i}_{j}"
                assert instance.get(key) == value
    
    # Cleanup
    for instance in instances:
        instance.stop_distributed_sync()

def test_version_metrics(cache_service):
    """Test version change metrics"""
    # Initial stats
    initial_stats = cache_service.get_stats()
    initial_version_changes = initial_stats["version_changes"]
    
    # Perform version changes
    for _ in range(3):
        cache_service.increment_version()
    
    # Verify metrics
    stats = cache_service.get_stats()
    assert stats["version_changes"] == initial_version_changes + 3

def test_tag_metrics(cache_service):
    """Test tag operation metrics"""
    # Initial stats
    initial_stats = cache_service.get_stats()
    initial_tag_ops = initial_stats["tag_operations"]
    
    # Perform tag operations
    cache_service.set("metric_key", "value", tags=["tag1"])
    cache_service.invalidate_by_tag("tag1")
    
    # Verify metrics
    stats = cache_service.get_stats()
    assert stats["tag_operations"] == initial_tag_ops + 2

@pytest.mark.asyncio
async def test_distributed_sync_recovery(cache_service):
    """Test distributed sync recovery after failure"""
    # Create second instance
    cache_service2 = CacheService(cache_service.redis, instance_id="test_instance_2")
    
    # Start sync
    cache_service.start_distributed_sync()
    cache_service2.start_distributed_sync()
    
    # Set initial value
    cache_service.set("recovery_key", "value1")
    await asyncio.sleep(0.5)
    assert cache_service2.get("recovery_key") == "value1"
    
    # Simulate failure and recovery
    cache_service2.stop_distributed_sync()
    cache_service.set("recovery_key", "value2")
    await asyncio.sleep(0.5)
    
    # Restart sync
    cache_service2.start_distributed_sync()
    await asyncio.sleep(0.5)
    
    # Verify sync recovery
    assert cache_service2.get("recovery_key") == "value2"
    
    # Cleanup
    cache_service.stop_distributed_sync()
    cache_service2.stop_distributed_sync() 