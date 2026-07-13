# 03: Networking & Volumes — Container Communication & Persistent Data

> **Level:** Beginner → Intermediate
> **Prerequisites:** Module 02 (Dockerfile basics)
> **Time:** 60–90 minutes
> **Last Updated:** 2026-05-21
> **What You'll Learn:** Docker networks, container DNS, volume types, persistent databases, bind mounts

---

## Introduction

**What:** Networking lets containers talk to each other. Volumes let data survive container restarts.

**Why:** In the real world, your app isn't alone. It talks to databases, caches, message queues. And when a container restarts, you don't want the database to lose all its data.

**Analogy:**
- **Networks** = Office hallways. Containers are rooms. A hallway lets rooms communicate.
- **Volumes** = USB drives. You can plug them into a container. When the container is deleted, the USB drive (data) remains.

---

## Part 1: Docker Networking

### The Default Networks

Docker comes with three built-in networks:

```bash
# List all networks
docker network ls

# Output:
# NETWORK ID     NAME      DRIVER    SCOPE
# a1b2c3d4e5f6   bridge    bridge    local   ← default for containers
# b2c3d4e5f6a7   host      host      local   ← shares host network stack
# c3d4e5f6a7b8   none      null      local   ← no networking at all
```

**The default `bridge` network (avoid in production!):**
```bash
# When you run a container without specifying a network,
# it joins the default 'bridge' network
docker run -d --name app1 nginx
docker run -d --name app2 nginx

# Try to ping app2 from app1
docker exec app1 ping app2
# ERROR: Name or service not known
# WHY: The default bridge network does NOT provide DNS!
# Containers can only communicate by IP address, which changes!
```

---

### User-Defined Bridge Networks (The Right Way)

Creating your own network gives you **automatic DNS** — containers find each other by name, not IP.

```bash
# Create a custom network
# 'bridge' driver = software-defined network on a single host
docker network create my-app-network

# Inspect the network
docker network inspect my-app-network
# Shows: subnet, gateway, connected containers

# Run containers on the custom network
docker run -d \
  --name web-server \
  --network my-app-network \
  nginx

docker run -d \
  --name api-server \
  --network my-app-network \
  my-api:1.0

# Now containers can reach each other by NAME!
docker exec api-server ping web-server
# WORKS! Docker provides DNS: 'web-server' resolves to its IP

docker exec api-server curl http://web-server:80
# WORKS! No hardcoded IPs needed
```

**How Docker DNS works:**
```
┌─────────────────────────────────────────────────────┐
│                 my-app-network                       │
│                                                      │
│  ┌──────────────┐      DNS lookup: "db"              │
│  │  web-server  │ ──────────────────────────────┐    │
│  │  172.20.0.2  │                               ↓    │
│  └──────────────┘  ┌──────────────────────────────┐  │
│                    │  Docker Embedded DNS Server   │  │
│  ┌──────────────┐  │  db → 172.20.0.3             │  │
│  │  db          │  └──────────────────────────────┘  │
│  │  172.20.0.3  │                                     │
│  └──────────────┘                                     │
└─────────────────────────────────────────────────────┘
```

---

### Port Publishing

```bash
# -p HOST_PORT:CONTAINER_PORT
# Map host's port 8080 to container's port 80
docker run -d -p 8080:80 nginx

# Bind to a specific interface (more secure)
# Only accessible from localhost, not external networks
docker run -d -p 127.0.0.1:8080:80 nginx

# Let Docker choose a random available host port
docker run -d -p 80 nginx
docker port <container-id>  # Shows: 80/tcp -> 0.0.0.0:32768

# Expose multiple ports
docker run -d -p 8080:80 -p 443:443 nginx
```

**⚠️ Important:** Only expose ports that MUST be public. Internal services (databases, internal APIs) should NOT be exposed with `-p`. Let them communicate through the Docker network.

```bash
# ✅ Correct setup:
# Web server: exposed to host (users access it)
# Database: NOT exposed (only web-server container accesses it)

docker network create app-net

docker run -d \
  --name db \
  --network app-net \
  -e POSTGRES_PASSWORD=secret \
  postgres:16-alpine
  # No -p flag! Database is not accessible from host

docker run -d \
  --name web \
  --network app-net \
  -p 8080:8080 \
  -e DATABASE_URL=postgresql://postgres:secret@db:5432/mydb \
  my-web-app:1.0
  # web can reach 'db' via Docker DNS
  # Only port 8080 is exposed to host
```

