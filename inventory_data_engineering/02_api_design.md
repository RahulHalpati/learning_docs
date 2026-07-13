# 02: API Design to Expose Inventory Data Models

> **Level:** Intermediate  
> **Prerequisites:** Module 01  
> **Time:** 45 minutes  
> **What You'll Learn:** How to build REST and GraphQL APIs to securely expose your database to the outside world.

## Introduction
**What:** Creating a digital gateway (API) so other apps can read/write your inventory data without touching the database directly.  
**Why:** Letting a front-end website directly query your database is a massive security risk and causes crashes. APIs act as a controlled bouncer at the door.  
**Example:** When the billing system needs to know if a customer's router is active, it asks the Inventory API, not the Inventory Database.

## Core Concepts

### Concept 1: RESTful API Design
- **What:** Representational State Transfer. Uses standard HTTP methods.
- **Why:** The industry standard. Easy to build and scale.
- **Methods:**
  - `GET /routers`: List all routers
  - `POST /routers`: Create a new router
  - `GET /routers/123`: Get router ID 123
  - `PUT /routers/123`: Update router ID 123

### Concept 2: Pagination & Filtering
- **What:** Limiting the data returned by the API.
- **Why:** If you have 10 million routers, a simple `GET /routers` will crash your server. You must implement `?limit=100&offset=0`.

### Concept 3: Payload Transformation
- **What:** Converting database models into API JSON responses (often called DTOs - Data Transfer Objects).
- **Why:** You might not want to expose internal database fields (like `created_by_admin_id`) to the public API.

## Practical Example

**Building:** A simple FastAPI endpoint to expose a Router.  
**Why:** FastAPI is a modern, fast Python web framework perfect for data APIs.

```python
# STANDARD LIBRARY
from typing import Optional, List

# THIRD-PARTY (pip install fastapi pydantic uvicorn)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Inventory API")

# --- Pydantic Models (Data Transfer Objects) ---
class RouterResponse(BaseModel):
    """What: The JSON structure sent to the user | Why: Validates data leaving the API"""
    id: int
    hostname: str
    status: str

class RouterCreate(BaseModel):
    """What: The JSON structure expected from the user | Why: Validates incoming data"""
    hostname: str
    status: Optional[str] = "active"

# --- Mock Database ---
# In a real app, this would query the SQL database from Module 01
fake_db = {
    1: {"id": 1, "hostname": "NYC-RTR-01", "status": "active"},
    2: {"id": 2, "hostname": "LA-RTR-01", "status": "faulty"}
}

# --- API Endpoints ---
@app.get("/api/v1/routers/{router_id}", response_model=RouterResponse)
def get_router(router_id: int) -> RouterResponse:
    """
    Get a specific router.
    
    What: Looks up router by ID.
    Why: Standard REST pattern for single item retrieval.
    Returns: RouterResponse - JSON payload
    """
    router = fake_db.get(router_id)
    if not router:
        # Why: Always return proper HTTP status codes, not just error strings.
        raise HTTPException(status_code=404, detail="Router not found")
        
    return router
```

## Best Practices

**✅ DO:**
- **Version Your APIs** - Why: Use `/api/v1/routers`. If you drastically change the API next year, you create `/v2/` so you don't break old systems.
- **Use Proper Status Codes** - Why: Return `200 OK` for success, `201 Created` for new items, `404 Not Found`, and `400 Bad Request`.

**❌ DON'T:**
- **Use Verbs in URLs** - Why bad: `GET /get_routers` or `POST /create_router` violates REST principles. | Fix: Use nouns and rely on the HTTP method: `GET /routers` and `POST /routers`.

## Common Mistakes

**Mistake:** Exposing the Database Auto-Incrementing ID blindly.
**Why:** If competitors see your IDs go from 1 to 50 in a day, they know exactly how many sales you made (German Tank Problem).
**Fix:** Use UUIDs (Universally Unique Identifiers) like `a1b2c3d4...` for public API IDs.

## Practice Exercises

**Exercise 1:** Design a POST endpoint
- Requirements: Write the function signature for a FastAPI endpoint that creates a new router using the `RouterCreate` model.
- Hint: Use `@app.post` and accept the model as a parameter.

<details>
<summary>Solution</summary>

```python
@app.post("/api/v1/routers", status_code=201, response_model=RouterResponse)
def create_router(router_in: RouterCreate) -> RouterResponse:
    # Logic to save to DB here...
    return {"id": 999, "hostname": router_in.hostname, "status": router_in.status}
```
**Why it works:** It uses the POST method for creation, expects the `RouterCreate` JSON body, and returns a 201 status code.
</details>

## What's Next
**Learned:** ✅ RESTful principles, ✅ DTOs with Pydantic, ✅ API Versioning.  
**Next:** Module 03: ETL & Data Profiling - How to get massive amounts of data INTO this database!  
**Check:** What HTTP method should you use to update an existing resource?
