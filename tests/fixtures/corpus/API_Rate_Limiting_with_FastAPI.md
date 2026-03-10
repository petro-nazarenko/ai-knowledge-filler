---
title: "API Rate Limiting Implementation with FastAPI"
type: guide
domain: backend-engineering
level: intermediate
status: active
version: v1.0
tags: [rate-limiting, fastapi, api, backend, throttling]
related:
  - "[[REST_API_Versioning_Strategies]]"
  - "[[Backend_API_Production_Readiness]]"
  - "[[Application_Security_Checklist]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Step-by-step guide to implementing API rate limiting in FastAPI applications using in-memory counters, Redis-backed sliding windows, and middleware.

## Prerequisites

- FastAPI application running
- Python 3.10+
- Optional: Redis for distributed rate limiting

## Rate Limiting Strategies

| Strategy | Use Case | Accuracy |
|----------|----------|----------|
| Fixed window | Simple APIs | Low |
| Sliding window | Most production APIs | High |
| Token bucket | Burst-tolerant APIs | High |
| Leaky bucket | Strict output rate | High |

## Step 1: Simple Fixed Window (In-Memory)

```python
import time
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

# {client_ip: [timestamp, ...]}
request_counts: dict = defaultdict(list)
RATE_LIMIT = 100  # requests
WINDOW_SECONDS = 60

def is_rate_limited(client_ip: str) -> bool:
    now = time.time()
    window_start = now - WINDOW_SECONDS
    # Remove expired timestamps
    request_counts[client_ip] = [
        t for t in request_counts[client_ip] if t > window_start
    ]
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        return True
    request_counts[client_ip].append(now)
    return False

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    if is_rate_limited(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return await call_next(request)
```

## Step 2: Redis-Backed Sliding Window

```python
import redis
import time

r = redis.Redis(host="localhost", port=6379, db=0)

def sliding_window_check(client_id: str, limit: int, window: int) -> bool:
    now = time.time()
    key = f"rate:{client_id}"
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window)
    results = pipe.execute()
    count = results[2]
    return count > limit
```

## Step 3: Rate Limit Headers

Return standard headers to help clients self-throttle:

```python
from fastapi import Response

@app.get("/api/data")
async def get_data(response: Response, request: Request):
    client_ip = request.client.host
    remaining = get_remaining_requests(client_ip)
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
    return {"data": "..."}
```

## Step 4: Per-Route Rate Limits

```python
from functools import wraps

def rate_limit(limit: int, window: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if is_rate_limited(request.client.host, limit, window):
                raise HTTPException(status_code=429)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

@app.get("/expensive-endpoint")
@rate_limit(limit=10, window=60)
async def expensive_op(request: Request):
    return {"result": "..."}
```

## Production Considerations

- **Use Redis** for distributed deployments (multiple app instances)
- **Rate limit by API key**, not just IP (prevents IP spoofing bypass)
- **Differentiate tiers** — free: 100/min, pro: 1000/min
- **Retry-After header** — tell clients when to retry
- **Monitor 429 rate** — spike indicates abuse or misconfigured client

## Conclusion

Start with in-memory sliding window for single-instance deployments. Move to Redis-backed implementation when scaling horizontally. Always return standard rate limit headers to improve client experience.
