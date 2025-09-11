# Docker Implementation Guide - Transcript Analysis Tool

**Version**: 1.1  
**Last Updated**: September 9, 2025  
**Purpose**: Complete guide for Docker containerization and orchestration

## 🐳 Docker Overview

The Transcript Analysis Tool uses Docker for consistent development and deployment environments. Our containerization strategy ensures that the application runs identically across all environments - from local development to production deployment.

## 📦 Container Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Docker Network: transcript-net          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────┐│
│  │   Flask App     │  │  Celery Worker  │  │  Redis   ││
│  │   Container     │  │    Container    │  │Container ││
│  │                 │  │                 │  │          ││
│  │  Port: 5001     │  │  Processes      │  │Port:6379 ││
│  │  ↓              │  │  Background     │  │          ││
│  │  API Endpoints  │──│  Tasks          │──│ Queue &  ││
│  │  WebSocket      │  │                 │  │ Sessions ││
│  └─────────────────┘  └─────────────────┘  └──────────┘│
│                                                           │
└──────────────────────────────────────────────────────────┘
```

## 🏗️ Docker Compose Configuration

### Complete docker-compose.yml (current)

```yaml
services:
  redis:
    image: redis:7-alpine
    command: ["redis-server", "--save", "", "--appendonly", "no", "--stop-writes-on-bgsave-error", "no"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    ports:
      - "5001:5000"
    env_file:
      - .env
    environment:
      - OPENAI_MODEL=gpt-5
      - REDIS_URL=redis://redis:6379
      - FLASK_APP=src.app
      - EVENTLET_NO_GREENDNS=yes
    volumes:
      - .:/app
    command: ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "src.app:create_app()"]

  worker:
    build: .
    env_file:
      - .env
    environment:
      - OPENAI_MODEL=gpt-5
      - REDIS_URL=redis://redis:6379
      - EVENTLET_NO_GREENDNS=yes
    volumes:
      - .:/app
    command: celery -A src.app.celery_app.celery worker --loglevel=info -Q celery,default

volumes:
  redis_data:
    driver: local

networks:
  transcript-net:
    driver: bridge
```

## 🔨 Dockerfile Implementation

### Multi-Stage Production Dockerfile

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Set Python path
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/api/health || exit 1

# Default command
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]
```

### Development Dockerfile

```dockerfile
# Development Dockerfile with hot-reload
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install development tools
RUN pip install --no-cache-dir \
    ipython \
    ipdb \
    pytest \
    pytest-cov \
    black \
    flake8

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=development
ENV FLASK_DEBUG=1

# Expose port
EXPOSE 5000

# Run with auto-reload
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--reload"]
```

## 🚀 Docker Commands Reference

### Basic Operations

```bash
# First-time build and start all services
docker compose up -d --build

# View running containers
docker compose ps

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f worker
docker compose logs -f app
docker compose logs -f redis

# Stop all services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```

### Development Commands

```bash
# Python-only code changes (fast):
docker compose restart app
docker compose restart worker   # if Celery code changed too

# Rebuild and restart after Dockerfile/static changes:
docker compose up -d --build

# Gunicorn graceful reload (no full restart):
docker compose exec app kill -HUP 1

# Execute command in running container
docker compose exec app python -c "from src.config import get_config; print(get_config())"

# Open shell in container
docker compose exec app /bin/bash

# Run tests in container
docker compose exec app pytest tests/

# Format code in container
docker compose exec app black src/

# Check Redis queue
docker compose exec redis redis-cli LLEN celery
```

### Debugging Commands

```bash
# Check container health
docker compose ps --all

# Inspect container
docker inspect transcript-app

# View container resource usage
docker stats

# Check network connectivity
docker compose exec app ping redis

# Test Redis connection
docker compose exec app python -c "import redis; r = redis.from_url('redis://redis:6379'); print(r.ping())"

# Test Celery worker
docker compose exec worker celery -A src.app.celery_app:celery inspect active

# View Celery queues
docker compose exec worker celery -A src.app.celery_app:celery inspect reserved
```

## 🔧 Docker Configuration Best Practices

### 1. Environment Variables

Create `.env` file for sensitive data:
```bash
# .env
OPENAI_API_KEY=sk-your-key-here
FLASK_ENV=development
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=DEBUG
```

### 2. Volume Management

```yaml
# Development: Mount source code for hot-reload
volumes:
  - ./src:/app/src  # Code changes reflect immediately
  - ./prompts:/app/prompts  # Prompt templates
  - ./output:/app/output  # Analysis results

# Production: Copy code into image
# No volume mounts for source code
volumes:
  - output_data:/app/output  # Persistent output only
```

### 3. Network Security

```yaml
# Isolated network for services
networks:
  transcript-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

# Service-specific network aliases
services:
  redis:
    networks:
      transcript-net:
        aliases:
          - cache
          - queue
```

### 4. Resource Limits

```yaml
# Production resource constraints
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  worker:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

## 🔍 Docker Troubleshooting

### Common Issues and Solutions

#### 1. Container Won't Start
```bash
# Check logs
docker compose logs app

