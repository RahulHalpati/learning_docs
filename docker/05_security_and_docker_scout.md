# 05: Security & Docker Scout — Scanning, Secrets & Hardening

> **Level:** Intermediate
> **Prerequisites:** Module 04 (Docker Compose)
> **Time:** 60–90 minutes
> **Last Updated:** 2026-05-21
> **What You'll Learn:** Docker Scout CVE scanning, secrets management, container hardening, non-root users, read-only filesystems

---

## Introduction

**What:** Docker security is about protecting your images, containers, and data from vulnerabilities and unauthorized access.

**Why:** A container running as root with vulnerable packages is a disaster waiting to happen. Docker provides built-in tools (Docker Scout) and patterns (non-root users, secrets management) to secure your entire pipeline.

**The security layers:**
```
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Runtime Security  (non-root, read-only fs)    │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Container Hardening  (capabilities, limits)   │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Secrets Management  (no hardcoded secrets)    │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Image Security  (scanning, minimal base)      │
└─────────────────────────────────────────────────────────┘
```

---

## Part 1: Docker Scout — Vulnerability Scanning

### What is Docker Scout?

Docker Scout is Docker's built-in security tool. It:
- Scans images for **known CVEs** (Common Vulnerabilities and Exposures)
- Generates **SBOM** (Software Bill of Materials — a list of all packages)
- Provides **fix recommendations** (e.g., "update this package")
- Integrates with **CI/CD pipelines** to block insecure builds

### Install Docker Scout

```bash
# Scout comes with Docker Desktop. For Linux Docker Engine:
curl -fsSL https://raw.githubusercontent.com/docker/scout-cli/main/install.sh | sh
# This installs the 'docker scout' CLI plugin

# Verify installation
docker scout version
```

### Scanning an Image

```bash
# Quick scan: show summary of vulnerabilities
docker scout quickview my-app:1.0

# Output:
# ✓ SBOM of image already cached, 234 packages indexed
# ✗ Detected 12 vulnerabilities
#   ├── 2 critical
#   ├── 4 high
#   ├── 4 medium
#   └── 2 low

# Detailed CVE report
docker scout cves my-app:1.0

# Filter by severity (only show critical)
docker scout cves --only-severity critical my-app:1.0

# Output:
# CVE-2024-1234  CRITICAL  libssl3  3.1.2 → fixed in 3.1.4
# CVE-2024-5678  CRITICAL  python   3.12.0 → fixed in 3.12.3
# Recommendation: Update base image to python:3.12.3-slim

# Recommendations for base image updates
docker scout recommendations my-app:1.0

# Output:
# Current:    python:3.12.0-slim → 12 CVEs (2 critical)
# Suggested:  python:3.12.5-slim → 0 CVEs  ✅  (-23MB smaller too!)
```

### Compare Two Images

```bash
# Compare security between image versions (before vs after update)
docker scout compare \
  --to myapp:1.0 \
  myapp:1.1

# Output:
# ✓ 2 critical vulnerabilities FIXED
# ✓ 4 high vulnerabilities FIXED  
# + 1 new medium vulnerability
# Net improvement: 5 vulnerabilities reduced
```

### Scan Before Push (CI Practice)

```bash
# Best practice: scan image BEFORE pushing to registry
docker build -t myapp:latest .
docker scout cves --exit-code myapp:latest
# --exit-code: Returns non-zero exit code if vulnerabilities found
# Use this in CI to FAIL the pipeline on critical CVEs!

# Only fail on critical/high, allow medium/low
docker scout cves \
  --only-severity critical,high \
  --exit-code \
  myapp:latest
```

---

## Part 2: Secrets Management

### The Problem with ENV Secrets

```dockerfile
# ❌ NEVER DO THIS — secrets visible in 'docker inspect' and logs
ENV DATABASE_PASSWORD=supersecret123
ENV API_KEY=sk-abc123def456
```

```bash
# Anyone with access to the host can see it:
docker inspect myapp | grep -i password
# "DATABASE_PASSWORD": "supersecret123"  ← exposed!
```

### Docker Secrets (for Docker Swarm)

```bash
# Create a secret (stored encrypted in Swarm's Raft store)
echo "my-super-secret-password" | docker secret create db_password -

# Use in a Swarm service
docker service create \
  --name my-api \
  --secret db_password \
  my-api:1.0
# Secret appears at /run/secrets/db_password inside the container
```

