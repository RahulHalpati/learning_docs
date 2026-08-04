# Section 08 · Observability & ops

> **Prerequisites:** [05 · API design & robustness](../05_api_design_and_robustness/README.md) · **Time:** ~2 h

You can't operate what you can't see. This section makes TaskFlow **observable**: **structured logs** you can search, **health/readiness probes** for orchestrators, and **Prometheus metrics** for dashboards and alerts. This is what separates "it's deployed" from "we know it's healthy."

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 08-1 | [Structured logging](01_structured_logging.md) | How do I emit logs I can actually search and correlate? |
| 08-2 | [Health checks](02_health_checks.md) | How do orchestrators know the app is alive and ready? |
| 08-3 | [Metrics & tracing](03_metrics_and_tracing.md) | How do I measure latency, errors, and throughput? |

## What you'll be able to do after this section

- Emit JSON logs with a request id, correlated across a request's life.
- Expose liveness (`/healthz`) and readiness (`/readyz`) probes.
- Export Prometheus metrics (request counts, latency) at `/metrics`.

→ Start: **[08-1 · Structured logging](01_structured_logging.md)**
