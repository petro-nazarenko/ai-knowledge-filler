---
title: "REST API Versioning Strategies"
type: reference
domain: api-design
level: intermediate
status: active
version: v1.0
tags: [api, versioning, rest, backend, compatibility]
related:
  - "[[API_Rate_Limiting_with_FastAPI]]"
  - "[[API_Documentation_Structure_OpenAPI]]"
  - "[[Backend_API_Production_Readiness]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for REST API versioning strategies — approaches for evolving APIs without breaking existing clients.

## Versioning Strategies

### 1. URL Path Versioning (Most Common)

```
GET /v1/users/123
GET /v2/users/123
```

**Pros:** Explicit, cacheable, easy to route
**Cons:** URL pollution, must maintain multiple routes
**Use when:** Public APIs, long-lived version support

### 2. Query Parameter Versioning

```
GET /users/123?version=1
GET /users/123?version=2
```

**Pros:** Stable URLs, simple rollout
**Cons:** Easily forgotten, poor cache behavior
**Use when:** Internal APIs, gradual migrations

### 3. Header Versioning

```
GET /users/123
Accept: application/vnd.myapi.v2+json
```

**Pros:** Clean URLs, HTTP-native
**Cons:** Hidden from view, harder to test in browser
**Use when:** API consumers are sophisticated clients

### 4. Content Negotiation (Media Type)

```
Accept: application/json; version=2
```

**Pros:** RFC-compliant, semantic
**Cons:** Complex to implement and document
**Use when:** Standards-compliance required

## Versioning Rules

### Breaking vs Non-Breaking Changes

| Change Type | Breaking | Action Required |
|-------------|----------|----------------|
| Add optional field | No | Deploy without version bump |
| Remove field | Yes | New major version |
| Change field type | Yes | New major version |
| Add required field | Yes | New major version |
| Change HTTP method | Yes | New major version |
| Change status code | Maybe | Evaluate per case |

### Deprecation Protocol

1. Announce deprecation with sunset date in response headers
2. Add `Deprecation` and `Sunset` headers
3. Maintain deprecated version for deprecation period (min 6 months)
4. Return 410 Gone after sunset date

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 01 Jan 2027 00:00:00 GMT
Link: <https://api.example.com/v2/users>; rel="successor-version"
```

## Version Lifecycle

```
v1 (active) → v1 (deprecated) → v1 (sunset) → v1 (removed)
v2 (active) ─────────────────────────────────────────────→
```

## Implementation (FastAPI)

```python
from fastapi import APIRouter

v1_router = APIRouter(prefix="/v1")
v2_router = APIRouter(prefix="/v2")

@v1_router.get("/users/{user_id}")
def get_user_v1(user_id: int):
    return {"id": user_id, "name": "..."}  # v1 schema

@v2_router.get("/users/{user_id}")
def get_user_v2(user_id: int):
    return {"id": user_id, "full_name": "...", "email": "..."}  # v2 schema
```

## Recommendations

- **Start with URL versioning** — simplest for most teams
- **Version at the resource level**, not endpoint level
- **Document all versions** in OpenAPI spec
- **Never remove versions without a sunset period**
- **Test both versions** in CI/CD

## Conclusion

URL path versioning is the industry standard for public REST APIs due to its simplicity and cacheability. Choose based on your client sophistication and operational capacity to maintain multiple versions.