---

### Network Drivers

| Driver | Use Case | How it works |
|--------|---------|--------------|
| `bridge` | Default, single-host apps | Software bridge, isolated network |
| `host` | High performance, no isolation | Shares host's network stack directly |
| `overlay` | Multi-host (Docker Swarm/K8s) | Connect containers across multiple machines |
| `macvlan` | Legacy app needs MAC address | Assign real MAC address to container |
| `none` | Complete isolation | No network at all |

```bash
# Example: host network (container shares host ports directly)
# WARNING: Removes network isolation!
docker run -d --network host nginx
# Nginx now runs on host's port 80 directly
# No -p mapping needed (or allowed)
```

---

### Connecting Containers to Multiple Networks

```bash
# A container can be on multiple networks
# Use case: API server talks to both frontend and backend networks

docker network create frontend-net
docker network create backend-net

# API: bridge between frontend and backend
docker run -d --name api \
  --network frontend-net \
  my-api:1.0

docker network connect backend-net api
# Now 'api' is on both networks

docker run -d --name web \
  --network frontend-net \
  my-web:1.0
# 'web' can reach 'api' (both on frontend-net)

docker run -d --name db \
  --network backend-net \
  postgres:16-alpine
# 'db' can reach 'api' (both on backend-net)
# 'db' CANNOT reach 'web' (different networks) ← security!
```

```mermaid
graph TD
    WEB["🌐 web (frontend-net)"]
    API["⚡ api (frontend-net + backend-net)"]
    DB["🗃️ db (backend-net)"]

    WEB <-->|frontend-net| API
    API <-->|backend-net| DB
    WEB -. "✗ cannot reach" .-> DB
```

---

## Part 2: Docker Volumes

### Why Containers Need Volumes

Containers are **ephemeral** — when you delete a container, everything inside it is gone:

```bash
# Problem: Data lost when container is deleted
docker run -d --name test-db postgres:16-alpine
# Create some data in the database...
docker rm -f test-db       # Oops! All database data gone!
docker run -d --name test-db postgres:16-alpine
# Brand new empty database 😢
```

**Volumes solve this** — they store data outside the container lifecycle.

---

### Volume Types

```
┌────────────────────────────────────────────────────────────┐
│                    Storage Options                          │
├─────────────────┬──────────────────────┬───────────────────┤
│   Named Volume  │    Bind Mount        │    tmpfs Mount    │
├─────────────────┼──────────────────────┼───────────────────┤
│ Managed by      │ Specific host path   │ In memory only    │
│ Docker          │ (e.g., ./data:/data) │ (no disk write)   │
│                 │                      │                    │
│ /var/lib/docker │ ~/myproject:/app     │ RAM only           │
│ /volumes/       │                      │                    │
│                 │                      │                    │
│ ✅ Production   │ ✅ Development        │ ✅ Sensitive temp  │
│ ✅ Portable     │ ❌ Host-dependent    │ ✅ Fast/secure     │
│ ✅ Easy backup  │ ✅ Hot-reloading     │ ❌ Lost on restart  │
└─────────────────┴──────────────────────┴───────────────────┘
```

---

### Named Volumes (Production Standard)

```bash
# Create a named volume
docker volume create my-db-data

# List volumes
docker volume ls

# Inspect a volume (see where data is stored on host)
docker volume inspect my-db-data
# "Mountpoint": "/var/lib/docker/volumes/my-db-data/_data"

# Use named volume with a container
docker run -d \
  --name postgres-db \
  --network my-app-network \
  -v my-db-data:/var/lib/postgresql/data \
  # -v VOLUME_NAME:CONTAINER_PATH
  # What: Mount 'my-db-data' volume at /var/lib/postgresql/data
  # Why: PostgreSQL stores its database files at that path
  # Effect: Data persists even if container is deleted!
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=securepassword \
  -e POSTGRES_DB=myapp \
  postgres:16-alpine

# Test persistence:
# 1. Insert data into the database
# 2. Delete the container: docker rm -f postgres-db
# 3. Recreate with same volume: docker run ... -v my-db-data:...
# 4. Your data is still there! ✅

# Remove a volume (CAREFUL: deletes data!)
docker volume rm my-db-data

# Remove all unused volumes
docker volume prune
```

---

