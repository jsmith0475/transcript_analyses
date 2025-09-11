"""
Socket.IO setup and helper utilities for progress/event streaming.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from flask import request, has_request_context
from flask_socketio import SocketIO, emit

# Try to preconfigure Socket.IO with message_queue for background workers
try:
    from src.config import get_config

    _cfg = get_config()
    _mq_url = _cfg.web.redis_url
    if _mq_url.rstrip("/").count("/") == 2:
        _mq_url = f"{_mq_url}/{_cfg.web.redis_db}"
    socketio: SocketIO = SocketIO(
        message_queue=_mq_url,
        async_mode=getattr(_cfg.web, "socketio_async_mode", "eventlet"),
        cors_allowed_origins=getattr(_cfg.web, "socketio_cors_allowed_origins", "*"),
    )
except Exception:
    # Fallback: will be initialized by app factory
    socketio: SocketIO = SocketIO()


def _base_payload(extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    # Build a base payload for progress events. Works for both HTTP and Socket.IO contexts.
    try:
        sid = getattr(request, "sid", None) if has_request_context() else None
    except Exception:
        sid = None
    payload = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "sid": sid,
    }
    if extra:
        payload.update(extra)
    return payload


# Namespace for progress events
PROGRESS_NS = "/progress"


@socketio.on("connect", namespace=PROGRESS_NS)
def on_connect():
    emit("connected", _base_payload({"status": "ok"}))


@socketio.on("disconnect", namespace=PROGRESS_NS)
def on_disconnect():
    # No-op; useful for logging if desired
    pass


def emit_progress(event: str, payload: Dict[str, Any]) -> None:
    """
    Emit a progress event on the progress namespace.
    """
    try:
        if socketio and hasattr(socketio, 'emit'):
            socketio.emit(event, _base_payload(payload), namespace=PROGRESS_NS)
    except Exception:
        # Silently fail if socketio is not available (e.g., in worker context)
        pass


def log_event(level: str, message: str, **extra: Any) -> None:
    """Emit a structured log event to the /progress namespace."""
    try:
        payload: Dict[str, Any] = {
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        if extra:
            payload.update(extra)
        emit_progress(f"log.{level}", payload)
    except Exception:
        pass


def log_debug(message: str, **extra: Any) -> None:
    log_event("debug", message, **extra)


def log_info(message: str, **extra: Any) -> None:
    log_event("info", message, **extra)


def log_warning(message: str, **extra: Any) -> None:
    log_event("warning", message, **extra)


def log_error(message: str, **extra: Any) -> None:
    log_event("error", message, **extra)


def job_queued(job_id: str) -> None:
    emit_progress("job.queued", {"jobId": job_id})


def analyzer_started(job_id: str, stage: str, analyzer: str) -> None:
    emit_progress(
        "analyzer.started",
        {"jobId": job_id, "stage": stage, "analyzer": analyzer},
    )


def analyzer_completed(
    job_id: str,
    stage: str,
    analyzer: str,
    processing_time_ms: int,
    token_usage: Dict[str, int] | None = None,
    cost_usd: float | None = None,
) -> None:
    emit_progress(
        "analyzer.completed",
        {
            "jobId": job_id,
            "stage": stage,
            "analyzer": analyzer,
            "processingTimeMs": processing_time_ms,
            "tokenUsage": token_usage or {},
            "costUSD": cost_usd,
        },
    )


def stage_completed(job_id: str, stage: str) -> None:
    emit_progress("stage.completed", {"jobId": job_id, "stage": stage})


def job_completed(
    job_id: str,
    total_processing_time_ms: int,
    total_token_usage: Dict[str, int] | None = None,
    total_cost_usd: float | None = None,
) -> None:
    emit_progress(
        "job.completed",
        {
            "jobId": job_id,
            "totalProcessingTimeMs": total_processing_time_ms,
            "totalTokenUsage": total_token_usage or {},
            "totalCostUSD": total_cost_usd,
        },
    )


def analyzer_error(job_id: str, stage: str, analyzer: str, error_message: str, processing_time_ms: int | None = None) -> None:
    """Emit analyzer error event."""
    emit_progress(
        "analyzer.error",
        {
            "jobId": job_id,
            "stage": stage,
            "analyzer": analyzer,
            "errorMessage": error_message,
            "processingTimeMs": processing_time_ms,
        },
    )


def job_error(job_id: str, error_code: str, message: str) -> None:
    emit_progress(
        "job.error",
        {
            "jobId": job_id,
            "errorCode": error_code,
            "message": message,
        },
    )
