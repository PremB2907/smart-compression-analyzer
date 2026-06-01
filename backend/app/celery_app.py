from celery import Celery
from celery.signals import worker_process_init

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "securearchive",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=settings.celery_worker_concurrency,
    task_time_limit=settings.celery_task_time_limit_sec,
    task_soft_time_limit=max(60, settings.celery_task_time_limit_sec - 60),
)
celery_app.autodiscover_tasks(["app.tasks"])


@worker_process_init.connect
def _configure_worker_logging(**_kwargs):
    from app.logging_config import setup_logging

    setup_logging(get_settings().log_level)