### Bind Mounts (Development Workflow)

Bind mounts map a **specific path on your host** to a path inside the container. Perfect for development — code changes on your host appear instantly inside the container.

```bash
# Syntax: -v /absolute/host/path:/container/path
# OR:     --mount type=bind,source=/host/path,target=/container/path

# Development: mount current directory into container
docker run -d \
  -p 5000:5000 \
  -v $(pwd):/app \
  # $(pwd): Current directory (your code)
  # /app: Where the container sees it
  # Effect: Edit code on host → immediately visible in container
  --name dev-server \
  my-flask-app:dev

# Result: No rebuild needed when you change code!
# The container reads directly from your host filesystem
```

**Bind mount for read-only config:**
```bash
# Mount a config file as read-only (container can't modify it)
docker run -d \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro \
  # :ro = read-only; container cannot modify the file
  nginx:1.27
```

---

### tmpfs Mounts (Sensitive Temporary Data)

```bash
# tmpfs: Data lives in memory only, never written to disk
# Use case: Session tokens, temporary credentials, sensitive processing
docker run -d \
  --tmpfs /tmp:size=100m,mode=1777 \
  # /tmp: Mount point inside container
  # size=100m: Limit to 100MB of RAM
  # mode=1777: World-writable with sticky bit (like /tmp on Linux)
  my-app:1.0

# Or in docker run long form:
docker run -d \
  --mount type=tmpfs,destination=/tmp,tmpfs-size=100m \
  my-app:1.0
```

---

### Volume Backups

```bash
# Backup a named volume
# Strategy: Run a temp container, mount the volume, tar the contents
docker run --rm \
  -v my-db-data:/source:ro \
  # Mount the volume as read-only source
  -v $(pwd):/backup \
  # Mount current directory for output
  ubuntu \
  tar czf /backup/db-backup-$(date +%Y%m%d).tar.gz -C /source .
  # tar: Create compressed archive
  # -czf: Create, gzip, file
  # -C /source: Change to source dir before archiving

# Restore a backup
docker run --rm \
  -v my-db-data:/target \
  -v $(pwd):/backup:ro \
  ubuntu \
  tar xzf /backup/db-backup-20260521.tar.gz -C /target
```

---

## Part 3: Putting It Together — App + Database

Let's run a full stack (FastAPI + PostgreSQL + Redis) using what we've learned:

```bash
# Create dedicated networks
docker network create app-frontend    # For client → API
docker network create app-backend     # For API → DB/Cache

# Create named volumes for persistence
docker volume create postgres-data
docker volume create redis-data

# Start PostgreSQL (backend network only, no public exposure)
docker run -d \
  --name postgres \
  --network app-backend \
  -v postgres-data:/var/lib/postgresql/data \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_PASSWORD=S3cureP@ss \
  -e POSTGRES_DB=appdb \
  --restart unless-stopped \
  # --restart: Automatically restart if it crashes or host reboots
  postgres:16-alpine

# Start Redis cache (backend network only)
docker run -d \
  --name redis \
  --network app-backend \
  -v redis-data:/data \
  --restart unless-stopped \
  redis:7-alpine \
  redis-server --appendonly yes
  # --appendonly yes: Enable AOF persistence (survives restarts)

# Start API (connected to BOTH networks)
docker run -d \
  --name api \
  --network app-backend \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://appuser:S3cureP@ss@postgres:5432/appdb \
  -e REDIS_URL=redis://redis:6379 \
  --restart unless-stopped \
  my-fastapi-app:1.0

# Connect API to frontend network too
docker network connect app-frontend api

# Start Nginx reverse proxy (frontend network, exposed to world)
docker run -d \
  --name nginx \
  --network app-frontend \
  -p 80:80 \
  -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro \
  --restart unless-stopped \
  nginx:1.27-alpine
```

**Architecture:**
```mermaid
graph TD
    USER["👤 Users (internet)"]
    NGINX["🔀 Nginx :80\n(frontend-net)"]
    API["⚡ FastAPI :8000\n(frontend-net + backend-net)"]
    PG["🗃️ PostgreSQL\n(backend-net only)"]
    REDIS["⚡ Redis\n(backend-net only)"]
    PG_VOL["💾 postgres-data volume"]
    REDIS_VOL["💾 redis-data volume"]

    USER --> NGINX
    NGINX --> API
    API --> PG
    API --> REDIS
    PG --> PG_VOL
    REDIS --> REDIS_VOL
```