**Access in your application:**
```python
# app.py — read secret from file (Docker Swarm/Compose secrets)

import os

def get_secret(secret_name: str) -> str:
    """
    Read a Docker secret from /run/secrets/
    
    What: Secrets are mounted as files, not env vars
    Why: Safer than env vars — not visible in docker inspect/history
    
    Args:
        secret_name (str): Name of the secret file
    
    Returns:
        str: The secret value, stripped of whitespace
    
    Raises:
        FileNotFoundError: If secret doesn't exist
    """
    secret_path = f"/run/secrets/{secret_name}"
    
    if os.path.exists(secret_path):
        # Read from Docker secret file
        with open(secret_path, 'r') as f:
            return f.read().strip()
    
    # Fallback to environment variable (for local dev without Swarm)
    env_value = os.getenv(secret_name.upper())
    if env_value:
        return env_value
    
    raise FileNotFoundError(f"Secret '{secret_name}' not found")

# Usage
db_password = get_secret("db_password")  # Reads /run/secrets/db_password
```

### Secrets in Docker Compose

```yaml
# compose.yaml with secrets support
services:
  api:
    image: my-api:1.0
    secrets:
      - db_password      # Mounted at /run/secrets/db_password
      - api_key          # Mounted at /run/secrets/api_key
    environment:
      # Reference by file path, not value (app reads the file)
      - DATABASE_URL=postgresql://user:$(cat /run/secrets/db_password)@db/mydb
    
  db:
    image: postgres:16-alpine
    secrets:
      - db_password
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
      # PostgreSQL supports _FILE suffix for reading from file!

# Declare secrets at top level
secrets:
  db_password:
    file: ./secrets/db_password.txt   # Read from local file
  api_key:
    file: ./secrets/api_key.txt

# Never commit ./secrets/ to git! Add to .gitignore
```

---

## Part 3: Running Containers as Non-Root

### Why Root is Dangerous

```bash
# By default, most containers run as root
docker run --rm alpine whoami
# root   ← This is dangerous!

# If the container is compromised and can break out,
# the attacker has ROOT access to the host!
```

### Creating a Non-Root User in Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

FROM python:3.12-slim

WORKDIR /app

# Install dependencies as root (needed for system packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Create non-root user BEFORE copying app code ──

# Create a system group (no login shell, no home dir)
# --gid 1001: Specific ID for predictability across containers
RUN groupadd --system --gid 1001 appgroup

# Create a system user (no login, no password, no home directory)
# --uid 1001: Specific UID
# --gid appgroup: Assign to our group
# --no-create-home: Don't create /home/appuser
# --shell /sbin/nologin: Can't log in interactively
RUN useradd --system --uid 1001 --gid appgroup \
    --no-create-home --shell /sbin/nologin \
    appuser

# Copy app code with correct ownership from the start
# --chown=appuser:appgroup: The copied files belong to appuser
COPY --chown=appuser:appgroup . .

# ── Switch to non-root user ──
# Everything below this runs as appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Verify the container runs as non-root
docker build -t secure-app .
docker run --rm secure-app whoami
# appuser  ← No longer root!
```

---

## Part 4: Container Hardening

### Read-Only Filesystem

```bash
# Run container with read-only root filesystem
docker run -d \
  --read-only \
  --tmpfs /tmp \        # Allow writes only to /tmp (in memory)
  --tmpfs /run \        # Allow writes to /run (PIDs, sockets)
  my-app:1.0

# If the app is compromised, attacker CANNOT write malware to the filesystem!
```

```yaml
# In compose.yaml:
services:
  api:
    image: my-api:1.0
    read_only: true               # Read-only root filesystem
    tmpfs:
      - /tmp                       # Temp files (in memory)
      - /run                       # Runtime files
    volumes:
      - uploads:/app/uploads       # Named volume for uploads (writable)
```

### Linux Capabilities

Containers run with a default set of Linux capabilities. You can drop them all and add back only what's needed:

```bash
# Drop ALL capabilities, add back only what the app needs
docker run -d \
  --cap-drop ALL \         # Drop everything by default
  --cap-add NET_BIND_SERVICE \   # Allow binding to ports < 1024
  my-nginx:1.0

# Why: If a vulnerability is exploited, attacker has minimal privileges
```

```yaml
# compose.yaml
services:
  nginx:
    image: nginx:1.27-alpine
    cap_drop:
      - ALL                        # Drop all capabilities
    cap_add:
      - NET_BIND_SERVICE           # Re-add: bind to port 80
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
      - /var/cache/nginx
