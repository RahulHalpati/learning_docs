# 02: Dockerfile Deep Dive — Multi-Stage Builds, BuildKit & Optimization

> **Level:** Beginner → Intermediate
> **Prerequisites:** Module 01 (wrote a basic Dockerfile)
> **Time:** 60–90 minutes
> **Last Updated:** 2026-05-21
> **What You'll Learn:** Multi-stage builds, BuildKit features, secret injection, build caching, tiny secure images

---

## Introduction

**What:** Advanced Dockerfile techniques that are standard in production 2025.

**Why:** A naive Dockerfile creates images that are 1GB+, slow to build, and full of security vulnerabilities. These techniques shrink images to under 50MB, make builds 10x faster, and keep secrets out of images.

**Real-world impact:**
```
Before optimization:  Image = 1.2 GB, Build time = 4 minutes
After optimization:   Image =  52 MB, Build time = 40 seconds (cached)
```

---

## Part 1: Multi-Stage Builds

### The Problem with Single-Stage Builds

When you build a Go or Java app, you need compilers and build tools. But you don't want those 500MB compilers in your final production image — they're security risks and dead weight.

```
Single-stage build problem:
┌──────────────────────────────┐
│ golang compiler  (400MB)     │  ← Only needed at BUILD time
│ source code      (5MB)       │  ← Only needed at BUILD time
│ test frameworks  (50MB)      │  ← Only needed at BUILD time
│ your compiled binary (8MB)   │  ← This is the ONLY thing needed at RUNTIME
└──────────────────────────────┘
Total: ~463MB — when you only need 8MB!
```

### Multi-Stage Builds — The Solution

```dockerfile
# ─────────────────────────────────────────────────
# Multi-Stage Dockerfile for a Go Application
# ─────────────────────────────────────────────────

# ── STAGE 1: Builder ──────────────────────────────
# 'AS builder' gives this stage a name we can reference later
# This stage has all build tools and compilers
FROM golang:1.22-alpine AS builder

# Set working directory for the build stage
WORKDIR /build

# Copy dependency files first (cache optimization)
# Go modules: go.mod defines dependencies like requirements.txt
COPY go.mod go.sum ./

# Download dependencies — cached if go.mod/go.sum don't change
RUN go mod download

# Copy source code
COPY . .

# Build the binary
# CGO_ENABLED=0: Static binary (no C dependencies)
# GOOS=linux: Build for Linux (needed even on Mac/Windows for containers)
# -ldflags="-w -s": Strip debug info → smaller binary
# -o /build/app: Output binary path
RUN CGO_ENABLED=0 GOOS=linux go build \
    -ldflags="-w -s" \
    -o /build/app \
    ./cmd/main.go

# ── STAGE 2: Runtime ──────────────────────────────
# 'scratch' = empty image — literally nothing but your binary!
# Why: Maximum security — no shell, no tools, no attack surface
# Alternative: 'gcr.io/distroless/static' (adds CA certs, timezone data)
FROM scratch

# Copy ONLY the compiled binary from the builder stage
# '--from=builder' references our named build stage
COPY --from=builder /build/app /app

# Copy CA certificates (needed for HTTPS connections)
# The 'builder' alpine image has these; scratch does not
COPY --from=builder /etc/ssl/certs/ca-certificates.crt \
    /etc/ssl/certs/

# The final image contains:
# - /app (the compiled binary)  ← ~8MB
# - /etc/ssl/certs/             ← ~300KB
# Total: ~8.3MB vs 463MB!

EXPOSE 8080

# Run the binary directly (no shell needed in scratch image)
ENTRYPOINT ["/app"]
```

---

### Multi-Stage Build for Python

Python can also benefit from multi-stage builds:

```dockerfile
# ─────────────────────────────────────────────────
# Multi-Stage Dockerfile for Python FastAPI App
# ─────────────────────────────────────────────────

# ── STAGE 1: Build virtual environment ────────────
FROM python:3.12-slim AS python-builder

WORKDIR /build

# Install build dependencies (not needed in final image)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
# 'rm -rf /var/lib/apt/lists/*': Delete apt cache in the SAME layer
# Why: Each RUN creates a layer; cleaning in a separate RUN layer
# still keeps the cache in the earlier layer. Clean in same RUN!

# Create a virtual environment in /venv
RUN python -m venv /venv

# Activate venv for subsequent commands
ENV PATH="/venv/bin:$PATH"

# Install Python dependencies into the venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── STAGE 2: Production Runtime ───────────────────
FROM python:3.12-slim AS runtime

# Copy the pre-built virtual environment from builder
# Only the installed packages, not build tools
COPY --from=python-builder /venv /venv

# Activate the venv in the runtime stage
ENV PATH="/venv/bin:$PATH"

WORKDIR /app

# Create a non-root user for security
# Why: Running as root inside container is a security risk
# If the container is compromised, attacker gets root on the container
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

# Copy application code
COPY --chown=appuser:appgroup . .

# Switch to non-root user for all subsequent commands
USER appuser

EXPOSE 8000

# Run FastAPI with uvicorn
# --host 0.0.0.0: Accept connections from outside container
# --workers 4: Multiple worker processes
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Size comparison:**
```bash
# Single-stage Python image
docker build -t python-single -f Dockerfile.single .
docker images python-single
# python-single    latest    a1b2c3   1.2GB  ← includes gcc, libpq-dev, build tools

# Multi-stage Python image
docker build -t python-multi .
docker images python-multi
# python-multi     latest    d4e5f6   185MB  ← production only, no build tools
```

---

## Part 2: BuildKit — The Modern Build Engine

**What is BuildKit?**
BuildKit is Docker's advanced build engine (default since Docker 23+). It offers:
- **Parallel** stage execution
- **Better caching** with `--mount=type=cache`
- **Secure secret injection** with `--mount=type=secret`
- **SSH forwarding** for private repos

### Enable BuildKit (older Docker versions)

```bash
# If using Docker < 23, enable BuildKit manually
export DOCKER_BUILDKIT=1

# Or set it permanently in daemon.json
# /etc/docker/daemon.json:
{
  "features": { "buildkit": true }
}
```

### Cache Mounts — Persistent Build Cache

This is one of BuildKit's most powerful features. Without it, `pip install` re-downloads packages from scratch every build. With cache mounts, the downloaded packages are stored between builds.

```dockerfile
# Syntax directive tells BuildKit to use the latest frontend
# (enables all new BuildKit features)
# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# --mount=type=cache,target=/root/.cache/pip
# What: Mounts a persistent cache directory at /root/.cache/pip
# Why: pip saves downloaded packages here. On next build, they're
#      reused from cache instead of downloading again.
# Effect: pip install goes from 45s → 2s on repeat builds!
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY . .
CMD ["python", "app.py"]
```

**For Node.js:**
```dockerfile
# syntax=docker/dockerfile:1

FROM node:22-alpine

WORKDIR /app

COPY package*.json .

# Cache the npm module downloads between builds
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline
# 'npm ci' = clean install (uses exact versions from package-lock.json)
# '--prefer-offline': Use cached packages when available

COPY . .
CMD ["node", "server.js"]
```

---

### Secret Injection — No Secrets in Image Layers!

**The Problem:**
```dockerfile
# ❌ NEVER DO THIS — the secret is visible in every layer forever!
ENV GITHUB_TOKEN=ghp_secret123
RUN pip install git+https://${GITHUB_TOKEN}@github.com/myorg/private-pkg.git
```

Even if you delete the ENV in a later layer, `docker history` reveals it:
```bash
docker history myimage  # Shows: ENV GITHUB_TOKEN=ghp_secret123
```

**The Solution — BuildKit Secrets:**
```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# --mount=type=secret,id=pip_token
# What: Temporarily mounts the secret at /run/secrets/pip_token
# Why: Secret is NEVER stored in any image layer
# It only exists during this RUN command, then disappears
RUN --mount=type=secret,id=pip_token \
    PIP_INDEX_URL=$(cat /run/secrets/pip_token) \
    pip install -r requirements.txt

COPY . .
CMD ["python", "app.py"]
```

**Build with the secret:**
```bash
# Pass the secret at build time — never goes into the image!
docker build \
  --secret id=pip_token,src=.secrets/pip_config \
  -t my-private-app .

