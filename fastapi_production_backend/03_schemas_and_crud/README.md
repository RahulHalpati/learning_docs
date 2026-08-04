# Section 03 · Schemas & CRUD

> **Prerequisites:** [02 · Data layer](../02_data_layer/README.md) · **Time:** ~3 h

Now the app does something. This section adds **Pydantic schemas** (the API contract), the **repository + service** layers that keep logic out of your routes, and full **CRUD endpoints** with pagination and filtering.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 03-1 | [Pydantic schemas](01_pydantic_schemas.md) | How do I define request/response models separate from the ORM? |
| 03-2 | [Repository & service pattern](02_repository_service_pattern.md) | Where does data access and business logic live? |
| 03-3 | [CRUD endpoints & pagination](03_crud_endpoints_pagination.md) | How do I build clean CRUD with paging and filtering? |

## What you'll be able to do after this section

- Write `Create`/`Read`/`Update` schemas and read straight from ORM objects (`from_attributes`).
- Split data access (repository) from business rules (service).
- Build CRUD routes returning a consistent paginated envelope, with query filters.

→ Start: **[03-1 · Pydantic schemas](01_pydantic_schemas.md)**
