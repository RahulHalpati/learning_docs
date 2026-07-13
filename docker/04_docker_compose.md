# 04: Docker Compose — Multi-Container Apps with One Command

> **Level:** Intermediate
> **Prerequisites:** Module 03 (Networking & Volumes)
> **Time:** 60–90 minutes
> **Last Updated:** 2026-05-21
> **What You'll Learn:** Docker Compose v2 syntax, `compose.yaml`, watch mode, health checks, multi-environment setup

---

## Introduction

**What:** Docker Compose lets you define and run your entire multi-container application with a single `compose.yaml` file and one command: `docker compose up`.

**Why:** Managing 5 containers manually with `docker run` is exhausting and error-prone. Compose gives you:
- One file to describe the entire stack
- One command to start everything
- Built-in networking (services find each other by name)
- Easy environment configuration

**Analogy:** If individual `docker run` commands are cooking each dish separately, Compose is a recipe book that says "cook all these dishes together, in this order, with these ingredients."

**📢 Important — v1 vs v2:**
```bash
# ❌ OLD (v1) — deprecated, removed in Docker Desktop 4.x
docker-compose up

# ✅ NEW (v2) — built into Docker, use this!
docker compose up
# No hyphen! It's now a Docker plugin
```

---

## Part 1: Your First Compose File

### The `compose.yaml` File

```yaml
# compose.yaml — Modern name (also accepts docker-compose.yml)
# Note: The 'version:' field is OBSOLETE — don't use it!
# Compose now follows a rolling spec, no version numbers needed.

services:
  # Each key under 'services' is a container
  web:
    # What service is this: Our Flask web application
    image: my-flask-app:1.0      # Use a pre-built image
    ports:
      - "5000:5000"              # HOST:CONTAINER port mapping
    environment:
      - FLASK_ENV=production     # Environment variable
      - DATABASE_URL=postgresql://appuser:pass@db:5432/appdb
      # 'db' = hostname of the postgres service below (Docker DNS!)
    depends_on:
      db:
        condition: service_healthy  # Wait until db is healthy!
        # Without this, web might start before database is ready → crash

  db:
    # What service is this: PostgreSQL database
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: appdb
    volumes:
      - postgres-data:/var/lib/postgresql/data  # Named volume for persistence
    healthcheck:
      # What: Test if PostgreSQL is ready to accept connections
      test: ["CMD-SHELL", "pg_isready -U appuser -d appdb"]
      # pg_isready: PostgreSQL tool to check if server accepts connections
      interval: 10s    # Run health check every 10 seconds
      timeout: 5s      # Wait up to 5s for a response
      retries: 5       # Mark unhealthy after 5 consecutive failures
      start_period: 10s  # Grace period (PostgreSQL takes time to start)

# Named volumes (declared at top level, shared across services)
volumes:
  postgres-data:
    # No options needed — Docker manages it automatically
```

**Core commands:**
```bash
# Start all services (build images if needed)
docker compose up

# Start in detached (background) mode
docker compose up -d

# Stop all services (containers + networks removed, volumes kept)
docker compose down

# Stop and remove volumes too (CAREFUL: deletes database data!)
docker compose down -v

# View logs from all services
docker compose logs

# View logs for a specific service
docker compose logs web

# Follow logs in real-time
docker compose logs -f web

# See running services
docker compose ps

# Run a one-off command in a service
docker compose exec web bash
docker compose exec db psql -U appuser appdb

# Scale a service (run multiple instances)
docker compose up -d --scale web=3
```

---

## Part 2: Building Images with Compose

Instead of pre-built images, Compose can build images from your Dockerfile:

```yaml
services:
  api:
    # 'build' tells Compose to build from a Dockerfile
    build:
      context: ./api          # Directory containing Dockerfile
      dockerfile: Dockerfile  # Name of Dockerfile (default: 'Dockerfile')
      args:
        # Pass build arguments to the Dockerfile
        APP_VERSION: "1.2.0"
        PYTHON_VERSION: "3.12"
    ports:
      - "8000:8000"

  frontend:
    build:
      context: ./frontend
      target: runtime         # Build only up to a specific multi-stage target
      # Why: In development, you might target a 'dev' stage
      # In production, target 'runtime' for the lean final image
    ports:
      - "3000:3000"
```

```bash
# Build all services
docker compose build

# Build a specific service
docker compose build api

# Build with no cache (force fresh build)
docker compose build --no-cache

# Build and start
docker compose up --build
```

---

## Part 3: Environment Variables

### Using .env Files

```bash
# .env — loaded automatically by docker compose
# Never commit this file to Git! Add it to .gitignore
POSTGRES_USER=appuser
POSTGRES_PASSWORD=SuperSecret123
POSTGRES_DB=appdb
API_PORT=8000
DEBUG=false
```

```yaml
# compose.yaml — reference .env variables
services:
  db:
    image: postgres:16-alpine
    environment:
      # Syntax 1: Direct reference from .env
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}

  api:
    build: ./api
    ports:
      - "${API_PORT}:8000"      # Dynamic port from .env
    env_file:
      - .env                    # Load entire .env file into container
      # Alternatively: load specific env files
      - .env.secrets            # Sensitive keys (never commit!)
```

