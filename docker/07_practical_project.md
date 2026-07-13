# 07: Practical Project — Dockerize a Complete FastAPI Application

> **Difficulty:** Intermediate
> **Time:** 2–4 hours
> **Prerequisites:** Modules 00–06 (all concepts)
> **Last Updated:** 2026-05-21
> **What You'll Build:** A production-ready URL shortener with FastAPI + PostgreSQL + Redis, fully Dockerized with security, health checks, and CI/CD

---

## Overview

**Building:** A **URL Shortener API** (like bit.ly) — a real-world application that combines all the Docker concepts you've learned.

**Why this project?**
- Requires a database (PostgreSQL) and a cache (Redis) → **networking**
- API + DB + Cache → **Docker Compose**
- Real users → **security** and **health checks**
- Production deployment → **CI/CD pipeline**

**What you'll have when done:**
```
✅ FastAPI application (Dockerized with multi-stage build)
✅ PostgreSQL database (with named volume for persistence)
✅ Redis cache (for fast URL lookups)
✅ Nginx reverse proxy
✅ Docker Compose setup (dev + prod environments)
✅ Security: non-root user, read-only filesystem, Docker Scout scan
✅ Health checks for all services
✅ GitHub Actions CI/CD pipeline
```

---

## Requirements

| Feature | Module Reference |
|---------|----------------|
| Multi-stage Dockerfile | Module 02 |
| Named volumes + custom networks | Module 03 |
| docker compose with health checks | Module 04 |
| Non-root user + secrets | Module 05 |
| CI/CD pipeline | Module 06 |

---

## Project Structure

```
url-shortener/
├── api/
│   ├── Dockerfile              # Multi-stage build
│   ├── requirements.txt        # Python dependencies
│   ├── requirements-dev.txt    # Development-only deps
│   └── app/
│       ├── main.py             # FastAPI app entry point
│       ├── models.py           # Database models
│       ├── database.py         # Database connection
│       ├── cache.py            # Redis client
│       ├── routes/
│       │   ├── urls.py         # URL shortener endpoints
│       │   └── health.py       # Health check endpoint
│       └── config.py           # App configuration
├── nginx/
│   └── nginx.conf              # Reverse proxy config
├── monitoring/
│   └── prometheus.yml          # Metrics scraping config
├── compose.yaml                # Base compose config
├── compose.dev.yaml            # Dev overrides (bind mounts, ports)
├── compose.prod.yaml           # Prod overrides (resource limits)
├── .env.example                # Example env vars (commit this)
├── .env                        # Actual secrets (never commit!)
├── .dockerignore               # Files to exclude from build
└── .github/
    └── workflows/
        └── ci-cd.yml           # GitHub Actions pipeline
```

---

## Build Steps

### Phase 1: Application Code

**`api/app/config.py`** — Centralized configuration:
```python
# config.py — App configuration from environment variables
# What: Pydantic settings automatically reads from environment variables
# Why: One place for all config; easy to override per environment

from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """
    Application settings.
    
    What: Loaded from environment variables (or .env file)
    Why: Separates configuration from code (12-factor app principle)
    
    Pydantic validates types automatically:
    - If DATABASE_URL is missing → startup error (not silent failure)
    - If REDIS_TTL is set to "abc" → type error caught early
    """
    
    # Database
    database_url: str                            # Required: no default
    # What: PostgreSQL connection string
    # Format: postgresql://user:pass@host:port/dbname
    
    # Redis
    redis_url: str = "redis://redis:6379/0"      # Optional with default
    # What: Redis connection URL
    # Default: Works with our compose.yaml service name 'redis'
    
    redis_ttl: int = 3600                        # URL cache TTL in seconds
    # What: How long URLs are cached in Redis
    # Default: 1 hour
    
    # App settings
    app_name: str = "URL Shortener API"
    app_version: str = "1.0.0"
    debug: bool = False                          # Never True in production!
    base_url: str = "http://localhost:8000"      # Used to construct short URLs
    
    class Config:
        env_file = ".env"                        # Load from .env file if present
        case_sensitive = False                   # DATABASE_URL = database_url

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    What: Returns the same Settings object on every call (cached)
    Why: Avoids re-reading environment variables on every request
    
    Returns:
        Settings: Application configuration object
    """
    return Settings()
```

