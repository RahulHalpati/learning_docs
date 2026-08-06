# 99 · Capstone — FlaskNotes

> **Level:** Intermediate → Advanced · **Prerequisites:** Sections 01–09
> **Time:** the whole course · **Verified:** 2026-07-29 · Python 3.10 · Flask 3.1.3 · Flask-SQLAlchemy 3.1.1 · Flask-Migrate 4.1.0 · Flask-Login 0.6.3 · PyJWT 2.13.0 · gunicorn 26.0.0

The complete, runnable application this course builds — **one codebase with two faces**: a server-rendered Jinja2 web UI and a token-authenticated JSON API, sharing models, config, and error handling.

## What's in it

| Concern | Where | Lesson |
|---------|-------|--------|
| Application factory | `app/__init__.py` | [04-1](../04_app_structure/01_app_factory.md) |
| Extensions (`init_app`) | `app/extensions.py` | [04-1](../04_app_structure/01_app_factory.md) |
| Config classes + env | `app/config.py` | [04-3](../04_app_structure/03_config_and_env.md) |
| Blueprints (web / auth / api) | `app/blueprints/` | [04-2](../04_app_structure/02_blueprints.md) |
| Models & relationships | `app/models.py` | [05-1](../05_data_layer/01_models_sqlalchemy.md) |
| Migrations | `migrations/` | [05-3](../05_data_layer/03_migrations.md) |
| Templates (inheritance, flash) | `app/templates/` | [02](../02_templates_and_static/README.md) |
| Image uploads (validated) | `app/blueprints/web.py` | [03-3](../03_request_handling/03_forms_files_images.md) |
| Session auth (Flask-Login) | `app/blueprints/auth.py` | [06-2](../06_auth_and_sessions/02_passwords_login.md) |
| JWT auth + ownership | `app/blueprints/api.py` | [06-3](../06_auth_and_sessions/03_jwt_apis.md) |
| Error handling (HTML *or* JSON) | `app/errors.py` | [07-1](../07_errors_logging_cors/01_error_handling.md) |
| Tests (20) | `tests/` | [08](../08_testing/README.md) |
| gunicorn + Docker | `wsgi.py`, `Dockerfile` | [09](../09_production/README.md) |

## The API

```
POST   /register  /login  /logout          session auth (web UI)
GET    /                                   your notes (HTML)
GET    /notes/new   POST /notes/new        create a note, with image upload
GET    /uploads/<filename>                 serve an uploaded image

POST   /api/v1/auth/token                  email+password -> JWT
GET    /api/v1/notes                       list (paginated: ?page=&per_page=)
POST   /api/v1/notes                       create            -> 201
GET    /api/v1/notes/<id>                  read one          (403 if not yours)
PATCH  /api/v1/notes/<id>                  partial update
DELETE /api/v1/notes/<id>                  delete            -> 204
GET    /healthz                            liveness probe
```

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export FLASK_APP=wsgi.py
flask db upgrade                 # create the schema
flask --app wsgi run --debug     # http://127.0.0.1:5000
```

Register an account, write a note, attach a PNG. Then try the API:

```bash
TOKEN=$(curl -s -X POST localhost:5000/api/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"password123"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s localhost:5000/api/v1/notes -H "Authorization: Bearer $TOKEN"
```

## Test it

```bash
pytest -q
```

**Output (real run):**
```
....................                                                     [100%]
20 passed in 2.98s
```

Covers the auth flow, note CRUD, pagination, validation (422), **ownership isolation** (user B gets 403 and sees zero of A's notes), image upload + rejection of bad types (415), the 404 page vs the JSON 404, and `/healthz`.

## Migrations

**Output (real run):**
```
$ flask db migrate -m "initial schema"
INFO  [alembic.autogenerate.compare] Detected added table 'users'
INFO  [alembic.autogenerate.compare] Detected added table 'notes'
$ flask db upgrade
INFO  [alembic.runtime.migration] Running upgrade  -> e48da8d06bf5, initial schema
$ tables -> ['alembic_version', 'users', 'notes']
```

## Serve it in production

```bash
gunicorn -w 4 -b 0.0.0.0:8000 'wsgi:app'
```

**Output (real run, gunicorn):**
```
GET /healthz        ->  {"status": "ok"}
GET /               ->  <title>FlaskNotes</title>
GET /api/v1/notes   ->  401                              (auth enforced)
GET /api/v1/nope    ->  {"error": {..., "status": 404}}  (JSON, not the HTML page)
```

Or the whole stack with Postgres:

```bash
docker compose up --build       # web + db
```

## Layout

```
99_project_flasknotes/
├── app/
│   ├── __init__.py        # create_app()
│   ├── config.py          # Development / Testing / Production
│   ├── extensions.py      # db, migrate, login_manager (bare)
│   ├── models.py          # User, Note
│   ├── errors.py          # ApiError + handlers
│   ├── blueprints/        # web.py, auth.py, api.py
│   ├── templates/         # base, index, new_note, login, register, 404, error
│   ├── static/style.css   └── uploads/
├── migrations/            # Alembic
├── tests/                 # conftest, test_web.py, test_api.py  (20 tests)
├── wsgi.py · requirements.txt · Dockerfile · docker-compose.yml · .env.example
```

## Extend it

- **Tags** on notes (many-to-many) — exercises an association table.
- **Background jobs** with Celery/RQ (email on note creation).
- **Rate limiting** with Flask-Limiter on `/login` and `/api/v1/auth/token`.
- **flask-smorest** to add OpenAPI docs to the API blueprint.
- **S3 uploads** instead of local disk, so multiple replicas share files.
