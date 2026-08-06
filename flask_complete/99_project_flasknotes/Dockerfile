# Multi-stage: build deps separately so the final image stays small.
FROM python:3.10-slim AS builder
WORKDIR /install
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY --from=builder /install/deps /usr/local
COPY app ./app
COPY migrations ./migrations
COPY wsgi.py .

# Never run as root.
RUN useradd --create-home appuser && chown -R appuser /srv
USER appuser

EXPOSE 8000
# Migrate, then serve with gunicorn (NEVER the dev server in production).
CMD ["sh", "-c", "flask db upgrade && gunicorn -w 4 -b 0.0.0.0:8000 'wsgi:app'"]
