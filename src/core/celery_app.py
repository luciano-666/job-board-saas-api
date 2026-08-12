import structlog
from celery import Celery
from celery.signals import setup_logging

from src.core.config import settings

logger = structlog.get_logger(__name__)


# Celery app is created here, imported by both:
#   - the worker process (celery -A src.core.celery_app worker)
#   - the FastAPI app (task producers call .delay()/.apply_async())
# It must NEVER import FastAPI app code (src.main) to avoid circular imports
# and to keep the worker process fully independent, per constraint #3.
celery_app = Celery(
    "job_board_saas",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        # Task modules registered explicitly — added incrementally as
        # INFRA-2/3/4 land (email confirmation, status change, daily digest,
        # auto-archive). Keeping this list explicit avoids autodiscovery
        # surprises across bounded contexts.
        # "src.modules.applications.infrastructure.tasks",
        # "src.modules.jobs.infrastructure.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    # Reasonable defaults; tune per-task with @task(...) overrides later.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)


@setup_logging.connect
def _configure_worker_logging(**kwargs) -> None:
    """Reuse the app's structlog JSON config instead of Celery's own
    logging setup, so worker logs match FastAPI logs (same JSON format,
    same structlog processors) — keeps log aggregation consistent."""
    from src.core.logging_config import configure_logging

    configure_logging()
    logger.info("Celery worker logging configured.")
