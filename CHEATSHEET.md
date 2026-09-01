# ⚡ Quick Reference — FastAPI · Flask · LangChain RAG · Redis · AWS · OpenTofu

> Scannable reference, no questions. For GCP / Pub/Sub / Gunicorn depth see **[INTERVIEW_CLOUD_CHEATSHEET.md](INTERVIEW_CLOUD_CHEATSHEET.md)**. For drilling, see **[INTERVIEW_QUESTIONS.md](INTERVIEW_QUESTIONS.md)**.

---

## 1 · FastAPI

### The skeleton that scales
```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):          # ✅ NOT @app.on_event (deprecated)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    yield
    await app.state.redis.aclose()

def create_app(settings) -> FastAPI:        # app factory → testable, multi-config
    app = FastAPI(lifespan=lifespan, title="svc", version="1.0")
    app.include_router(v1_router, prefix="/api/v1")
    return app
```

### Params — all the input types
```python
from typing import Annotated
from fastapi import Depends, Path, Query, Header, Cookie, Form, File, UploadFile

async def h(
    id: Annotated[int, Path(ge=1)],
    q: Annotated[str | None, Query(max_length=50)] = None,
    ua: Annotated[str | None, Header()] = None,          # user-agent (auto _→-)
    sid: Annotated[str | None, Cookie()] = None,
    name: Annotated[str, Form()] = ...,                   # multipart/form
    doc: Annotated[UploadFile, File()] = ...,             # needs python-multipart
    body: ItemIn = ...,                                   # Pydantic model = JSON body
): ...
```
> You **can't** mix a JSON `Body` with `File`/`Form` — the content-type owns the request.

### Dependency injection
```python
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]

async def get_db():                     # yield dep = resource manager
    async with SessionLocal() as s:
        try:
            yield s
            await s.commit()            # ONE commit point per request
        except Exception:
            await s.rollback(); raise
```
- Same dep used twice in a request → **runs once** (cached). Opt out: `Depends(f, use_cache=False)`.
- Router-wide: `APIRouter(dependencies=[Depends(require_api_key)])`.
- Tests: `app.dependency_overrides[get_db] = fake` (always clean up).

### Pydantic v2 (never v1 syntax)
| ✅ v2 | ❌ v1 |
|---|---|
| `model_config = ConfigDict(...)` | `class Config:` |
| `@field_validator` / `@model_validator` | `@validator` |
| `model_dump()` / `model_dump_json()` | `.dict()` / `.json()` |
| `model_validate()` | `parse_obj()` |

```python
class LinkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")     # reject unknown fields
    url: HttpUrl
    slug: str = Field(min_length=3, pattern=r"^[a-z0-9-]+$")

class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)   # ORM → schema
    slug: str                                          # note: no owner_email

@router.post("/links", response_model=LinkOut, status_code=201)   # ← security boundary
```

### Errors (RFC 9457 problem+json)
```python
@app.exception_handler(AppError)
async def handle(request, exc: AppError):
    return JSONResponse(
        status_code=exc.status,
        media_type="application/problem+json",
        content={"type": exc.code, "title": exc.title,
                 "status": exc.status, "detail": str(exc),
                 "instance": str(request.url)},
    )
```
Services raise **domain** exceptions; only the API layer knows HTTP.

### Status codes
`200` ok · `201` created (+`Location`) · `204` no content · `307/308` redirect (preserve method) · `400` bad input · `401` unauthenticated · `403` unauthorized · `404` not found (also: hide existence) · `409` conflict · `413` too large · `422` validation · `429` rate limited (+`Retry-After`)

### Layers
```
router     → HTTP only (parse, status, response_model)
service    → business rules, domain exceptions, NO fastapi imports
repository → queries only, no business rules
```

### Testing
```python
# pyproject: [tool.pytest.ini_options] asyncio_mode = "auto"
async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
    r = await c.post("/links", json={...})
```
Per-test isolation: session-scoped engine → `conn.begin()` → session bound to conn → override `get_db` → **rollback** in teardown.

