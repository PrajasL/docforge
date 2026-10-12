from celery import Celery

from app.core.config import settings
from app.core.monitoring import init_monitoring

init_monitoring()

celery_app = Celery(
    "docforge_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    broker_connection_retry_on_startup=False,
    broker_connection_max_retries=1,
    beat_schedule={
        "cleanup-expired-jobs-every-15-min": {
            "task": "app.workers.tasks.cleanup_expired_jobs_task",
            "schedule": 900.0,
        },
    },
)