```

### Resource Limits

```yaml
services:
  api:
    image: my-api:1.0
    deploy:
      resources:
        limits:
          cpus: "0.50"             # Max 50% of 1 CPU core
          memory: 256M             # Max 256MB RAM
        reservations:
          cpus: "0.25"             # Guaranteed minimum
          memory: 128M             # Guaranteed minimum RAM
    # Without limits: one container can consume ALL host resources!
    # 'limits': Hard cap — container killed if exceeded
    # 'reservations': Minimum guaranteed
```

---

## Part 5: Image Security Best Practices

### Use Minimal Base Images

```dockerfile
# Priority order (most to least secure):
# 1. scratch              - For compiled Go/Rust binaries (zero OS)
# 2. distroless           - Minimal runtime (no shell, no package manager)
# 3. alpine               - Minimal Linux (4MB base, has shell)
# 4. debian:slim / *-slim - Stripped Debian (still has shell)
# 5. ubuntu / debian      - Full OS (avoid if possible)

# For Python — use distroless (Google's minimal image):
FROM python:3.12-slim AS builder
# ... install deps into /venv ...

FROM gcr.io/distroless/python3-debian12 AS runtime
COPY --from=builder /venv /venv
COPY --from=builder /app /app
ENV PATH="/venv/bin:$PATH"
CMD ["/app/main.py"]
# This image has NO shell — attacker can't 'exec' into it!
```

### Never Store Secrets in Images

```dockerfile
# ❌ SECRET IN IMAGE LAYER — visible in docker history FOREVER
RUN pip install --index-url https://${TOKEN}@pypi.example.com/simple/ my-private-pkg

# ✅ USE BUILDKIT SECRETS — never stored in any layer
RUN --mount=type=secret,id=pypi_token \
    pip install \
      --index-url https://$(cat /run/secrets/pypi_token)@pypi.example.com/simple/ \
      my-private-pkg
```

### Sign Your Images (Docker Content Trust)

```bash
# Enable Docker Content Trust (DCT)
# Requires image signing before push
export DOCKER_CONTENT_TRUST=1

# Now docker push/pull verifies signatures
docker push myregistry.io/my-app:1.0
# Docker prompts for signing keys if not already set up
# Consumers can verify the image hasn't been tampered with

# Verify an image signature
docker trust inspect myregistry.io/my-app:1.0
```

---

## Part 6: CI/CD Security Gates with GitHub Actions

Integrate Docker Scout into your CI pipeline to automatically block insecure images:

```yaml
# .github/workflows/docker-security.yml
name: Build & Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-scan:
    runs-on: ubuntu-latest
    
    # Required for pushing to GitHub Container Registry
    permissions:
      contents: read
      packages: write
      security-events: write   # For uploading SARIF results

    steps:
      # Step 1: Check out code
      - name: Checkout code
        uses: actions/checkout@v4

      # Step 2: Set up BuildKit (enables advanced build features)
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      # Step 3: Log in to container registry
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # Step 4: Build and push the image
      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha     # Use GitHub Actions cache
          cache-to: type=gha,mode=max

      # Step 5: Run Docker Scout security scan
      - name: Docker Scout CVE Scan
        uses: docker/scout-action@v1
        with:
          command: cves
          image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          only-severities: critical,high    # Only fail on critical/high
          exit-code: true                   # Fail the job if CVEs found
          # sarif-file: sarif.output.json  # Save SARIF report

      # Step 6: Get base image recommendations
      - name: Docker Scout Recommendations
        uses: docker/scout-action@v1
        with:
          command: recommendations
          image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
        if: always()  # Run even if CVE scan fails
```

---

## Part 7: Security Checklist

Use this checklist before any production deployment:

```bash
# Check 1: Does the container run as non-root?
docker inspect my-app | jq '.[0].Config.User'
# Should NOT be empty or "root"

# Check 2: Are ports unnecessarily exposed?
docker inspect my-app | jq '.[0].HostConfig.PortBindings'
# Only expected ports should be listed

# Check 3: Is the filesystem read-only?
docker inspect my-app | jq '.[0].HostConfig.ReadonlyRootfs'
# Ideally true

# Check 4: Are capabilities minimized?
docker inspect my-app | jq '.[0].HostConfig.CapAdd'
# Should be minimal or null

