import os
from celery import Celery
from celery.schedules import crontab
import logging

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery('paper_trail')

# Load config from environment variables
celery_app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_rate_limit='10/m',
)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'retry-failed-submissions': {
        'task': 'app.tasks.form_processing.retry_failed_submissions',
        'schedule': crontab(minute='*/15'),  # Run every 15 minutes
        'options': {'queue': 'retry'}
    },
    'cleanup-old-submissions': {
        'task': 'app.tasks.cleanup.cleanup_old_submissions',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight
        'options': {'queue': 'cleanup'}
    }
}

# Configure task routes
celery_app.conf.task_routes = {
    'app.tasks.form_processing.*': {'queue': 'form_processing'},
    'app.tasks.cleanup.*': {'queue': 'cleanup'},
    'app.tasks.analytics.*': {'queue': 'analytics'}
}

# Configure task error handling
@celery_app.task_failure.connect
def handle_task_failure(task_id, exception, args, kwargs, traceback, einfo, **kw):
    logger.error(
        f"Task {task_id} failed: {exception}\n"
        f"Args: {args}\n"
        f"Kwargs: {kwargs}\n"
        f"Traceback: {traceback}"
    )

@celery_app.task_success.connect
def handle_task_success(result, **kw):
    logger.info(f"Task completed successfully: {result}")

# Configure task retry settings
celery_app.conf.task_default_retry_delay = 300  # 5 minutes
celery_app.conf.task_max_retries = 3 