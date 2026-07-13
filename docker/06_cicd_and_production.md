# 06: CI/CD & Production — Pipelines, Monitoring & Health

> **Level:** Intermediate → Advanced
> **Prerequisites:** Module 05 (Security & Docker Scout)
> **Time:** 60–90 minutes
> **Last Updated:** 2026-05-21
> **What You'll Learn:** GitHub Actions Docker pipeline, health checks, structured logging, monitoring with Prometheus/Grafana, Docker production deployment patterns

---

## Introduction

**What:** CI/CD (Continuous Integration/Continuous Deployment) automates the entire journey from code commit to production. Combined with health checks and monitoring, your Docker app becomes self-healing and observable.

**Why:** Manual deployments are slow, error-prone, and don't scale. With CI/CD:
- Every code push is automatically tested
- Images are automatically scanned for vulnerabilities
- Deployments happen with zero downtime
- Problems are detected in seconds, not hours

**The Production Journey:**
```
Developer pushes code
        ↓
GitHub Actions runs
        ↓
    ┌───────┐
    │ Test  │ ← Run unit tests
    └───┬───┘
        ↓
    ┌───────┐
    │ Build │ ← Build Docker image
    └───┬───┘
        ↓
    ┌───────┐
    │ Scan  │ ← Docker Scout vulnerability scan
    └───┬───┘
        ↓
    ┌───────┐
    │ Push  │ ← Push to registry if scan passes
    └───┬───┘
        ↓
    ┌────────┐
    │ Deploy │ ← Update production containers
    └────────┘
        ↓
    ┌──────────┐
    │ Monitor  │ ← Health checks, metrics, logs
    └──────────┘
```

---

## Part 1: GitHub Actions Docker Pipeline

### Complete CI/CD Workflow

```yaml
# .github/workflows/ci-cd.yml
# Full CI/CD pipeline for a Dockerized application

name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io                          # GitHub Container Registry
  IMAGE_NAME: ${{ github.repository }}        # e.g., username/my-app

jobs:
  # ── Job 1: Run Tests ─────────────────────────────────────────
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    services:
      # Spin up a real PostgreSQL for integration tests
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432         # Map to host for test runner

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}

      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
        run: pytest tests/ -v --cov=app --cov-report=xml

      - name: Upload coverage report
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml

  # ── Job 2: Build & Push Image ─────────────────────────────────
  build:
    name: Build & Push Image
    runs-on: ubuntu-latest
    needs: test                               # Only run if tests pass

    permissions:
      contents: read
      packages: write
      security-events: write

    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
      image-tag: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        with:
          driver-opts: image=moby/buildkit:latest   # Use latest BuildKit

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}   # Auto-provided by GitHub

      - name: Extract metadata for Docker
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            # Tag with git SHA (unique, always)
            type=sha,prefix=sha-
            # Tag with branch name
            type=ref,event=branch
            # Tag with semantic version (if git tag is pushed)
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            # Tag as 'latest' only on main branch
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push image
        id: build
        uses: docker/build-push-action@v6
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          # Don't push on PRs — only build to verify
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          build-args: |
            APP_VERSION=${{ github.sha }}
            BUILD_DATE=${{ github.event.head_commit.timestamp }}
          # Use GitHub Actions cache for fast builds
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ── Job 3: Security Scan ──────────────────────────────────────
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: build
    if: github.event_name != 'pull_request'

    permissions:
      contents: read
      packages: read
      security-events: write

    steps:
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Docker Scout CVE Scan
        uses: docker/scout-action@v1
        with:
          command: cves
          image: ${{ needs.build.outputs.image-tag }}
          only-severities: critical,high
          exit-code: true           # Fail pipeline if critical/high CVEs found
          sarif-file: scout-results.sarif

      - name: Upload SARIF results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: scout-results.sarif
        if: always()                # Upload even if scan fails

      - name: Get Scout Recommendations
        uses: docker/scout-action@v1
        with:
          command: recommendations
          image: ${{ needs.build.outputs.image-tag }}
        if: always()

  # ── Job 4: Deploy to Production ───────────────────────────────
  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [build, security-scan]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    environment:
      name: production
      url: https://myapp.example.com

    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            # Pull latest image
            docker pull ${{ needs.build.outputs.image-tag }}
            
            # Zero-downtime rolling update
            cd /opt/myapp
            
            # Update IMAGE_TAG in .env
            echo "IMAGE_TAG=${{ github.sha }}" > .env.deploy
            
            # Pull and restart with compose
            docker compose pull
            docker compose up -d --no-deps api
            # --no-deps: Only restart 'api', leave db/redis running
            
            # Wait for health check to pass
            echo "Waiting for health check..."
            for i in {1..30}; do
              if docker compose ps api | grep -q "healthy"; then
                echo "✅ Deploy successful!"
                exit 0
              fi
              sleep 5
            done
            echo "❌ Health check failed after 150s"
            exit 1
```

