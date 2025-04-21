from celery import Celery
from app.core.config import settings
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)

# Initialize Celery
celery_app = Celery(
    "paper_trail_automator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.pdf_tasks",
        "app.tasks.form_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.browser_tasks"
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.pdf_tasks.*": {"queue": "pdf"},
        "app.tasks.form_tasks.*": {"queue": "forms"},
        "app.tasks.ai_tasks.*": {"queue": "ai"},
        "app.tasks.browser_tasks.*": {"queue": "browser"}
    },
    task_default_headers={
        'supabase_url': settings.SUPABASE_URL,
        'supabase_key': settings.SUPABASE_KEY
    }
)

@celery_app.task(bind=True)
def debug_task(self):
    logger.info(f"Request: {self.request!r}") 