"""
Monitoring and metrics module.

This module provides functionality for monitoring application health,
collecting metrics, and tracking usage analytics.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import time
import psutil
import prometheus_client as prom
from prometheus_client import Counter, Histogram, Gauge
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)

# Define metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

ACTIVE_REQUESTS = Gauge(
    "http_requests_active",
    "Number of active HTTP requests",
    ["method", "endpoint"]
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total number of HTTP errors",
    ["method", "endpoint", "error_type"]
)

# System metrics
CPU_USAGE = Gauge(
    "system_cpu_usage_percent",
    "CPU usage percentage"
)

MEMORY_USAGE = Gauge(
    "system_memory_usage_bytes",
    "Memory usage in bytes"
)

DISK_USAGE = Gauge(
    "system_disk_usage_bytes",
    "Disk usage in bytes"
)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting HTTP metrics."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.start_time = time.time()

    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()
        
        # Increment active requests
        ACTIVE_REQUESTS.labels(
            method=request.method,
            endpoint=request.url.path
        ).inc()

        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).inc()
            
            return response
            
        except Exception as e:
            # Record error
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                error_type=type(e).__name__
            ).inc()
            raise
            
        finally:
            # Decrement active requests
            ACTIVE_REQUESTS.labels(
                method=request.method,
                endpoint=request.url.path
            ).dec()

class SystemMetrics:
    """System metrics collector."""
    
    @staticmethod
    def collect_metrics() -> Dict[str, Any]:
        """Collect system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            CPU_USAGE.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            MEMORY_USAGE.set(memory.used)
            
            # Disk usage
            disk = psutil.disk_usage("/")
            DISK_USAGE.set(disk.used)
            
            return {
                "cpu_usage": cpu_percent,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "disk_used": disk.used,
                "disk_total": disk.total,
                "uptime": time.time() - SystemMetrics.start_time
            }
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return {}

    @staticmethod
    def get_health_status() -> Dict[str, Any]:
        """Get system health status."""
        metrics = SystemMetrics.collect_metrics()
        
        # Define health thresholds
        thresholds = {
            "cpu_usage": 90,  # 90% CPU usage
            "memory_usage": 90,  # 90% memory usage
            "disk_usage": 90,  # 90% disk usage
        }
        
        # Check health status
        status = "healthy"
        checks = {
            "cpu": metrics.get("cpu_usage", 0) < thresholds["cpu_usage"],
            "memory": (metrics.get("memory_used", 0) / metrics.get("memory_total", 1)) * 100 < thresholds["memory_usage"],
            "disk": (metrics.get("disk_used", 0) / metrics.get("disk_total", 1)) * 100 < thresholds["disk_usage"]
        }
        
        if not all(checks.values()):
            status = "unhealthy"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
            "metrics": metrics
        }

class UsageAnalytics:
    """Usage analytics collector."""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_counts = {}
        self.error_counts = {}
        self.latency_sum = {}
        self.latency_count = {}
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record request metrics."""
        key = f"{method}:{endpoint}"
        
        # Update request counts
        self.request_counts[key] = self.request_counts.get(key, 0) + 1
        
        # Update latency metrics
        self.latency_sum[key] = self.latency_sum.get(key, 0) + duration
        self.latency_count[key] = self.latency_count.get(key, 0) + 1
        
        # Record errors
        if status >= 400:
            self.error_counts[key] = self.error_counts.get(key, 0) + 1
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get usage analytics."""
        analytics = {
            "uptime": time.time() - self.start_time,
            "total_requests": sum(self.request_counts.values()),
            "total_errors": sum(self.error_counts.values()),
            "endpoints": {}
        }
        
        # Calculate per-endpoint metrics
        for key in self.request_counts:
            method, endpoint = key.split(":")
            count = self.request_counts[key]
            errors = self.error_counts.get(key, 0)
            avg_latency = (
                self.latency_sum[key] / self.latency_count[key]
                if self.latency_count[key] > 0
                else 0
            )
            
            analytics["endpoints"][key] = {
                "method": method,
                "endpoint": endpoint,
                "requests": count,
                "errors": errors,
                "error_rate": errors / count if count > 0 else 0,
                "avg_latency": avg_latency
            }
        
        return analytics

# Initialize analytics
analytics = UsageAnalytics() 