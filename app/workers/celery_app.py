"""
Celery background worker application configuration.
Handles asynchronous URL scanning, threat enrichment, and notification queuing.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "phishing_detector_workers",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.tasks.scan",
        "app.workers.tasks.notify",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # Max 5 minutes per task
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,  # Fair task distribution
    task_routes={
        "app.workers.tasks.scan.*": {"queue": "scanning"},
        "app.workers.tasks.notify.*": {"queue": "notifications"},
    },
)
