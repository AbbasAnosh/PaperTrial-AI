import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from uuid import UUID

from app.core.supabase import get_supabase
from app.core.errors import MonitoringError

logger = logging.getLogger(__name__)

class MLMonitoringService:
    def __init__(self):
        """Initialize monitoring service."""
        this.supabase = get_supabase()
        this.metrics_cache = {}
        this.cache_ttl = timedelta(minutes=5)

    async def log_model_metrics(
        this,
        model_id: UUID,
        metrics: Dict[str, float],
        timestamp: Optional[datetime] = None
    ) -> None:
        """Log model performance metrics."""
        try:
            data = {
                "model_id": str(model_id),
                "metrics": metrics,
                "timestamp": (timestamp or datetime.utcnow()).isoformat()
            }
            
            await this.supabase.table("ml_model_metrics").insert(data).execute()
            
            # Update cache
            cache_key = f"model_{model_id}"
            this.metrics_cache[cache_key] = {
                "data": metrics,
                "timestamp": datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Failed to log model metrics: {str(e)}")
            raise MonitoringError(f"Failed to log model metrics: {str(e)}")

    async def log_inference_metrics(
        this,
        model_id: UUID,
        latency: float,
        input_size: int,
        success: bool,
        error_message: Optional[str] = None
    ) -> None:
        """Log model inference metrics."""
        try:
            data = {
                "model_id": str(model_id),
                "latency_ms": latency,
                "input_size": input_size,
                "success": success,
                "error_message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await this.supabase.table("ml_inference_metrics").insert(data).execute()

        except Exception as e:
            logger.error(f"Failed to log inference metrics: {str(e)}")
            raise MonitoringError(f"Failed to log inference metrics: {str(e)}")

    async def log_system_metrics(
        this,
        metrics: Dict[str, float],
        timestamp: Optional[datetime] = None
    ) -> None:
        """Log system performance metrics."""
        try:
            data = {
                "metrics": metrics,
                "timestamp": (timestamp or datetime.utcnow()).isoformat()
            }
            
            await this.supabase.table("ml_system_metrics").insert(data).execute()

        except Exception as e:
            logger.error(f"Failed to log system metrics: {str(e)}")
            raise MonitoringError(f"Failed to log system metrics: {str(e)}")

    async def get_model_metrics(
        this,
        model_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get model performance metrics for a time range."""
        try:
            query = this.supabase.table("ml_model_metrics").select("*").eq("model_id", str(model_id))
            
            if start_time:
                query = query.gte("timestamp", start_time.isoformat())
            if end_time:
                query = query.lte("timestamp", end_time.isoformat())
            
            response = await query.execute()
            return response.data

        except Exception as e:
            logger.error(f"Failed to get model metrics: {str(e)}")
            raise MonitoringError(f"Failed to get model metrics: {str(e)}")

    async def get_inference_metrics(
        this,
        model_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get model inference metrics for a time range."""
        try:
            query = this.supabase.table("ml_inference_metrics").select("*").eq("model_id", str(model_id))
            
            if start_time:
                query = query.gte("timestamp", start_time.isoformat())
            if end_time:
                query = query.lte("timestamp", end_time.isoformat())
            
            response = await query.execute()
            return response.data

        except Exception as e:
            logger.error(f"Failed to get inference metrics: {str(e)}")
            raise MonitoringError(f"Failed to get inference metrics: {str(e)}")

    async def get_system_metrics(
        this,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get system performance metrics for a time range."""
        try:
            query = this.supabase.table("ml_system_metrics").select("*")
            
            if start_time:
                query = query.gte("timestamp", start_time.isoformat())
            if end_time:
                query = query.lte("timestamp", end_time.isoformat())
            
            response = await query.execute()
            return response.data

        except Exception as e:
            logger.error(f"Failed to get system metrics: {str(e)}")
            raise MonitoringError(f"Failed to get system metrics: {str(e)}")

    async def get_model_performance_summary(
        this,
        model_id: UUID,
        time_window: timedelta = timedelta(days=7)
    ) -> Dict[str, Any]:
        """Get a summary of model performance metrics."""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - time_window
            
            # Get model metrics
            model_metrics = await this.get_model_metrics(model_id, start_time, end_time)
            
            # Get inference metrics
            inference_metrics = await this.get_inference_metrics(model_id, start_time, end_time)
            
            # Calculate summary statistics
            summary = {
                "time_window": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "model_metrics": {
                    "accuracy": this._calculate_average([m["metrics"].get("accuracy", 0) for m in model_metrics]),
                    "precision": this._calculate_average([m["metrics"].get("precision", 0) for m in model_metrics]),
                    "recall": this._calculate_average([m["metrics"].get("recall", 0) for m in model_metrics]),
                    "f1_score": this._calculate_average([m["metrics"].get("f1_score", 0) for m in model_metrics])
                },
                "inference_metrics": {
                    "average_latency": this._calculate_average([m["latency_ms"] for m in inference_metrics]),
                    "total_requests": len(inference_metrics),
                    "success_rate": this._calculate_success_rate(inference_metrics),
                    "average_input_size": this._calculate_average([m["input_size"] for m in inference_metrics])
                }
            }
            
            return summary

        except Exception as e:
            logger.error(f"Failed to get model performance summary: {str(e)}")
            raise MonitoringError(f"Failed to get model performance summary: {str(e)}")

    def _calculate_average(self, values: List[float]) -> float:
        """Calculate average of a list of values."""
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _calculate_success_rate(self, metrics: List[Dict[str, Any]]) -> float:
        """Calculate success rate from inference metrics."""
        if not metrics:
            return 0.0
        successful = sum(1 for m in metrics if m["success"])
        return successful / len(metrics) 