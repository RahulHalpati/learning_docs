# Multi-stage build — a small, non-root runtime image.
# (The Docker course covers this pattern in depth; here it's the "build" stage.)

# ---- builder: install deps into a venv ----
FROM python:3.11-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN python -m venv /venv && /venv/bin/pip install -r requirements.txt

# ---- runtime: copy only what's needed ----
FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PATH="/venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY --from=builder /venv /venv
COPY app ./app

# run as a non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
# gunicorn would be the production server; flask's built-in is fine for the demo
CMD ["python", "-m", "app.main"]

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