### Run
```bash
fastapi dev app/main.py                                    # dev
uvicorn app.main:app --host 0.0.0.0 --workers 4            # prod (simple)
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4  # prod (managed)
```
Async workers: **~1 per core** (not `2n+1`). `AUTO`-suspend equivalents: `--timeout-graceful-shutdown`.

---

## 2 · Flask (and how it maps to FastAPI)

| Concept | Flask | FastAPI |
|---|---|---|
| App | `Flask(__name__)` | `FastAPI()` (+ factory) |
| Route | `@app.route("/x", methods=["POST"])` | `@app.post("/x")` |
| Modularity | **Blueprint** | **APIRouter** |
| Request data | `request.json` / `request.form` / `request.files` | typed params + Pydantic |
| Validation | manual / marshmallow | **built-in** (Pydantic) |
| Config | `app.config.from_object()` | pydantic-settings + `Depends` |
| Per-request state | `g`, context locals | dependencies (explicit) |
| Sessions | `flask.session` (signed cookie) | your own cookie/JWT/Redis |
| Docs | none | **auto OpenAPI** |
| Server | WSGI (gunicorn sync) | ASGI (uvicorn) |

```python
# Flask app factory + blueprint (the pattern that transfers)
def create_app(cfg=None):
    app = Flask(__name__)
    app.config.from_object(cfg or "config.Default")
    db.init_app(app); migrate.init_app(app, db)
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    @app.errorhandler(AppError)
    def _e(e): return jsonify(error=str(e)), e.status
    return app
```
```bash
gunicorn "app:create_app()" -w 5 --bind 0.0.0.0:8000   # sync workers: (2×cores)+1
```
**Gotchas:** app/request context (`with app.app_context()`), Flask-SQLAlchemy sessions are per-context, `flask db migrate/upgrade` (Flask-Migrate = Alembic).

---

## 3 · LangChain RAG

### The pipeline
```
load → split → embed → store          (ingest, offline)
query → retrieve → [rerank] → prompt → LLM → answer + citations   (serve)
```

### Minimal chain
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

prompt = ChatPromptTemplate.from_template(
    "Answer ONLY from the context. If it's not there, say you don't know.\n\n"
    "Context:\n{context}\n\nQuestion: {question}"
)
chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt | llm | StrOutputParser()
)
chain.invoke("what is the refund window?")     # .ainvoke / .stream / .astream
```

### Splitting
```python
RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
```
Too big → diluted embedding + wasted tokens. Too small → lost context. **Test with a hit-rate set.**

### Retrieval knobs
| Strategy | Use when |
|---|---|
| `similarity` (top-k) | default |
| `mmr` | results are near-duplicates |
| score threshold | drop weak matches |
| **hybrid** (BM25 + dense) | exact terms/IDs/rare words matter |
| **rerank** (cross-encoder) | precision matters; retrieve 50 → keep 5 |
| multi-query | phrasing varies |
| parent-document | small chunks to match, big chunks to answer |

### Vector stores — pick one
| Store | When |
|---|---|
| `InMemoryVectorStore` / FAISS | learning, tests, prototypes |
| **pgvector** | **default for prod** ≤ ~50M vectors, you already run Postgres |
| Qdrant | pure-vector scale + strong filtering |
| Weaviate | want hybrid built in |
| Pinecone | zero-ops managed, enterprise SLA |
| Neo4j | relationships *are* the query (GraphRAG) |

```python
from langchain_postgres import PGVector
store = PGVector(embeddings=emb, collection_name="docs",
                 connection=os.environ["PG_DSN"], use_jsonb=True)
