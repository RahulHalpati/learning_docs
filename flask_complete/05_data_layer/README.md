# Section 05 · Data layer

> **Prerequisites:** [04 · App structure](../04_app_structure/README.md) · **Time:** ~3 h

Persistence, the industry-standard way: **Flask-SQLAlchemy 3.1** (SQLAlchemy 2.0 under the hood) for models and queries, and **Flask-Migrate 4** (Alembic) to evolve the schema without losing data.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 05-1 | [Models with Flask-SQLAlchemy](01_models_sqlalchemy.md) | How do I define tables as Python classes? |
| 05-2 | [Queries & relationships](02_queries_relationships.md) | How do I read, filter, paginate, and traverse relations? |
| 05-3 | [Migrations with Flask-Migrate](03_migrations.md) | How do I change the schema safely over time? |

## What you'll be able to do after this section

- Define typed models with relationships, cascades, and indexes.
- Query with the SQLAlchemy 2.0 `select()` style and paginate results.
- Run `flask db init/migrate/upgrade` and understand what Alembic generated.

→ Start: **[05-1 · Models with Flask-SQLAlchemy](01_models_sqlalchemy.md)**