---

## Part 2: Health Checks in Production

### Application Health Endpoint

Add a proper `/health` endpoint to your API:

```python
# app/health.py — Health check endpoint
# What: Returns health status of the application and its dependencies
# Why: Docker, Kubernetes, and load balancers use this to verify app readiness

from fastapi import APIRouter
from sqlalchemy import text
import redis
import asyncio
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.
    
    What: Verifies app, database, and cache are all operational
    Why: Orchestrators call this to decide whether to send traffic
    
    Returns:
        dict: Health status with component details
    
    Status codes:
        200: All components healthy
        503: One or more components unhealthy
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.2.0",
        "components": {}
    }
    
    # Check database
    try:
        # Execute a simple query to verify connection
        await db.execute(text("SELECT 1"))
        health["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["status"] = "unhealthy"
        health["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check Redis cache
    try:
        await redis_client.ping()
        health["components"]["cache"] = {"status": "healthy"}
    except Exception as e:
        health["status"] = "unhealthy"
        health["components"]["cache"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Return 503 if unhealthy (Docker/Kubernetes will mark as failing)
    status_code = 200 if health["status"] == "healthy" else 503
    return JSONResponse(content=health, status_code=status_code)

@router.get("/ready")
async def readiness_check():
    """
    Readiness probe — is app ready to receive traffic?
    
    What: Separate from liveness; checks if app can serve requests
    Why: App may be running but still initializing (loading models, warming cache)
    """
    if not app_state.initialized:
        return JSONResponse({"ready": False}, status_code=503)
    return {"ready": True}
```

### Dockerfile HEALTHCHECK

```dockerfile
# Adding health check at the Dockerfile level
HEALTHCHECK --interval=30s \
            --timeout=10s \
            --start-period=15s \
            --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# --interval=30s: Check every 30 seconds
# --timeout=10s: If response takes > 10s, it's unhealthy
# --start-period=15s: Don't count failures in first 15s (app startup time)
# --retries=3: Mark unhealthy after 3 consecutive failures
# curl -f: Returns non-zero exit code on HTTP error (4xx, 5xx)
```

---

## Part 3: Structured Logging

### Always Log to stdout/stderr

```python
# app/logging_config.py — Production logging setup
# What: Configure structured JSON logging for Docker
# Why: Docker captures stdout/stderr; JSON logs work with aggregation tools

import logging
import json
import sys
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """
    Format log records as JSON.
    
    What: Converts Python log records to JSON strings
    Why: Machine-readable logs work with Grafana Loki, ELK Stack, Datadog
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as JSON.
        
        Args:
            record: Python log record with message, level, etc.
        
        Returns:
            str: JSON-formatted log line
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "my-api",                  # Identify the service
            "version": "1.2.0",
        }
        
        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Include extra fields (e.g., request_id, user_id)
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
        
        return json.dumps(log_entry)


def setup_logging():
    """Configure application-wide logging to stdout (JSON format)."""
    
    handler = logging.StreamHandler(sys.stdout)  # Always log to stdout!
    handler.setFormatter(JSONFormatter())
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    
    # Suppress noisy library logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

### Log Rotation in Docker

```yaml
# compose.yaml — Configure log rotation
services:
  api:
    image: my-api:1.0
    logging:
      driver: "json-file"        # Default Docker logging driver
      options:
        max-size: "10m"          # Rotate when log file hits 10MB
        max-file: "3"            # Keep last 3 rotated files
        compress: "true"         # Compress rotated files
        labels: "service,version"  # Add metadata to log entries

  # Alternative: Send logs to centralized system
  api-with-loki:
    image: my-api:1.0
    logging:
      driver: "loki"             # Grafana Loki log driver
      options:
        loki-url: "http://loki:3100/loki/api/v1/push"
        labels: "service=api,env=production"
```

---

## Part 4: Monitoring with Prometheus + Grafana

### Expose Application Metrics

```python
# app/metrics.py — Prometheus metrics
# What: Expose metrics that Prometheus scrapes
# Why: Track request counts, latencies, error rates in real-time

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import APIRouter

router = APIRouter()

# Counter: Only goes up (requests, errors)
REQUEST_COUNT = Counter(
    "http_requests_total",                  # Metric name
    "Total HTTP request count",             # Description
    ["method", "endpoint", "status_code"]  # Labels (dimensions to filter by)
)

# Histogram: Tracks distributions (response times)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5]
    # buckets: Track what % of requests fall under each threshold
)

# Gauge: Can go up or down (active connections, queue size)
ACTIVE_CONNECTIONS = Gauge(
    "active_connections",
    "Number of active WebSocket connections"
)

