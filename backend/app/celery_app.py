from celery import Celery
from celery.schedules import crontab
import os

# Initialize Celery
celery_app = Celery(
    'paper_trail_automator',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True
)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'retry-failed-submissions': {
        'task': 'retry-failed-submissions',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
    },
}

# Import tasks
celery_app.autodiscover_tasks(['app.tasks']) 