# Check 5: Scan for CVEs
docker scout cves my-app:1.0 --only-severity critical,high
# Should return 0 critical/high CVEs

# Check 6: Any secrets in environment variables?
docker inspect my-app | jq '.[0].Config.Env'
# Should not contain passwords, tokens, keys
```

---

## Common Mistakes

**Mistake 1: Running as root (default)**

```dockerfile
# ❌ WRONG — default, runs as root
FROM python:3.12-slim
CMD ["python", "app.py"]

# ✅ CORRECT — explicit non-root user
FROM python:3.12-slim
RUN useradd --system --uid 1001 appuser
USER appuser
CMD ["python", "app.py"]
```

**Mistake 2: Copying secrets into images**

```dockerfile
# ❌ WRONG — .env may contain API keys!
COPY . .   # Copies .env too if no .dockerignore

# ✅ CORRECT — exclude secrets via .dockerignore
# .dockerignore:
# .env
# *.key
# secrets/
```

**Mistake 3: Using 'latest' in production**

```dockerfile
# ❌ WRONG — 'latest' changes, may introduce vulnerabilities
FROM python:latest

# ✅ CORRECT — pinned version, known security state
FROM python:3.12.5-slim
```

---

## Practice Exercises

**Exercise 1: Harden an Existing Dockerfile**

Take this insecure Dockerfile and apply all security improvements:

```dockerfile
# Before: Insecure Dockerfile
FROM ubuntu:latest
RUN apt-get update && apt-get install -y python3 python3-pip
COPY . .
ENV DB_PASSWORD=hardcoded123
RUN pip install -r requirements.txt
CMD python3 app.py
```

<details>
<summary>Solution</summary>

```dockerfile
# syntax=docker/dockerfile:1

# 1. Pin the base image version
FROM python:3.12.5-slim AS builder

WORKDIR /build

# 2. Install deps in build stage (not final image)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt --target=/install

# 3. Production stage — minimal image
FROM python:3.12.5-slim AS runtime

WORKDIR /app

# 4. Copy only installed packages
COPY --from=builder /install /app/deps
ENV PYTHONPATH=/app/deps

# 5. Create non-root user
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup \
    --no-create-home --shell /sbin/nologin appuser

# 6. Copy code with correct ownership
COPY --chown=appuser:appgroup . .

# 7. No ENV for secrets — use Docker secrets or external vault
# (Remove DB_PASSWORD from Dockerfile entirely)

# 8. Switch to non-root
USER appuser

EXPOSE 8000

# 9. Exec form CMD
CMD ["python3", "app.py"]
```

Key fixes:
1. Pinned `python:3.12.5-slim` (not ubuntu:latest + manual install)
2. Multi-stage to exclude build tools from final image
3. Non-root user `appuser`
4. Removed hardcoded `DB_PASSWORD`
5. Exec form CMD

</details>

---

## Best Practices Summary

**✅ DO:**
- Run Docker Scout scans in CI — Why: Catch CVEs before production
- Run as non-root user — Why: Limits impact of container escape
- Use minimal base images (alpine/slim/distroless) — Why: Smaller attack surface
- Use `--read-only` where possible — Why: Prevents filesystem tampering
- Use `.dockerignore` — Why: Prevents secrets being copied into image
- Pin image versions — Why: Known, auditable security state

**❌ DON'T:**
- Store secrets in ENV/ARG/COPY — Why bad: Visible in image layers | Fix: Docker secrets or BuildKit `--mount=type=secret`
- Use `latest` tag in production — Why bad: Unpredictable, unknown vulnerabilities | Fix: Pin exact version
- Skip vulnerability scanning — Why bad: Unknown CVEs in production | Fix: `docker scout cves` in CI
- Run as root — Why bad: Container escape → host compromise | Fix: `USER appuser` in Dockerfile

---

## What's Next

**Learned:** ✅ Docker Scout scanning, ✅ Secrets management, ✅ Non-root users, ✅ Read-only filesystem, ✅ Resource limits, ✅ CI security gates

**Next:** Module 06: CI/CD & Production — GitHub Actions pipelines, health monitoring, logging, Compose Bridge to Kubernetes

**Check:** Can you scan an image with Docker Scout and fix the critical CVEs it finds?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-21 | Initial version — Docker Scout, BuildKit secrets, 2025 security patterns |
