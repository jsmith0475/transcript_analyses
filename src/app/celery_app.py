"""
Celery app initialization decoupled from Flask to avoid circular imports.
- Broker/Backend: Redis (from AppConfig.web)
- Tasks live in: src.app.orchestration

This module exposes a module-level `celery` instance that workers use via:
  celery -A src.app.celery_app.celery worker --loglevel=info -Q default
"""

from __future__ import annotations

from celery import Celery
from src.config import get_config

# Build Celery instance from configuration (no Flask app import here)
_cfg = get_config()

celery = Celery(
    "transcript-analysis",
    broker=_cfg.web.celery_broker_url,
    backend=_cfg.web.celery_result_backend,
    include=["src.app.orchestration"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_time_limit=_cfg.web.celery_task_time_limit,
    worker_send_task_events=True,
    task_send_sent_event=True,
)
