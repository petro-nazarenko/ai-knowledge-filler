---
title: "Service Blueprint — FastAPI Backend with OpenAPI Contract"
type: template
domain: backend-engineering
level: intermediate
status: active
version: v1.0
tags: [template, fastapi, openapi, service-blueprint, backend]
related:
  - "[[Backend_Service_Architecture_FastAPI|extends]]"
  - "[[API_Documentation_Structure_OpenAPI|extends]]"
  - "[[Backend_API_Production_Readiness_Checklist|references]]"
  - "[[API_Rate_Limiting_with_FastAPI|references]]"
created: 2026-03-17
updated: 2026-03-17
---

## Purpose

Reusable service blueprint for new FastAPI backend services. Synthesized from the FastAPI architecture reference and OpenAPI documentation standards. Copy this file, rename it `[ServiceName]_Service_Blueprint.md`, and fill in the placeholders before writing any code.

**How to use:** Complete every section before starting implementation. The blueprint is done when every `[PLACEHOLDER]` is replaced with real decisions.

---

## Service Overview

| Field | Value |
|-------|-------|
| **Service Name** | `[SERVICE_NAME]` |
| **Purpose** | [One sentence: what does this service do and for whom?] |
| **Owning Team / Owner** | [Name or team] |
| **Initial Version** | `1.0.0` |
| **Status** | `planning` → `development` → `staging` → `production` |
| **Base URL (Production)** | `https://[service-name].example.com/v1` |
| **Base URL (Staging)** | `https://[service-name]-staging.example.com/v1` |
| **Port (Local)** | `8000` |

### Functional Scope
- **In Scope:** [List 3–5 things this service is responsible for]
- **Out of Scope:** [List 2–3 explicit exclusions to prevent scope creep]

### Non-Functional Requirements

| Concern | Target |
|---------|--------|
| P99 latency | ≤ [X] ms |
| Availability | [99.9% / 99.5%] |
| Max RPS | [N] requests/second |
| Auth method | [Bearer JWT / API Key / OAuth 2.0] |

---

## Project Directory Layout

```
[service-name]/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routers/
│   │   │   ├── [resource_1].py       # e.g. users.py, orders.py
│   │   │   └── [resource_2].py
│   │   └── dependencies.py           # Shared FastAPI dependencies
│   ├── core/
│   │   ├── config.py                 # pydantic-settings Settings class
│   │   └── security.py               # Auth helpers
│   ├── models/
│   │   ├── domain.py                 # Pydantic domain models (business objects)
│   │   └── schemas.py                # API request/response schemas
│   ├── services/
│   │   └── [resource_1].py           # Business logic layer
│   ├── repositories/
│   │   ├── base.py                   # Generic CRUD repository
│   │   └── [resource_1].py           # Resource-specific queries
│   ├── db.py                         # Async SQLAlchemy engine + session factory
│   └── main.py                       # App factory (create_app)
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

---

## Core Endpoints (CRUD Scaffold)

Define your primary resource endpoints before writing code.

**Primary Resource:** `[resource]` (e.g. `orders`, `users`, `documents`)

| Method | Path | Summary | Auth Required |
|--------|------|---------|--------------|
| `GET` | `/v1/[resources]` | List [resources] (paginated) | Yes |
| `POST` | `/v1/[resources]` | Create a new [resource] | Yes |
| `GET` | `/v1/[resources]/{id}` | Get [resource] by ID | Yes |
| `PATCH` | `/v1/[resources]/{id}` | Update [resource] | Yes |
| `DELETE` | `/v1/[resources]/{id}` | Delete [resource] | Yes |
| `GET` | `/health` | Health check | No |
| `GET` | `/v1/me` | Current authenticated user | Yes |

**Add secondary resources as needed:**

| Method | Path | Summary | Auth Required |
|--------|------|---------|--------------|
| | | | |

---

## OpenAPI Info Block

Paste this into your FastAPI `create_app()` or your `openapi.yaml` root:

```yaml
openapi: "3.1.0"
info:
  title: "[SERVICE_NAME] API"
  version: "1.0.0"
  description: |
    [Full description. Supports Markdown. Include: purpose, key concepts, rate limits.]
  contact:
    email: "[api-support@example.com]"
  license:
    name: "[MIT / Apache-2.0 / Proprietary]"

servers:
  - url: "https://[service-name].example.com/v1"
    description: Production
  - url: "https://[service-name]-staging.example.com/v1"
    description: Staging
  - url: "http://localhost:8000/v1"
    description: Local development

tags:
  - name: "[resource_1]"
    description: "[Resource 1] management operations"
  - name: "[resource_2]"
    description: "[Resource 2] management operations"
  - name: health
    description: Health and readiness checks

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    [Resource]:
      type: object
      required: [id, created_at]
      properties:
        id:
          type: string
          format: uuid
          example: "550e8400-e29b-41d4-a716-446655440000"
        created_at:
          type: string
          format: date-time
        # Add resource-specific fields here

    Error:
      type: object
      required: [detail, type]
      properties:
        detail:
          type: string
        type:
          type: string

  responses:
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    Unauthorized:
      description: Missing or invalid authentication
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
```

---

## Auth Pattern

Select and document the auth pattern before writing any route:

### Option A — Bearer JWT (Recommended)
```python
# core/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"],
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
```

### Option B — API Key
```python
from fastapi import Security
from fastapi.security.api_key import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key
```

**Selected pattern:** [ ] Bearer JWT  [ ] API Key  [ ] OAuth 2.0

---

## Observability Hooks

Wire these before going to staging:

### Structured Logging
```python
# logger.py
import structlog
log = structlog.get_logger()

# Usage in route handlers:
log.info("request.received", path=request.url.path, user_id=current_user["sub"])
```

### Health Endpoint
```python
@app.get("/health", tags=["health"])
async def health() -> dict:
    return {
        "status": "ok",
        "version": settings.version,
        "db": await check_db_connection(),
    }
```

### Metrics (Prometheus)
```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

### Tracing (OpenTelemetry)
```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
```

**Observability checklist:**
- [ ] Structured logging configured
- [ ] `/health` endpoint returns `200 OK` with DB status
- [ ] `/metrics` endpoint exposed (Prometheus or compatible)
- [ ] Distributed tracing instrumented
- [ ] Error rates alertable in Grafana / Datadog

---

## Deployment Notes

### Docker

```dockerfile
# Multi-stage build — see [[Docker_Multi_Stage_Builds]]
FROM python:3.12-slim AS base
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM base AS production
COPY src/ ./src/
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Environment Variables

```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
SECRET_KEY=changeme
API_KEY=changeme
LOG_LEVEL=INFO
DEBUG=false
VERSION=1.0.0
```

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run with hot reload
uvicorn src.main:app --reload --port 8000

# Run tests
pytest tests/ -v

# View API docs
open http://localhost:8000/docs
```

### Production Deployment Checklist
- [ ] `DEBUG=false` in production environment
- [ ] `SECRET_KEY` rotated from default
- [ ] Database connection pool sized for expected load
- [ ] Rate limiting configured (see [[API_Rate_Limiting_with_FastAPI]])
- [ ] Kubernetes readiness probe pointed at `/health`
- [ ] Resource limits set (CPU/memory)
- [ ] Horizontal Pod Autoscaler configured

---

## Conclusion

This blueprint is complete when every placeholder is filled, the OpenAPI contract is finalized, and the observability hooks are wired. Do not begin implementation until the endpoint table and auth pattern are confirmed — changing these after build starts is expensive. Reference [[Backend_Service_Architecture_FastAPI]] for implementation patterns and [[Backend_API_Production_Readiness_Checklist]] before go-live.
