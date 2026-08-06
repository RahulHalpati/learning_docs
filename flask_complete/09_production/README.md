# Section 09 · Production

> **Prerequisites:** [08 · Testing](../08_testing/README.md) · **Time:** ~2 h

Getting FlaskNotes off your laptop: a real WSGI server, a container, and a checklist so nothing important is forgotten.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 09-1 | [Gunicorn & WSGI](01_gunicorn_wsgi.md) | How do I serve Flask properly (and why not `flask run`)? |
| 09-2 | [Docker & compose](02_docker_deploy.md) | How do I package the app and its database? |
| 09-3 | [Production checklist](03_production_checklist.md) | What must be true before this goes live? |

## What you'll be able to do after this section

- Serve with gunicorn (workers, `ProxyFix`) behind a reverse proxy.
- Build a multi-stage image that migrates on boot and runs as non-root.
- Run a concrete security/reliability checklist before deploying.

→ Start: **[09-1 · Gunicorn & WSGI](01_gunicorn_wsgi.md)**
