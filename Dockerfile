# Dev container for Transcript Analysis Tool (Python 3.11 to avoid Py3.13 wheel issues)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (slimmed to avoid large apt cache usage during build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Pre-copy requirements to leverage layer caching
COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# App source
COPY . /app

# Default env (can be overridden by docker-compose env_file)
ENV FLASK_APP=src.app \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000

EXPOSE 5000

# Default command runs Gunicorn with Eventlet for Socket.IO compatibility
# Increased timeout for long-running LLM operations (10 minutes)
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "--timeout", "600", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "100", "src.app:create_app()"]
