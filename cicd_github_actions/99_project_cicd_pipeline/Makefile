# Local mirror of the CI pipeline. Every CI stage has a `make` target here, so
# "works on my machine" and "works in CI" run the SAME commands.
#
#   make install   → create .venv and install dev deps
#   make lint      → ruff (style + common bugs)
#   make test      → pytest
#   make cov       → pytest with coverage, fail under 80%
#   make security  → bandit (SAST) + pip-audit (SCA)
#   make build     → docker image
#   make ci        → lint + cov + security   (what the CI job runs)
#   make run       → run the app locally
#   make smoke     → hit /health on a running app

VENV := .venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip
IMAGE := linkstash:local

.PHONY: install lint format test cov security build run smoke ci clean

install:
	python3 -m venv $(VENV)
	$(PIP) install -q -U pip
	$(PIP) install -q -r requirements-dev.txt
	$(PIP) install -q -e .

lint:
	$(VENV)/bin/ruff check app tests

format:
	$(VENV)/bin/ruff format app tests

test:
	$(PY) -m pytest

cov:
	$(PY) -m coverage run -m pytest
	$(PY) -m coverage report --fail-under=80

security:
	$(VENV)/bin/bandit -q -r app
	$(VENV)/bin/pip-audit -r requirements.txt      # audit what we SHIP (locked runtime deps)

build:
	docker build -t $(IMAGE) .

run:
	$(PY) -m app.main

smoke:
	curl -fsS http://127.0.0.1:8000/health && echo " OK"

ci: lint cov security
	@echo "✅ CI passed locally"

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache .coverage htmlcov dist *.egg-info
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
