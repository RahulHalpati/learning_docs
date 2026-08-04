# Section 02 · Data layer

> **Prerequisites:** [01 · Foundations & structure](../01_foundations_and_structure/README.md) · **Time:** ~3 h

The database is the heart of a service. This section builds the data layer: **async SQLAlchemy 2.0** models with typed columns and relationships, the **engine + session** plumbing (with a `get_db` dependency), and **Alembic** to version-control schema changes.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 02-1 | [SQLAlchemy models](01_sqlalchemy_models.md) | How do I define tables and relationships with SQLAlchemy 2.0? |
| 02-2 | [Engine & session](02_engine_and_session.md) | How do I connect async, and give each request a session? |
| 02-3 | [Migrations with Alembic](03_migrations_alembic.md) | How do I evolve the schema safely over time? |

## What you'll be able to do after this section

- Write typed `Mapped[...]` models with relationships, FKs, and mixins.
- Set up an async engine + session factory and the `get_db` dependency.
- Autogenerate and apply Alembic migrations (on SQLite and Postgres).

→ Start: **[02-1 · SQLAlchemy models](01_sqlalchemy_models.md)**