**`api/app/models.py`** — Database model:
```python
# models.py — Database models using SQLAlchemy
# What: Defines the database table structure as Python classes
# Why: ORM (Object-Relational Mapper) lets us work with DB using Python objects

from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import random
import string

# Base class that all models inherit from
# What: Provides metadata and ORM functionality
Base = declarative_base()

class URL(Base):
    """
    URL model — represents a shortened URL in the database.
    
    What: Maps to the 'urls' table in PostgreSQL
    Why: Stores the mapping between short codes and original URLs
    """
    
    __tablename__ = "urls"              # Table name in PostgreSQL
    
    id = Column(Integer, primary_key=True, index=True)
    # What: Auto-incrementing unique ID
    # primary_key=True: Unique identifier for each row
    # index=True: Create a database index for fast lookups by ID
    
    short_code = Column(String(10), unique=True, index=True, nullable=False)
    # What: The short URL code (e.g., 'abc123' in short.ly/abc123)
    # unique=True: No two URLs can have the same code
    # index=True: Fast lookups when redirecting users
    # nullable=False: Cannot be empty
    
    original_url = Column(String(2048), nullable=False)
    # What: The full original URL to redirect to
    # 2048: Maximum URL length (browser limit is ~2048)
    
    clicks = Column(Integer, default=0)
    # What: Track how many times this URL was accessed
    # default=0: New URLs start with 0 clicks
    
    created_at = Column(DateTime, default=datetime.utcnow)
    # What: When this URL was created
    # default=datetime.utcnow: Set automatically at creation time

    @staticmethod
    def generate_code(length: int = 6) -> str:
        """
        Generate a random short code.
        
        What: Creates a random alphanumeric string (e.g., 'aB3xKm')
        Why: Each shortened URL needs a unique, human-friendly identifier
        
        Args:
            length (int): Length of the code. Default 6.
        
        Returns:
            str: Random alphanumeric code
        
        Example:
            >>> URL.generate_code()
            'aB3xKm'
        """
        characters = string.ascii_letters + string.digits
        # ascii_letters: a-z + A-Z
        # digits: 0-9
        # Together: 62 possible characters → 62^6 = 56 billion combinations
        return ''.join(random.choices(characters, k=length))
```

