.PHONY: install dev test migrate migration up down lint

install:                       ## install deps into the active venv
	pip install -r requirements.txt

dev:                           ## run the API with autoreload
	uvicorn app.main:app --reload

test:                          ## run the test suite (SQLite; Redis tests skip if none)
	pytest -q

migrate:                       ## apply migrations
	alembic upgrade head

migration:                     ## autogenerate a migration: make migration m="add x"
	alembic revision --autogenerate -m "$(m)"

up:                            ## full stack via docker compose
	docker compose up --build

down:                          ## tear the stack down
	docker compose down -v