@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    What: Returns all metrics in Prometheus text format
    Why: Prometheus scrapes this endpoint every 15s to collect data
    
    Returns:
        Response: Prometheus text format metrics
    """
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### Docker Compose Monitoring Stack

```yaml
# compose.monitoring.yml — Add monitoring to your stack
# Run with: docker compose -f compose.yaml -f compose.monitoring.yml up

services:

  # ── Prometheus — Metrics collection ──────────────────────────
  prometheus:
    image: prom/prometheus:v2.51.0
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks:
      - monitoring
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=15d'   # Keep 15 days of data

  # ── Grafana — Dashboards & visualization ──────────────────────
  grafana:
    image: grafana/grafana:10.4.0
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
      GF_INSTALL_PLUGINS: grafana-clock-panel
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    networks:
      - monitoring
    depends_on:
      - prometheus

  # ── cAdvisor — Container resource metrics ─────────────────────
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.49.1
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro                      # Host filesystem (read-only)
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    networks:
      - monitoring
    privileged: true                      # Needed to access host metrics

volumes:
  prometheus-data:
  grafana-data:

networks:
  monitoring:
    driver: bridge
```

**Prometheus config:**
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s          # Scrape metrics every 15 seconds
  evaluation_interval: 15s

scrape_configs:
  # Scrape our API's metrics endpoint
  - job_name: 'my-api'
    static_configs:
      - targets: ['api:8000']   # Container name + port (Docker DNS!)
    metrics_path: '/metrics'    # Our metrics endpoint path

  # Scrape container resource metrics (CPU, memory, network)
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  # Scrape Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

---

## Part 5: Zero-Downtime Deployments

### Rolling Update with Docker Compose

```bash
#!/bin/bash
# deploy.sh — Zero-downtime deployment script

set -e

NEW_VERSION=$1    # Pass version as argument: ./deploy.sh 1.2.0

echo "🚀 Deploying version $NEW_VERSION..."

# 1. Pull the new image
docker pull myregistry.io/my-api:${NEW_VERSION}

# 2. Update the running container (no-deps = don't restart db/redis)
docker compose up -d --no-deps api
# Compose starts new container, replaces old one
# Network connections are maintained by Nginx/load balancer

# 3. Wait for health check to pass
echo "⏳ Waiting for health check..."
MAX_WAIT=60  # Maximum seconds to wait
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    HEALTH=$(docker compose ps api --format json | \
             python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Health',''))" 2>/dev/null)
    
    if [ "$HEALTH" = "healthy" ]; then
        echo "✅ Deployment successful! API is healthy."
        exit 0
    fi
    
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo "  Still waiting... (${ELAPSED}s)"
done

# 4. Rollback if health check fails!
echo "❌ Health check failed! Rolling back..."
docker compose up -d --no-deps api  # Compose re-reads image from compose.yaml
exit 1
```

---

## Part 6: Useful Production Commands

```bash
# View live resource usage for all containers
docker stats

# View logs from last hour (useful for debugging)
docker compose logs --since=1h

# Filter logs by service and time
docker compose logs --since=30m --tail=100 api

# Check container health status
docker compose ps

# Follow health check status
watch -n 5 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'

# Force-remove all stopped containers and unused images
docker system prune -f

# Detailed disk usage
docker system df -v

# Execute command in running container
docker compose exec api python manage.py migrate

# Copy files from container to host (e.g., export logs)
docker cp api-container:/app/logs/error.log ./error.log

# View container events in real-time
docker events --filter container=api
```

---

## Best Practices

**✅ DO:**
- Implement `/health` and `/ready` endpoints — Why: Enables smart load balancing and zero-downtime deploys
- Use structured JSON logging — Why: Machine-readable, works with all log aggregation tools
- Configure log rotation — Why: Prevent disk exhaustion
- Use `--no-deps` for rolling updates — Why: Only restart the updated service
- Export Prometheus metrics — Why: Alerting on response times and error rates

**❌ DON'T:**
- Deploy without scanning images — Why bad: Ship unknown CVEs | Fix: `docker scout cves` in CI
- Run containers without resource limits — Why bad: One container can consume all host resources | Fix: `deploy.resources.limits`
- Skip health checks — Why bad: Dead containers still receive traffic | Fix: HEALTHCHECK in Dockerfile + `condition: service_healthy` in Compose
- Log to files inside container — Why bad: Lost on container restart, disk fill | Fix: Log to stdout/stderr always

---

## What's Next

**Learned:** ✅ GitHub Actions CI/CD, ✅ Health check endpoints, ✅ Structured logging, ✅ Prometheus + Grafana, ✅ Zero-downtime deployments

**Next:** Module 07: Practical Project — Build, secure, and deploy a complete Python FastAPI app with the full Docker stack

**Check:** Can you set up a GitHub Actions pipeline that builds, scans, and deploys your app automatically?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-21 | Initial version — GitHub Actions, Docker Scout CI integration, 2025 patterns |