# Verify: secret is NOT in the image
docker history my-private-app  # pip_token not visible anywhere!
```

---

### SSH Forwarding — For Private Git Repos

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Install git and openssh for SSH connections
RUN apt-get update && apt-get install -y git openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# --mount=type=ssh: Forward your SSH agent to the build
# What: Uses your local SSH keys temporarily during the build
# Why: Install packages from private GitHub repos without embedding keys
RUN --mount=type=ssh \
    pip install git+ssh://git@github.com/myorg/private-lib.git
```

```bash
# Start SSH agent and add your key
eval $(ssh-agent)
ssh-add ~/.ssh/id_rsa

# Build with SSH forwarding
docker build --ssh default -t my-app .
```

---

## Part 3: Distroless and Alpine Images

### Image Size Comparison

```
Image sizes for a Python app:
FROM python:3.12                    →  1.0 GB  (Debian full)
FROM python:3.12-slim               →  130 MB  (Debian slim, no extras)
FROM python:3.12-alpine             →   50 MB  (Alpine Linux base)
FROM gcr.io/distroless/python3      →   45 MB  (No shell, minimal OS)
FROM scratch (Go binary)            →    8 MB  (Zero OS)
```

### When to Use Which

| Base Image | Use When | Pros | Cons |
|-----------|---------|------|------|
| `python:3.12` | Development, debugging | All tools available | Very large |
| `python:3.12-slim` | General production | Good balance | Still has shell |
| `python:3.12-alpine` | Small production images | Smallest Python | musl libc, some pkg issues |
| `distroless/python3` | Maximum security | No shell, tiny | Hard to debug |
| `scratch` | Compiled binaries (Go, Rust) | Absolute minimum | Only compiled apps |

**Alpine Gotcha:**
```dockerfile
# Alpine uses musl libc instead of glibc
# Most Python packages work fine, but some C extensions may fail
# If you get compilation errors with Alpine, switch to 'slim'
FROM python:3.12-alpine

# Install build deps needed for packages with C extensions
RUN apk add --no-cache gcc musl-dev libffi-dev
```

---

## Part 4: Build Arguments

```dockerfile
# ARG: Build-time variables (not available at runtime, unlike ENV)
# Why: Customize builds without multiple Dockerfiles
ARG PYTHON_VERSION=3.12
ARG APP_VERSION=1.0.0
ARG BUILD_DATE

FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# LABEL: Add metadata to the image
# Why: Useful for image management, CI systems, and auditing
LABEL version="${APP_VERSION}" \
      maintainer="yourname@example.com" \
      build-date="${BUILD_DATE}" \
      description="My FastAPI application"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Note: ARG values declared before FROM are NOT available after FROM
# Redeclare them after FROM to use in the image:
ARG APP_VERSION
ENV APP_VERSION=${APP_VERSION}
# This makes APP_VERSION available at runtime too

CMD ["python", "app.py"]
```

```bash
# Pass build arguments at build time
docker build \
  --build-arg PYTHON_VERSION=3.11 \
  --build-arg APP_VERSION=2.1.0 \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  -t my-app:2.1.0 .
```

---

## Part 5: Docker Build Checks (New in 2025)

Docker Desktop now includes **Build Checks** — automatic validation of your Dockerfile before building.

```bash
# Check your Dockerfile for issues WITHOUT actually building
docker build --check .

# Sample output:
# [+] Building 0.0s (0/0) docker:default
# Check: JSONArgsRecommended
# Info: JSON form is recommended for CMD and ENTRYPOINT
# Hint: Change CMD python app.py → CMD ["python", "app.py"]
#
# Check: NoHealthcheck
# Info: No HEALTHCHECK added
# Hint: Add HEALTHCHECK for production images
```

These checks catch issues like:
- Non-JSON CMD/ENTRYPOINT
- Missing HEALTHCHECK
- Running as root
- Missing .dockerignore
- Inefficient layer ordering

---

## Full Example: Production-Ready Dockerfile

Here's a complete, production-grade Dockerfile incorporating all the techniques:

```dockerfile
# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────
# Production Dockerfile for Python FastAPI App
# Features: Multi-stage, BuildKit cache, non-root user, health check
# ─────────────────────────────────────────────────────────────────

# Build arguments — can be overridden at build time
ARG PYTHON_VERSION=3.12

# ── STAGE 1: Dependency Builder ───────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

# Install system build dependencies for C-extension packages
# Grouped in one RUN to minimize layers and clean up in same layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment for clean dependency management
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies with BuildKit cache mount
# The pip cache persists between builds, speeding up reinstalls
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# ── STAGE 2: Production Runtime ───────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS runtime

# Add image metadata for tracking and auditing
ARG APP_VERSION=1.0.0
ARG BUILD_DATE
LABEL version="${APP_VERSION}" \
      build-date="${BUILD_DATE}" \
      description="FastAPI production image"

WORKDIR /app

# Install only runtime system dependencies (not build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the virtual environment (no build tools from builder)
COPY --from=builder /opt/venv /opt/venv

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Security: Create non-root user and group
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home \
    --shell /sbin/nologin appuser

# Copy application code with correct ownership
COPY --chown=appuser:appgroup . .

# Runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000

# Switch to non-root user BEFORE exposing ports and running
USER appuser

EXPOSE 8000

# Health check: verify app responds to requests
# --interval=30s: Check every 30 seconds
# --timeout=10s: Wait up to 10s for a response
# --start-period=5s: Grace period before first check (app startup time)
# --retries=3: Mark unhealthy after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Build Script

```bash
#!/bin/bash
# build.sh — consistent, repeatable build script

set -e  # Exit on any error

APP_NAME="my-fastapi-app"
VERSION=$(git describe --tags --always)     # Use git tag as version
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)  # ISO 8601 timestamp

echo "Building $APP_NAME:$VERSION..."

docker build \
  --build-arg APP_VERSION="$VERSION" \
  --build-arg BUILD_DATE="$BUILD_DATE" \
  --tag "$APP_NAME:$VERSION" \
  --tag "$APP_NAME:latest" \
  .

echo "Build complete! Image: $APP_NAME:$VERSION"
docker images "$APP_NAME"
```

---

## Best Practices Summary

**✅ DO:**
- Use multi-stage builds — Why: Drastically smaller, more secure production images
- Pin base image versions — Why: Reproducible, prevents surprise breakage
- Add HEALTHCHECK — Why: Orchestrators and `docker compose` depend on it
- Run as non-root user — Why: Limits damage if container is compromised
- Use `--mount=type=cache` for package managers — Why: 10x faster incremental builds
- Add LABEL metadata — Why: Traceability and image management

**❌ DON'T:**
- Put secrets in ENV/ARG — Why bad: Visible in `docker history` | Fix: Use `--mount=type=secret`
- Install unnecessary packages in final stage — Why bad: Increases attack surface | Fix: Multi-stage, install only runtime deps
- Use `apt-get update` in a separate RUN from install — Why bad: Cache inconsistency | Fix: `RUN apt-get update && apt-get install -y pkg && rm -rf /var/lib/apt/lists/*`

---

## Practice Exercises

**Exercise 1: Convert Single-Stage to Multi-Stage**

Take this single-stage Dockerfile and convert it to multi-stage:
```dockerfile
FROM node:22
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build  # Compiles TypeScript → JavaScript in /app/dist
CMD ["node", "dist/server.js"]
```

<details>
<summary>Solution</summary>

```dockerfile
# Stage 1: Build TypeScript
FROM node:22-alpine AS builder
WORKDIR /build
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build  # Produces /build/dist/

# Stage 2: Production (only the compiled JS)
FROM node:22-alpine AS runtime
WORKDIR /app
COPY package*.json .
RUN npm ci --omit=dev  # Install only production dependencies
COPY --from=builder /build/dist ./dist
USER node  # node:alpine includes a 'node' user
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

**Why it works:** Build tools and TypeScript source code stay in the builder stage. The runtime stage is much smaller because it only has compiled JavaScript and production dependencies.
</details>

---

## What's Next

**Learned:** ✅ Multi-stage builds, ✅ BuildKit cache mounts, ✅ Secret injection, ✅ Non-root users, ✅ Build checks

**Next:** Module 03: Networking & Volumes — How containers communicate and persist data

**Check:** Can you build a multi-stage Python image under 200MB?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-21 | Initial version — covers BuildKit, multi-stage, distroless |
