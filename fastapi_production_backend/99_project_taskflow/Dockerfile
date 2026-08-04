# Multi-stage build: small final image, no build tooling shipped.
FROM python:3.10-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

FROM base AS builder
WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

FROM base AS final
WORKDIR /srv
# Copy only the installed packages from the builder stage.
COPY --from=builder /install/deps /usr/local
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .

# Run as a non-root user (security).
RUN useradd --create-home appuser && chown -R appuser /srv
USER appuser

EXPOSE 8000
# Apply migrations, then serve. gunicorn manages uvicorn workers in production.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