---

## Common Mistakes

**Mistake 1: Storing data inside the container**

```bash
# ❌ WRONG — data is inside the container
docker run -d --name db postgres:16-alpine
# Data at /var/lib/postgresql/data INSIDE the container
docker rm db  # All data gone! 😢

# ✅ CORRECT — use a named volume
docker run -d --name db \
  -v postgres-data:/var/lib/postgresql/data \
  postgres:16-alpine
docker rm db          # Container gone
docker run -d --name db \
  -v postgres-data:/var/lib/postgresql/data \  # Same volume!
  postgres:16-alpine
# Data is still here! ✅
```

**Mistake 2: Using default bridge network**

```bash
# ❌ WRONG — no DNS, containers can't find each other by name
docker run -d --name web my-web:1.0
docker run -d --name api my-api:1.0
# web cannot ping 'api' by name

# ✅ CORRECT — custom network provides DNS
docker network create app-net
docker run -d --name web --network app-net my-web:1.0
docker run -d --name api --network app-net my-api:1.0
# web can now ping 'api' by name ✅
```

**Mistake 3: Exposing database ports publicly**

```bash
# ❌ WRONG — PostgreSQL accessible from the internet!
docker run -d -p 5432:5432 --name db postgres:16-alpine

# ✅ CORRECT — no -p, only accessible from other containers on same network
docker run -d --network app-net --name db postgres:16-alpine
```

---

## Practice Exercises

**Exercise 1: Set Up MongoDB with Persistence**

Set up MongoDB with a named volume and custom network:

Requirements:
- Named volume: `mongo-data`
- Custom network: `mongo-net`
- Environment: `MONGO_INITDB_ROOT_USERNAME=admin`, `MONGO_INITDB_ROOT_PASSWORD=admin123`
- Don't expose MongoDB to the host

<details>
<summary>Solution</summary>

```bash
# Create resources
docker volume create mongo-data
docker network create mongo-net

# Run MongoDB
docker run -d \
  --name mongodb \
  --network mongo-net \
  -v mongo-data:/data/db \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=admin123 \
  --restart unless-stopped \
  mongo:7.0

# Verify it's running
docker ps
docker logs mongodb

# Connect using the mongo shell FROM inside the network
docker run -it --rm \
  --network mongo-net \
  mongo:7.0 \
  mongosh mongodb://admin:admin123@mongodb:27017
# NOTE: No host port mapping needed — accessed via Docker DNS
```

**Why it works:** MongoDB stores its data in `/data/db` inside the container. The `mongo-data` volume mounts there, persisting data even if the container is deleted. The custom network enables DNS so other containers can reach it by name `mongodb`.
</details>

**Exercise 2: Network Isolation Test**

```bash
# Create two separate apps (should NOT communicate)
docker network create app1-net
docker network create app2-net

docker run -d --name app1 --network app1-net alpine sleep 3600
docker run -d --name app2 --network app2-net alpine sleep 3600

# Try to ping app2 from app1 (should fail!)
docker exec app1 ping -c 2 app2
# Expected: ping: bad address 'app2' — correctly isolated!

# Now put them on the same network
docker network connect app1-net app2
docker exec app1 ping -c 2 app2
# Expected: Works! They can now communicate.
```

---

## Best Practices

**✅ DO:**
- Use named volumes for databases — Why: Managed by Docker, portable, easy backup
- Create custom networks for your apps — Why: Automatic DNS, isolation
- Use bind mounts for development — Why: Hot-reload without rebuilding
- Only expose ports that must be public — Why: Reduces attack surface

**❌ DON'T:**
- Store app state inside containers — Why bad: Lost on restart | Fix: Named volumes
- Use the default bridge network — Why bad: No DNS | Fix: `docker network create`
- Expose database ports publicly — Why bad: Security risk | Fix: Use Docker networks only
- Use bind mounts in production — Why bad: Host-dependent, permission issues | Fix: Named volumes

---

## What's Next

**Learned:** ✅ Docker networks, ✅ Custom networks with DNS, ✅ Named volumes, ✅ Bind mounts, ✅ tmpfs, ✅ Multi-service networking

**Next:** Module 04: Docker Compose — Run your entire stack with one command

**Check:** Can you run a web app + database with proper networking and persistent storage?

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-21 | Initial version |