# Common fixes:
# - Check .env file exists
# - Verify OPENAI_API_KEY is set
# - Ensure ports aren't already in use
```

#### 2. Worker Not Processing Tasks
```bash
# Restart worker
docker compose restart worker

# Check worker is connected
docker compose exec worker celery -A src.app.celery_app:celery inspect ping

# Check for tasks in queue
docker compose exec redis redis-cli LLEN celery
```

#### 3. Redis Connection Issues
```bash
# Test Redis connectivity
docker compose exec redis redis-cli ping

# Clear Redis if corrupted
docker compose exec redis redis-cli FLUSHALL

# Disable persistence errors
docker compose exec redis redis-cli CONFIG SET stop-writes-on-bgsave-error no
```

#### 4. Out of Memory
```bash
# Check memory usage
docker system df

# Clean up unused resources
docker system prune -a

# Remove old volumes
docker volume prune
```

## 📊 Docker Performance Optimization

### 1. Build Optimization

```dockerfile
# Use specific Python version
FROM python:3.11.5-slim

# Leverage build cache
COPY requirements.txt .
RUN pip install -r requirements.txt
# Then copy source code
COPY . .

# Multi-stage builds reduce image size
# Final image: ~200MB vs ~800MB
```

### 2. Layer Caching

```dockerfile
# Order matters - least changing first
COPY requirements.txt .
RUN pip install -r requirements.txt

# Frequently changing files last
COPY src/ ./src/
```

### 3. Container Startup

```yaml
# Health checks ensure dependencies are ready
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
  interval: 5s
  timeout: 3s
  retries: 5
  start_period: 10s
```

## 🚢 Production Deployment

### Docker Swarm Configuration

```yaml
# docker-stack.yml
version: '3.8'

services:
  app:
    image: transcript-analyzer:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  worker:
    image: transcript-analyzer:latest
    command: celery worker
    deploy:
      replicas: 5
      placement:
        constraints:
          - node.role == worker
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: transcript-analyzer
spec:
  replicas: 3
  selector:
    matchLabels:
      app: transcript-analyzer
  template:
    metadata:
      labels:
        app: transcript-analyzer
    spec:
      containers:
      - name: app
        image: transcript-analyzer:latest
        ports:
        - containerPort: 5000
        env:
        - name: REDIS_URL
          value: redis://redis-service:6379
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

## 🔐 Docker Security Best Practices

### 1. Non-Root User
```dockerfile
# Create and use non-root user
RUN useradd -m -u 1000 appuser
USER appuser
```

### 2. Minimal Base Images
```dockerfile
# Use slim or alpine variants
FROM python:3.11-slim  # ~150MB
# Not: FROM python:3.11  # ~900MB
```

### 3. Secret Management
```bash
# Use Docker secrets (Swarm)
docker secret create openai_key openai_key.txt

# Reference in compose
secrets:
  openai_key:
    external: true
```

### 4. Image Scanning
```bash
# Scan for vulnerabilities
docker scan transcript-analyzer:latest

# Use Trivy for detailed scanning
trivy image transcript-analyzer:latest
```

## 📈 Monitoring Docker Containers

### Prometheus Metrics
```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Container Metrics
```bash
# Real-time stats
docker stats

# Export metrics
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Log aggregation
docker compose logs -f --tail=100 | grep ERROR
```

## 🔄 Docker Development Workflow

### 1. Local Development
```bash
# Start development environment
docker compose up -d

# Watch logs
docker compose logs -f

# Make code changes (auto-reload enabled)
# Test changes
curl http://localhost:5001/api/health

# Run tests
docker compose exec app pytest
```

### 2. Testing
```bash
# Run test suite
docker compose -f docker-compose.test.yml up --abort-on-container-exit

# Clean test environment
docker compose -f docker-compose.test.yml down -v
```

### 3. Building for Production
```bash
# Build production image
docker build -f Dockerfile.prod -t transcript-analyzer:prod .

# Tag for registry
docker tag transcript-analyzer:prod registry.example.com/transcript-analyzer:v1.0.0

# Push to registry
docker push registry.example.com/transcript-analyzer:v1.0.0
```

## 📝 Docker Checklist

### Development Setup
- [ ] Docker Desktop installed
- [ ] docker-compose.yml configured
- [ ] .env file created with API keys
- [ ] Volumes mounted for hot-reload
- [ ] Services starting successfully

### Production Readiness
- [ ] Multi-stage Dockerfile optimized
- [ ] Non-root user configured
- [ ] Health checks implemented
- [ ] Resource limits set
- [ ] Secrets management configured
- [ ] Image scanned for vulnerabilities
- [ ] Monitoring configured

### Deployment
- [ ] Images tagged appropriately
- [ ] Registry configured
- [ ] Orchestration platform ready
- [ ] Rollback strategy defined
- [ ] Backup procedures in place

---

**Docker Guide Maintainer**: DevOps Team  
**Last Review**: September 6, 2025  
**Next Review**: October 6, 2025
