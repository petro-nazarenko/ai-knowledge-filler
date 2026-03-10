---
title: "Observability Stack Design with Metrics, Logs, and Traces"
type: guide
domain: devops
level: advanced
status: active
version: v1.0
tags: [observability, metrics, logging, tracing, opentelemetry]
related:
  - "[[Kubernetes_Deployment_Readiness]]"
  - "[[Microservices_Architecture_Patterns]]"
  - "[[Backend_API_Production_Readiness]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to designing a comprehensive observability stack using the three pillars — metrics, logs, and traces — with OpenTelemetry as the unifying standard.

## Prerequisites

- Running containerized application (Docker/Kubernetes)
- Understanding of distributed systems
- Basic familiarity with Prometheus or similar

## The Three Pillars

### Metrics
Numeric measurements over time. Answer: "Is the system healthy?"

### Logs
Discrete events with context. Answer: "What happened?"

### Traces
Request flow across services. Answer: "Where is the latency?"

## Step 1: OpenTelemetry SDK Setup

```python
# Python FastAPI application
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configure tracer
tracer_provider = TracerProvider()
tracer_provider.add_span_exporter(
    OTLPSpanExporter(endpoint="http://otel-collector:4317")
)
trace.set_tracer_provider(tracer_provider)

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
```

## Step 2: Metrics with Prometheus

```python
from prometheus_client import Counter, Histogram, generate_latest
import time

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Step 3: Structured Logging

```python
import structlog

log = structlog.get_logger()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

# Usage
log.info(
    "request.completed",
    method="GET",
    path="/orders",
    status_code=200,
    duration_ms=45,
    user_id="user-123",
    trace_id="trace-abc",
)
```

## Step 4: Distributed Tracing

```python
tracer = trace.get_tracer(__name__)

async def process_order(order_id: str):
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_id)

        with tracer.start_as_current_span("validate_order"):
            result = await validate(order_id)
            span.set_attribute("order.valid", result.valid)

        with tracer.start_as_current_span("payment.charge"):
            await charge_payment(order_id)
```

## SLI/SLO Definitions

### RED Method (Requests, Errors, Duration)

```yaml
# Prometheus alerting rules
- alert: HighErrorRate
  expr: rate(http_requests_total{status_code=~"5.."}[5m]) > 0.01
  annotations:
    summary: "Error rate above 1%"

- alert: HighLatency
  expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 0.5
  annotations:
    summary: "p99 latency above 500ms"
```

## Stack Options

| Tool | Purpose | Cloud-managed option |
|------|---------|---------------------|
| Prometheus | Metrics collection | Amazon Managed Prometheus |
| Grafana | Dashboards | Grafana Cloud |
| Loki | Log aggregation | Grafana Cloud |
| Jaeger/Tempo | Distributed tracing | Grafana Cloud Tempo |
| OTel Collector | Unified export | OpenTelemetry |

## Conclusion

Start with OpenTelemetry instrumentation for all three signals from day one — retrofitting observability is expensive. Use the RED method for service metrics, structured JSON logs with trace IDs, and distributed tracing for latency investigations. Target: every user-impacting issue should be diagnosed within 5 minutes using your observability stack.
