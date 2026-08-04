# 08-3 · Metrics & tracing

> **Level:** Intermediate · **Prerequisites:** [05-3 · Middleware & CORS](../05_api_design_and_robustness/03_middleware_and_cors.md)
> **Time:** 30 min · **Verified:** 2026-07-27 (prometheus-client; from the TaskFlow app)

## Why this matters

Logs tell you about *individual* events; **metrics** tell you about *aggregate* behavior — request rate, error rate, latency percentiles — the numbers you put on dashboards and alert on. **Prometheus** is the de-facto standard: your app exposes a `/metrics` endpoint, Prometheus scrapes it, and you graph/alert in Grafana. **Tracing** (OpenTelemetry) then follows one request across services.

---

## Metrics with a middleware

Record a counter and a latency histogram for every request, labeled by method, route, and status:

```python
# app/observability/metrics.py (essentials)
from prometheus_client import Counter, Histogram, make_asgi_app

REQUESTS = Counter("http_requests_total", "Total HTTP requests",
                   ["method", "path", "status"])
LATENCY  = Histogram("http_request_duration_seconds", "Request latency",
                     ["method", "path"])

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)     # /projects/{id}, not /projects/7
        LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
        REQUESTS.labels(request.method, path, response.status_code).inc()
        return response

def setup_metrics(app):
    app.add_middleware(MetricsMiddleware)
    app.mount("/metrics", make_asgi_app())      # Prometheus scrapes here
```

**Output (real run):**
```
GET /metrics/  ->  200, body contains  http_requests_total
```

Prometheus scrapes `/metrics`, and you get request rate, error rate (filter `status`), and latency percentiles per endpoint.

> ⚠️ **Label by the route *template*, not the raw path.** Use `/projects/{id}`, never `/projects/7`, `/projects/8`, … Raw paths create unbounded label cardinality — a new time series per id — which will melt Prometheus. Always aggregate dynamic segments into their template. (`make_asgi_app` mounted at `/metrics` serves at `/metrics/`; Prometheus follows the redirect.)

---

## The three golden signals

With those two metrics you can watch what matters most (from Google's SRE book):

| Signal | From | Alert when |
|--------|------|-----------|
| **Traffic** | `rate(http_requests_total)` | unusual spike/drop |
| **Errors** | `rate(http_requests_total{status=~"5.."})` | error rate climbs |
| **Latency** | `histogram_quantile(0.95, http_request_duration_seconds)` | p95 exceeds your SLO |

(The fourth, *saturation*, comes from resource metrics — CPU/memory/pool usage.) These four are usually enough to know whether the service is healthy.

---

## Tracing with OpenTelemetry (the next step)

Metrics tell you *that* p95 latency rose; **traces** tell you *where* the time went. **OpenTelemetry** instruments your app to emit spans — a tree of "this request spent 40ms in the DB, 200ms calling an external API" — viewable in Jaeger/Tempo, and correlatable to your logs via the request id.

```python
# conceptual — pip install opentelemetry-instrumentation-fastapi
# from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
# FastAPIInstrumentor.instrument_app(app)   # auto-spans for every request
```

Metrics for *what's wrong*, traces for *where*, logs for *why* — the three pillars of observability, correlated by the request id.

---

## Recap & next

- ✅ Expose **Prometheus** metrics at `/metrics` via a middleware: request counter + latency histogram.
- ✅ Label by the **route template** (`/projects/{id}`) to avoid unbounded cardinality.
- ✅ Watch the golden signals: traffic, errors, latency (+ saturation).
- ✅ Add **OpenTelemetry** tracing to see *where* time goes; correlate metrics/traces/logs by request id.
- ✅ Self-check: why is labeling metrics with `/projects/7` (raw id) a production hazard?

→ Next: **[09 · Containerization & deploy](../09_containerization_and_deploy/README.md)**

## Exercises

1. Scrape `/metrics`, make a few requests, and find `http_requests_total{...status="200"}` climbing. Then write a Prometheus query for the 5xx error rate.

<details>
<summary>Solution</summary>

Hit some endpoints, `GET /metrics`, grep `http_requests_total`. Error-rate query: `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` — the fraction of requests failing, the classic alerting metric.
</details>