### Multiple Environments

```
project/
├── compose.yaml          # Base configuration (shared)
├── compose.dev.yaml      # Development overrides
├── compose.prod.yaml     # Production overrides
├── .env                  # Default environment variables
└── .env.production       # Production-specific variables
```

**compose.yaml (base):**
```yaml
services:
  api:
    build: ./api
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/mydb

  db:
    image: postgres:16-alpine
    volumes:
      - db-data:/var/lib/postgresql/data

volumes:
  db-data:
```

**compose.dev.yaml (development overrides):**
```yaml
services:
  api:
    build:
      context: ./api
      target: development          # Use dev stage from multi-stage Dockerfile
    environment:
      - DEBUG=true
      - RELOAD=true
    volumes:
      - ./api:/app                 # Bind mount for hot-reload
    ports:
      - "8000:8000"

  db:
    ports:
      - "5432:5432"                # Expose DB to host for debugging tools
```

**compose.prod.yaml (production overrides):**
```yaml
services:
  api:
    image: myregistry.io/my-api:${APP_VERSION}  # Use published image
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
    restart: unless-stopped
```

**Usage:**
```bash
# Development
docker compose -f compose.yaml -f compose.dev.yaml up

# Production
docker compose -f compose.yaml -f compose.prod.yaml up -d

# Shortcut: set COMPOSE_FILE env var
export COMPOSE_FILE=compose.yaml:compose.dev.yaml
docker compose up
```

---

## Part 4: Docker Compose Watch (2025 Feature!)

**Compose Watch** is one of the most useful new features. It automatically syncs your code changes into running containers — no rebuild, no restart, just instant updates.

```yaml
services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    
    # The 'develop' block enables Compose Watch
    develop:
      watch:
        # Action 1: 'sync' — copy file changes into the container
        # Use for: Hot-reloadable code (Python, Node.js, etc.)
        - action: sync
          path: ./api/src           # Watch this host directory
          target: /app/src          # Sync to this container path
          # Effect: Edit a .py file → instantly appears in container
          # Your app's hot-reload feature (uvicorn --reload) picks it up

        # Action 2: 'rebuild' — rebuild the image from scratch
        # Use for: Dependency changes (requirements.txt, package.json)
        - action: rebuild
          path: ./api/requirements.txt
          # Why: Dependency changes can't be hot-reloaded;
          # need a full image rebuild

        # Action 3: 'sync+restart' — sync file then restart container
        # Use for: Config files that require restart (not hot-reload)
        - action: sync+restart
          path: ./api/config.yaml
          target: /app/config.yaml
```

```bash
# Start with watch mode enabled
docker compose watch

# Or start normally, then enable watch in another terminal
docker compose up -d
docker compose watch
```

**What happens with watch:**
```
You edit: ./api/src/routes/users.py
Compose detects change in ./api/src/
Compose copies the file to /app/src/ in the container
Uvicorn (with --reload) detects the change and reloads
Your API is updated — no rebuild, no restart! ⚡
```

---

## Part 5: Health Checks & Dependencies

Without proper health checks, services start in the wrong order and crash:

```
Problem without health checks:
1. Compose starts 'db' (PostgreSQL starts booting...)
2. Compose starts 'api' (immediately)
3. 'api' tries to connect to 'db'
4. 'db' not ready yet → Connection refused → 'api' crashes! 😢
```

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypass
      POSTGRES_DB: mydb
    
    # HEALTHCHECK: Define what "healthy" means for this service
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myuser -d mydb"]
      # CMD-SHELL: Run the command in a shell
      # pg_isready: Returns 0 (healthy) when Postgres accepts connections
      interval: 10s       # Check every 10 seconds
      timeout: 5s         # Max wait time for response
      retries: 5          # Fail after 5 consecutive failures
      start_period: 10s   # Don't count failures in first 10s (startup grace)

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      # redis-cli ping: Returns "PONG" when Redis is ready
      interval: 5s
      timeout: 3s
      retries: 3

  api:
    build: ./api
    depends_on:
      db:
        condition: service_healthy   # Wait until db passes healthcheck!
      redis:
        condition: service_healthy   # Wait until redis is healthy too!
    # Now 'api' only starts when BOTH db and redis are healthy ✅
    ports:
      - "8000:8000"
```

---

## Part 6: Full Production compose.yaml

Here's a complete, production-ready compose.yaml for a FastAPI application:

```yaml
# compose.yaml — Production-grade multi-container application
# FastAPI + PostgreSQL + Redis + Nginx

name: myapp  # Project name (used in container/network names)

