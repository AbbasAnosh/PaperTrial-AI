from celery import shared_task
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any, List
from app.config.database import get_db
from app.config.redis import get_redis_client
import json
from functools import wraps

logger = logging.getLogger(__name__)

def cache_result(expire_seconds: int = 3600):
    """Decorator to cache task results in Redis"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            redis_client = get_redis_client()
            if not redis_client:
                return func(*args, **kwargs)
                
            # Generate cache key
            cache_key = f"analytics:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get cached result
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
                
            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, expire_seconds, json.dumps(result))
            return result
        return wrapper
    return decorator

@shared_task(
    name='app.tasks.analytics.update_submission_metrics',
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600
)
@cache_result(expire_seconds=3600)
def update_submission_metrics(
    self,
    days: Optional[int] = 30,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update submission metrics for the specified time period.
    
    Args:
        days: Number of days to analyze (default: 30)
        user_id: Optional user ID to filter metrics for specific user
        
    Returns:
        dict: Updated metrics
    """
    try:
        logger.info(f"Updating submission metrics for the last {days} days")
        
        start_date = datetime.utcnow() - timedelta(days=days)
        db = get_db()
        
        # Base query conditions
        query_conditions = [
            ('created_at', 'gte', start_date),
            ('is_deleted', 'eq', False)
        ]
        if user_id:
            query_conditions.append(('user_id', 'eq', user_id))
            
        # Get submission counts by status
        status_counts = db.table('form_submissions').select(
            'status',
            count='exact'
        ).match(query_conditions).execute()
        
        # Get processing time statistics
        processing_times = db.table('form_submissions').select(
            'processing_duration_ms'
        ).match(query_conditions).not_.is_('processing_duration_ms', 'null').execute()
        
        processing_stats = {
            'avg': 0,
            'min': 0,
            'max': 0,
            'p95': 0,
            'p99': 0
        }
        
        if processing_times.data:
            times = [sub['processing_duration_ms'] for sub in processing_times.data]
            processing_stats = {
                'avg': sum(times) / len(times),
                'min': min(times),
                'max': max(times),
                'p95': sorted(times)[int(len(times) * 0.95)],
                'p99': sorted(times)[int(len(times) * 0.99)]
            }
            
        # Get error counts by category
        error_counts = db.table('form_submissions').select(
            'error_category',
            count='exact'
        ).match(query_conditions).not_.is_('error_category', 'null').execute()
        
        # Get retry statistics
        retry_stats = db.table('form_submissions').select(
            'retry_count',
            count='exact'
        ).match(query_conditions).gt('retry_count', 0).execute()
        
        # Get submission method distribution
        method_stats = db.table('form_submissions').select(
            'submission_method',
            count='exact'
        ).match(query_conditions).execute()
        
        # Get hourly submission distribution
        hourly_stats = db.table('form_submissions').select(
            'created_at'
        ).match(query_conditions).execute()
        
        hourly_distribution = {}
        for submission in hourly_stats.data:
            hour = datetime.fromisoformat(submission['created_at']).hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
            
        # Compile metrics
        metrics = {
            'period_days': days,
            'start_date': start_date.isoformat(),
            'end_date': datetime.utcnow().isoformat(),
            'total_submissions': sum(count['count'] for count in status_counts.data),
            'status_breakdown': {
                count['status']: count['count']
                for count in status_counts.data
            },
            'processing_time_stats': {
                k: round(v, 2) for k, v in processing_stats.items()
            },
            'error_breakdown': {
                count['error_category']: count['count']
                for count in error_counts.data
            },
            'retry_statistics': {
                'total_retried': sum(count['count'] for count in retry_stats.data),
                'retry_count_breakdown': {
                    count['retry_count']: count['count']
                    for count in retry_stats.data
                }
            },
            'submission_method_distribution': {
                count['submission_method']: count['count']
                for count in method_stats.data
            },
            'hourly_distribution': hourly_distribution
        }
        
        # Store metrics in database with versioning
        db.table('submission_metrics').insert({
            'period_start': start_date,
            'period_end': datetime.utcnow(),
            'metrics': metrics,
            'version': 1,
            'user_id': user_id
        }).execute()
        
        logger.info("Successfully updated submission metrics")
        return {
            'status': 'success',
            'message': 'Successfully updated submission metrics',
            'metrics': metrics
        }
        
    except Exception as e:
        logger.error(f"Error updating submission metrics: {str(e)}", exc_info=True)
        raise

@shared_task(
    name='app.tasks.analytics.cleanup_old_metrics',
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def cleanup_old_metrics(
    self,
    retention_days: Optional[int] = 90
) -> Dict[str, Any]:
    """
    Clean up old metrics data that exceeds the retention period.
    
    Args:
        retention_days: Number of days to retain metrics (default: 90)
        
    Returns:
        dict: Cleanup summary
    """
    try:
        logger.info(f"Cleaning up metrics older than {retention_days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        db = get_db()
        
        # Delete old metrics
        result = db.table('submission_metrics').delete().lt('period_start', cutoff_date).execute()
        
        logger.info(f"Successfully cleaned up {result.count} old metrics records")
        return {
            'status': 'success',
            'message': f'Successfully cleaned up {result.count} old metrics records',
            'deleted_count': result.count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old metrics: {str(e)}", exc_info=True)
        self.retry(exc=e) 