**`api/app/routes/urls.py`** — API endpoints:
```python
# routes/urls.py — URL shortener API endpoints
# What: FastAPI routes for creating and resolving short URLs
# Why: Handles the core business logic of the URL shortener

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl
from typing import Optional
import logging

from ..database import get_db
from ..cache import get_cache
from ..models import URL
from ..config import get_settings

logger = logging.getLogger(__name__)   # Module-level logger
router = APIRouter(prefix="/api/v1", tags=["URLs"])
settings = get_settings()

# ── Request/Response Schemas ─────────────────────────────────────
class CreateURLRequest(BaseModel):
    """
    Request body for creating a shortened URL.
    
    What: Pydantic model validates incoming JSON automatically
    Why: Ensures url is actually a valid URL before processing
    """
    url: HttpUrl                        # Pydantic validates this is a real URL
    custom_code: Optional[str] = None  # Allow custom short codes

class URLResponse(BaseModel):
    """Response after creating a short URL."""
    short_code: str
    short_url: str                      # Full short URL with domain
    original_url: str
    clicks: int

# ── Endpoints ────────────────────────────────────────────────────
@router.post("/shorten", response_model=URLResponse, status_code=201)
async def shorten_url(
    request: CreateURLRequest,
    db: AsyncSession = Depends(get_db),
    cache = Depends(get_cache),
):
    """
    Create a shortened URL.
    
    What: Takes a long URL and returns a short code that redirects to it
    Why: Core functionality of the URL shortener
    
    Args:
        request: Contains the original URL and optional custom code
        db: Database session (injected by FastAPI dependency injection)
        cache: Redis client (injected by dependency injection)
    
    Returns:
        URLResponse: The created short URL with its code and stats
    
    Raises:
        HTTPException 400: If custom code is already taken
        HTTPException 422: If URL is invalid (handled by Pydantic)
    """
    
    # Use custom code or generate one
    code = request.custom_code or URL.generate_code()
    
    # Check if custom code already exists
    if request.custom_code:
        existing = await db.get(URL, {"short_code": code})
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Short code '{code}' is already taken"
            )
    
    # Create database record
    url_obj = URL(
        short_code=code,
        original_url=str(request.url)
    )
    db.add(url_obj)
    await db.commit()
    await db.refresh(url_obj)   # Refresh to get generated ID
    
    # Cache the mapping for fast redirects
    await cache.setex(
        f"url:{code}",          # Key format: 'url:abc123'
        settings.redis_ttl,     # TTL from config
        str(request.url)        # Value: original URL
    )
    
    logger.info(f"Created short URL: {code} → {request.url}")
    
    return URLResponse(
        short_code=code,
        short_url=f"{settings.base_url}/r/{code}",
        original_url=str(request.url),
        clicks=0
    )

@router.get("/r/{code}")
async def redirect_url(
    code: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    cache = Depends(get_cache),
):
    """
    Redirect to the original URL.
    
    What: Looks up short code, increments click counter, redirects user
    Why: Core redirect functionality — must be fast!
    
    Strategy:
    1. Check Redis cache first (fast: < 1ms)
    2. If cache miss, check PostgreSQL (slower: ~10ms)
    3. If found, re-cache and redirect
    4. Increment click count in background (doesn't slow response)
    
    Args:
        code: The short URL code from the URL path
        background_tasks: FastAPI background task runner
        db: Database session
        cache: Redis client
    
    Returns:
        RedirectResponse: 301 redirect to original URL
    
    Raises:
        HTTPException 404: If short code doesn't exist
    """
    
    # Step 1: Check cache first (fast path)
    cached_url = await cache.get(f"url:{code}")
    if cached_url:
        # Cache hit! Schedule click increment without waiting for it
        background_tasks.add_task(increment_clicks, code, db)
        return RedirectResponse(url=cached_url, status_code=301)
    
    # Step 2: Cache miss — check database (slow path)
    url_obj = await db.execute(
        select(URL).where(URL.short_code == code)
    )
    url_obj = url_obj.scalar_one_or_none()
    
    if not url_obj:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    # Re-populate cache for future requests
    await cache.setex(f"url:{code}", settings.redis_ttl, url_obj.original_url)
    
    # Increment click count in background (doesn't delay response)
    background_tasks.add_task(increment_clicks, code, db)
    
    return RedirectResponse(url=url_obj.original_url, status_code=301)


async def increment_clicks(code: str, db: AsyncSession) -> None:
    """
    Increment click counter for a URL.
    
    What: Updates the click count in the database
    Why: Run as background task so it doesn't slow down the redirect
    
    Args:
        code: Short URL code
        db: Database session
    """
    await db.execute(
        update(URL).where(URL.short_code == code).values(clicks=URL.clicks + 1)
    )
    await db.commit()
```

---

### Phase 2: Dockerfile (Multi-Stage)

**`api/Dockerfile`:**
```dockerfile
# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────
# Multi-stage Dockerfile for URL Shortener API
# Stage 1: builder — installs Python dependencies
# Stage 2: runtime — minimal production image
# ─────────────────────────────────────────────────────────────────

ARG PYTHON_VERSION=3.12

# ── Stage 1: Install Dependencies ────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

# Install build dependencies for C-extension packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies (with BuildKit cache for speed)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# ── Stage 2: Production Runtime ───────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

# Build-time metadata
ARG APP_VERSION=1.0.0
ARG BUILD_DATE
LABEL version="${APP_VERSION}" \
      build-date="${BUILD_DATE}" \
      description="URL Shortener FastAPI App"

WORKDIR /app

# Runtime system dependencies only (not build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the virtual environment (no build tools)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Security: Non-root user
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup \
    --no-create-home --shell /sbin/nologin appuser

# Copy application code with correct ownership
COPY --chown=appuser:appgroup app/ ./app/

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`.dockerignore`:**
```
# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.coverage
htmlcov/

# Virtual environments
.venv/
venv/
env/

# IDE
.vscode/
.idea/
*.swp

# Secrets (CRITICAL!)
.env
.env.*
!.env.example
*.key
*.pem
secrets/

# Development
tests/
*.test.py
compose.dev.yaml
```

---

### Phase 3: Docker Compose

**`compose.yaml`:**
```yaml
name: url-shortener