services:

  # ── Nginx Reverse Proxy ──────────────────────────────────────
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
      - "443:443"                    # HTTPS (if you add SSL config)
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro  # Config (read-only)
      - ./nginx/certs:/etc/nginx/certs:ro            # SSL certificates
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped          # Restart if it crashes, but not if manually stopped
    networks:
      - frontend

  # ── FastAPI Application ──────────────────────────────────────
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
      target: runtime                # Use production stage from multi-stage build
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - APP_ENV=production
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
      start_period: 15s              # FastAPI may take time to start with DB connections
    restart: unless-stopped
    networks:
      - frontend
      - backend
    deploy:
      resources:
        limits:
          cpus: "1.0"               # Max 1 CPU core
          memory: 512M              # Max 512MB RAM
        reservations:
          cpus: "0.25"              # Minimum reserved
          memory: 128M

  # ── PostgreSQL Database ──────────────────────────────────────
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./postgres/init:/docker-entrypoint-initdb.d  # Run SQL init scripts
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    networks:
      - backend
    deploy:
      resources:
        limits:
          memory: 512M

  # ── Redis Cache ──────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    # --appendonly yes: Enable AOF persistence
    # --requirepass: Require password authentication
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3
    restart: unless-stopped
    networks:
      - backend

# ── Volumes ────────────────────────────────────────────────────
volumes:
  postgres-data:
    driver: local                    # Store on host filesystem (default)
  redis-data:
    driver: local

# ── Networks ───────────────────────────────────────────────────
networks:
  frontend:
    driver: bridge
    # nginx and api can talk here
  backend:
    driver: bridge
    # api, db, and redis can talk here
    # nginx CANNOT reach db or redis directly (security!)
```

**.env file for the above:**
```bash
# .env — NEVER commit this to version control!
POSTGRES_USER=appuser
POSTGRES_PASSWORD=SuperSecure123!
POSTGRES_DB=myappdb
REDIS_PASSWORD=RedisSecure456!
SECRET_KEY=your-64-char-random-secret-key-here
```

---

## Common Mistakes

**Mistake 1: Using `depends_on` without health checks**

```yaml
# ❌ WRONG — 'api' starts when 'db' CONTAINER starts, not when DB is ready
services:
  api:
    depends_on:
      - db   # Only waits for container to start, not for PostgreSQL to be ready!

# ✅ CORRECT — wait for actual readiness
services:
  api:
    depends_on:
      db:
        condition: service_healthy  # Waits for healthcheck to pass!
  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myuser"]
```

**Mistake 2: Hardcoding secrets in compose.yaml**

```yaml
# ❌ WRONG — credentials visible in file and git history!
services:
  db:
    environment:
      POSTGRES_PASSWORD: mysecret123

# ✅ CORRECT — use environment variables from .env
services:
  db:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # Loaded from .env
```

**Mistake 3: Forgetting the `version:` field is obsolete**

```yaml
# ❌ WRONG — the 'version' key is deprecated and ignored
version: "3.9"
services:
  ...

# ✅ CORRECT — just omit it entirely
services:
  ...
```

---

## Practice Exercises

**Exercise 1: Compose a 3-Tier App**

Create a `compose.yaml` for:
- Nginx (port 80)
- Node.js API (not exposed to host, only nginx talks to it)
- MongoDB (not exposed, only api talks to it)

Requirements: proper networks, named volume for MongoDB, health checks.

<details>
<summary>Solution</summary>

```yaml
services:
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      api:
        condition: service_healthy
    networks:
      - frontend

  api:
    build: ./api
    environment:
      - MONGO_URL=mongodb://admin:pass@mongodb:27017/mydb?authSource=admin
    depends_on:
      mongodb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - frontend
      - backend

  mongodb:
    image: mongo:7.0
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: pass
    volumes:
      - mongo-data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
    networks:
      - backend

volumes:
  mongo-data:

networks:
  frontend:
  backend:
```

**Why it works:** Nginx can reach the API (both on `frontend` network). The API can reach MongoDB (both on `backend` network). Nginx cannot reach MongoDB directly (different networks). Users can only access port 80.
</details>

---

## Best Practices

**✅ DO:**
- Use `condition: service_healthy` with health checks — Why: Prevents race conditions
- Use `.env` for secrets — Why: Never hardcode credentials
- Use named networks — Why: Service isolation and DNS
- Use named volumes — Why: Data persistence across `docker compose down`
- Use `restart: unless-stopped` for production — Why: Auto-recover from crashes

**❌ DON'T:**
- Include `version:` field — Why bad: Obsolete, ignored | Fix: Just remove it
- Use `depends_on: [db]` without health condition — Why bad: DB may not be ready | Fix: Add healthcheck
- Commit `.env` to git — Why bad: Exposes credentials | Fix: Add `.env` to `.gitignore`

---

## What's Next

**Learned:** ✅ compose.yaml syntax, ✅ Multi-environment setup, ✅ Watch mode, ✅ Health checks, ✅ Resource limits

**Next:** Module 05: Security & Docker Scout — Vulnerability scanning, secrets management, non-root best practices

**Check:** Can you run a full stack (web + database + cache) with `docker compose up` in under 2 minutes?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-21 | Initial version — covers Compose v2, Watch mode, 2025 best practices |
