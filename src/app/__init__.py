"""
Flask application factory for the Transcript Analysis Tool.
Sets up: Config, Sessions (Redis), Socket.IO, API blueprint, and health endpoint.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from flask_session import Session
from redis import Redis, from_url as redis_from_url

from src.config import get_config, AppConfig
from .sockets import socketio


def _init_session_store(app: Flask, cfg: AppConfig) -> Optional[Redis]:
    """
    Initialize Redis-backed session store if REDIS_URL is available.
    Returns the Redis client or None if init failed (falls back to filesystem).
    """
    redis_client: Optional[Redis] = None
    try:
        redis_url = cfg.web.redis_url
        # Append db if not provided (use cfg.web.redis_db)
        if redis_url.rstrip("/").count("/") == 2:
            redis_url = f"{redis_url}/{cfg.web.redis_db}"
        redis_client = redis_from_url(redis_url)
        # Ping to validate connectivity
        redis_client.ping()

        app.config.update(
            SESSION_TYPE="redis",
            SESSION_REDIS=redis_client,
            PERMANENT_SESSION_LIFETIME=cfg.processing.session_timeout,
        )
    except Exception:
        # Fallback to filesystem sessions in dev if Redis not available
        app.config.update(
            SESSION_TYPE="filesystem",
            PERMANENT_SESSION_LIFETIME=cfg.processing.session_timeout,
        )
        redis_client = None
    return redis_client


def create_app(config_object: AppConfig | None = None) -> Flask:
    """
    Flask application factory.
    """
    cfg = config_object or get_config()
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )

    # Core config
    app.config.update(
        SECRET_KEY=cfg.web.secret_key,
        MAX_CONTENT_LENGTH=cfg.web.max_content_length,
        UPLOAD_FOLDER=str(cfg.web.upload_folder),
        JSON_SORT_KEYS=False,
    )

    # CORS for dev
    CORS(app, resources={r"/api/*": {"origins": "*"}, r"/socket.io/*": {"origins": "*"}})

    # Sessions
    _ = _init_session_store(app, cfg)
    Session(app)

    # Socket.IO with Redis message_queue for cross-process events
    try:
        mq_url = cfg.web.redis_url
        if mq_url.rstrip("/").count("/") == 2:
            mq_url = f"{mq_url}/{cfg.web.redis_db}"
    except Exception:
        mq_url = None

    socketio.init_app(
        app,
        async_mode=getattr(cfg.web, "socketio_async_mode", "eventlet"),
        cors_allowed_origins=getattr(cfg.web, "socketio_cors_allowed_origins", "*"),
        message_queue=mq_url,
    )

    # Register API blueprint
    from .api import api_bp  # defer import until app exists
    app.register_blueprint(api_bp, url_prefix="/api")

    # Root UI
    @app.get("/")
    def index():
        return render_template("index.html")

    # Health endpoint
    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "time": datetime.utcnow().isoformat() + "Z",
                "model": cfg.llm.model,
                "redis": app.config.get("SESSION_TYPE"),
            }
        )

    # Log readiness for easier container diagnostics
    try:
        app.logger.info(
            "App initialized. Health at /health. model=%s async=%s mq=%s",
            cfg.llm.model,
            getattr(cfg.web, "socketio_async_mode", None),
            mq_url,
        )
    except Exception:
        pass

    return app


# Convenience for running via `flask run`
# Only create the app automatically when invoked by Flask CLI or explicitly requested.
if os.getenv("FLASK_RUN_FROM_CLI") == "true" or os.getenv("CREATE_FLASK_APP", "").lower() == "true":
    app = create_app()
else:
    # Avoid initializing Socket.IO/eventlet when importing this package from CLI scripts
    app = None
