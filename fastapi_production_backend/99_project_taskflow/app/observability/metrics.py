"""Prometheus metrics — a /metrics endpoint plus request counters/latency."""
import time

from fastapi import FastAPI
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REQUESTS = Counter(
    "http_requests_total", "Total HTTP requests",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency",
    ["method", "path"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        # Use the route template (e.g. /projects/{id}), not the raw path, to bound cardinality.
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
        REQUESTS.labels(request.method, path, response.status_code).inc()
        return response


def setup_metrics(app: FastAPI) -> None:
    app.add_middleware(MetricsMiddleware)
    app.mount("/metrics", make_asgi_app())        # Prometheus scrapes this