services:

  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      api:
        condition: service_healthy
    networks:
      - frontend
    restart: unless-stopped

  api:
    build:
      context: ./api
      dockerfile: Dockerfile
      target: runtime
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - BASE_URL=${BASE_URL:-http://localhost}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - frontend
      - backend
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - backend
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3
    networks:
      - backend
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:

networks:
  frontend:
  backend:
```

**`.env.example`** (commit this template — not the actual .env!):
```bash
# Copy this to .env and fill in your values
# cp .env.example .env
POSTGRES_USER=urluser
POSTGRES_PASSWORD=CHANGE_ME_USE_STRONG_PASSWORD
POSTGRES_DB=urlshortener
REDIS_PASSWORD=CHANGE_ME_REDIS_PASSWORD
BASE_URL=http://localhost
```

---

### Phase 4: GitHub Actions CI/CD

**`.github/workflows/ci-cd.yml`:**
```yaml
name: URL Shortener CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/api

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-retries 5
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-retries 5
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r api/requirements.txt -r api/requirements-dev.txt
      - run: pytest api/tests/ -v
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379/0

  build-and-scan:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: ./api
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Docker Scout Scan
        uses: docker/scout-action@v1
        with:
          command: cves
          image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          only-severities: critical,high
          exit-code: true
```

---

## Running the Complete Project

```bash
# 1. Clone/create the project structure
mkdir url-shortener && cd url-shortener
# ... create all files as shown above ...

# 2. Copy and configure environment
cp .env.example .env
# Edit .env with strong passwords!

# 3. Start everything
docker compose up --build -d

# 4. Run database migrations
docker compose exec api python -c "
from app.database import engine
from app.models import Base
import asyncio
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(create_tables())
"

# 5. Test the API
# Create a short URL
curl -X POST http://localhost/api/v1/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://docs.docker.com/guides/"}'

# Expected response:
# {
#   "short_code": "aB3xKm",
#   "short_url": "http://localhost/r/aB3xKm",
#   "original_url": "https://docs.docker.com/guides/",
#   "clicks": 0
# }

# Test the redirect
curl -L http://localhost/r/aB3xKm
# Should redirect you to the Docker docs!

# 6. Check health
curl http://localhost/health
# Expected: {"status": "healthy", "components": {"database": {...}, "cache": {...}}}

# 7. View logs
docker compose logs -f

# 8. Scan for vulnerabilities
docker scout cves url-shortener-api:latest

# 9. Stop when done
docker compose down
```

---

## Extend It

| Enhancement | Difficulty | What You'll Learn |
|-------------|-----------|-------------------|
| Add URL expiration (TTL) | Easy | Database timestamps, cleanup jobs |
| Add click analytics endpoint | Easy | Aggregation queries |
| Add authentication (API keys) | Medium | FastAPI middleware, JWT tokens |
| Rate limiting (per IP) | Medium | Redis for rate limiting |
| QR code generation | Medium | External service integration |
| Add Prometheus metrics | Medium | Module 06 integration |
| Deploy to AWS ECS or Fly.io | Hard | Cloud container deployment |
| Add Docker Compose Watch | Easy | Live code reloading |

**Docker Compose Watch setup:**
```yaml
# compose.dev.yaml — Add watch for development
services:
  api:
    develop:
      watch:
        - action: sync
          path: ./api/app
          target: /app/app
        - action: rebuild
          path: ./api/requirements.txt
```

```bash
# Development with hot-reload
docker compose -f compose.yaml -f compose.dev.yaml watch
```

---

## Congratulations! 🎉

You've built and fully Dockerized a production-ready application!

**Skills you've mastered:**
- ✅ Multi-stage Dockerfile (security + size optimization)
- ✅ Docker networks (service isolation + DNS)
- ✅ Named volumes (persistent database storage)
- ✅ Docker Compose (orchestrate entire stack)
- ✅ Health checks (self-healing containers)
- ✅ Docker Scout (vulnerability scanning)
- ✅ Non-root users (security hardening)
- ✅ CI/CD pipeline (automated build + scan + deploy)
- ✅ Structured logging (production observability)

**What to learn next:**
- **Kubernetes (K8s)** — Container orchestration at scale
- **Docker Swarm** — Simpler orchestration for small clusters
- **Terraform + Docker** — Infrastructure as Code for container deployments
- **OpenTelemetry** — Distributed tracing across microservices
- **GitHub Packages / Docker Hub** — Image registry management

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-21 | Initial version — URL shortener with FastAPI + full Docker stack |