retriever = store.as_retriever(search_kwargs={"k": 5, "filter": {"tenant": tid}})
```
```sql
CREATE EXTENSION vector;
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops);  -- else seq scan
SET hnsw.ef_search = 100;   -- ↑ recall, ↑ latency
```
**Indexes:** flat = exact/small · **IVFFlat** = fast build, less memory, tune `lists`/`probes` · **HNSW** = best recall/latency, slower build, more memory (**prod default**). All trade **recall for speed**.

### Tool calling / agents
```python
@tool
def get_order(order_id: str) -> dict:
    """Look up an order by its ID. Use when the user mentions an order number."""
    ...                       # docstring + types = the contract the model reads
llm.bind_tools([get_order])    # model emits the call; YOUR code executes it
```

### Evaluation
- **Retrieval:** context precision / recall, hit-rate@k
- **Generation:** **faithfulness** (grounded?) + answer relevance (useful?)
- Golden set + LLM-as-judge → **run in CI with a threshold**

### Grounding rules
Answer only from context · cite sources · "I don't know" when unretrieved · retrieved text is **data, not instructions** (injection) · pre-filter by tenant, never post-filter.

---

## 4 · Redis

```python
from redis.asyncio import Redis                 # ✅ redis-py (aioredis is dead)
r = Redis.from_url(url, decode_responses=True)  # one client per process, in lifespan
```

| Pattern | Commands |
|---|---|
| **Cache-aside** | `GET` → miss → DB → `SETEX key ttl val` → return |
| **Invalidate** | `DEL key` **on write** (don't try to update it) |
| Fixed-window limit | `INCR k` + `EXPIRE k 60` (boundary-burst flaw) |
| **Sliding window** | `ZADD` ts → `ZREMRANGEBYSCORE` → `ZCARD` |
| Denylist / revoke | `SET jti 1 EX <remaining-ttl>` |
| Session store | `HSET session:{id}` + `EXPIRE` (sliding) |
| Distributed lock | `SET k v NX EX 30` (+ unique token to release) |
| Idempotency mark | `SET done:{id} 1 NX EX 86400` |
| Queue (jobs) | Arq/Celery over Redis lists |
| **Pub/sub** | `PUBLISH ch msg` / `SUBSCRIBE` — broadcast, **at-most-once, no replay** |
| **Streams** | `XADD` / `XREADGROUP` — durable broadcast + ack + replay |

```python
# cache-aside
if (hit := await r.get(k)):
    return Model.model_validate_json(hit)
obj = await db_fetch()
await r.setex(k, 300, obj.model_dump_json())
```
```python
# subscriber = long-lived task in lifespan, on its OWN connection
async with r.pubsub() as ps:
    await ps.subscribe("events")
    async for m in ps.listen():
        if m["type"] == "message": await handle(m["data"])
```
**Rules:** key naming `entity:{id}:v1` · TTL bounds *staleness*, not correctness · a subscribed connection can't run normal commands · rate-limit key = user/API-key (IP alone is bypassable).

---

## 5 · AWS (short)

| Service | Is | Note |
|---|---|---|
| **S3** | object storage | private by default; **presigned URL** to share; `ContentDisposition` = download vs stream |
| **Lambda** | serverless fn | needs an **execution role**; cold starts |
| **API Gateway** | HTTP front for Lambda | proxy integration |
| **DynamoDB** | NoSQL | PK/SK design decides everything |
| **RDS** | managed Postgres/MySQL | |
| **SQS** | queue, one consumer | durable, at-least-once → **idempotent** |
| **SNS** | pub/sub fan-out | pair with SQS per consumer |
| **EventBridge** | event bus, content routing | |
| **Secrets Manager / SSM** | secrets / params | never hardcode |
| **IAM / STS** | who can do what / temp creds | prefer **roles** over users |
| **CloudWatch / Logs** | metrics / logs | |
| **KMS** | encryption keys | encrypt-at-rest story |
| **ECR / ECS / Fargate** | registry / containers | |

### IAM — the two policies every service role needs
```json
// 1) TRUST policy — who may assume it
{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
 "Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}
```
```json
// 2) PERMISSIONS policy — what it may do (named actions, named ARNs)
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":["dynamodb:GetItem","dynamodb:PutItem"],
  "Resource":"arn:aws:dynamodb:*:*:table/links"},
 {"Effect":"Allow","Action":["logs:CreateLogStream","logs:PutLogEvents"],
  "Resource":"arn:aws:logs:*:*:*"}]}          // ← omit and your fn logs nothing
```
- **Identity-based** = attached to a role · **Resource-based** = attached to the thing (S3 bucket policy, SQS queue policy).
- `"Resource": "*"` is a review smell. Least privilege = named actions on named ARNs.
- `aws sts get-caller-identity` = "who am I actually running as".

### boto3
```python
s3 = boto3.client("s3", endpoint_url=os.getenv("AWS_ENDPOINT_URL") or None)  # emulator-friendly
s3.put_object(Bucket=b, Key=k, Body=data, ContentType="application/pdf")
url = s3.generate_presigned_url("get_object", Params={"Bucket": b, "Key": k}, ExpiresIn=3600)
```
**Local dev:** Floci (LocalStack's free successor) at `http://localhost:4566` — `awslocal s3 mb s3://x`. Caveat: the emulator **doesn't enforce IAM**, so author policies locally, verify allow/deny on real AWS.

---

## 6 · Terraform / OpenTofu

> OpenTofu is the open-source Terraform fork — **same HCL, state, modules, workflow**. `terraform` ↔ `tofu` are drop-in.

```bash
tofu init       # providers + backend
tofu plan       # review the diff — the safety rail
tofu apply      # make it so
tofu destroy    # tear down (do this on trials!)
tofu fmt && tofu validate
tofu state list && tofu import <addr> <id>
```

```hcl
terraform {
  required_providers { aws = { source = "hashicorp/aws", version = "~> 5.0" } }
  backend "s3" {                     # REMOTE state + locking (never local, never committed)
    bucket = "tf-state"; key = "prod/terraform.tfstate"
    region = "us-east-1"; use_lockfile = true
  }
}

variable "env" { type = string; default = "dev" }

resource "aws_s3_bucket" "assets" {
  bucket = "linkbox-assets-${var.env}"
  tags   = { env = var.env }
}

data "aws_caller_identity" "me" {}          # read, don't create

module "api" {                              # reuse
  source = "./modules/service"
  name   = "linkbox"
  count  = var.enabled ? 1 : 0              # or for_each = toset([...])
}

output "bucket" { value = aws_s3_bucket.assets.id }
```

**Key ideas:** declarative + **idempotent** · state maps config→real resources (holds secrets — remote + locked) · plan before apply · one config/workspace per env · modules for reuse · `depends_on` only when implicit ordering fails.

**Against Floci:**
```hcl
provider "aws" {
  region = "us-east-1"
  access_key = "test"; secret_key = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  s3_use_path_style           = true        # emulator S3 quirk
  endpoints { s3 = "http://localhost:4566" }
}
```

---

## The one-liners worth memorizing

- `response_model` is a **security boundary**, not documentation.
- One **commit point** per request; services never import `fastapi`.
- Async workers ≈ **1 per core**; sync ≈ `(2×cores)+1`.
- Gunicorn is **WSGI**; FastAPI is **ASGI** → `-k uvicorn.workers.UvicornWorker`.
- TTL bounds **staleness**; only invalidation gives **correctness**.
- pub/sub = broadcast/at-most-once · queue = one-consumer/durable · Streams = both.
- **pgvector unless you can name the bottleneck.** No index = sequential scan.
- HNSW/IVF trade **recall for speed**.
- Retrieved text is **data, not instructions**.
- IAM: named actions on named ARNs; `*` is a smell.
- `plan` before `apply`; state is remote, locked, and never committed.
