---
title: "OAuth 2.0 Implementation for API Authentication"
type: guide
domain: security
level: intermediate
status: active
version: v1.0
tags: [oauth2, authentication, security, api, authorization]
related:
  - "[[Application_Security_Checklist_REST_APIs]]"
  - "[[Zero_Trust_Architecture_Principles]]"
  - "[[REST_API_Versioning_Strategies]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to implementing OAuth 2.0 for API authentication — covering grant types, token management, and integration with FastAPI.

## Prerequisites

- Understanding of HTTP and REST APIs
- Python 3.10+ with FastAPI
- Basic cryptography concepts (signing, hashing)

## OAuth 2.0 Grant Types

| Grant Type | Use Case | Security Level |
|-----------|----------|----------------|
| Authorization Code + PKCE | Web/mobile apps | High |
| Client Credentials | Service-to-service | High |
| Device Code | CLI / smart devices | High |
| Resource Owner Password | Legacy only | Low (avoid) |
| Implicit | Deprecated | Very Low (avoid) |

## Step 1: Authorization Code Flow with PKCE

```
Client                    Auth Server              Resource Server
  |                           |                         |
  |--- [1] Auth Request + ───→|                         |
  |    code_challenge         |                         |
  |                           |                         |
  |←── [2] Auth Code ────────|                         |
  |                           |                         |
  |--- [3] Token Request + ──→|                         |
  |    code_verifier          |                         |
  |                           |                         |
  |←── [4] Access Token ─────|                         |
  |                           |                         |
  |─────── [5] API Request + Bearer Token ────────────→|
  |←────── [6] Resource ──────────────────────────────|
```

## Step 2: JWT Access Token Structure

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key-2026-03"
  },
  "payload": {
    "sub": "user-123",
    "iss": "https://auth.example.com",
    "aud": "https://api.example.com",
    "exp": 1741651200,
    "iat": 1741647600,
    "scope": "read:orders write:orders"
  }
}
```

## Step 3: Token Validation in FastAPI

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

security = HTTPBearer()
jwks_client = PyJWKClient("https://auth.example.com/.well-known/jwks.json")

def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience="https://api.example.com",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

@app.get("/orders")
def get_orders(token_payload: dict = Depends(verify_token)):
    user_id = token_payload["sub"]
    return get_user_orders(user_id)
```

## Step 4: Scope-Based Authorization

```python
def require_scope(required_scope: str):
    def checker(payload: dict = Depends(verify_token)):
        scopes = payload.get("scope", "").split()
        if required_scope not in scopes:
            raise HTTPException(status_code=403, detail="Insufficient scope")
        return payload
    return checker

@app.delete("/orders/{order_id}")
def delete_order(
    order_id: str,
    payload: dict = Depends(require_scope("write:orders"))
):
    ...
```

## Token Lifecycle Management

| Token Type | TTL | Storage |
|-----------|-----|---------|
| Access Token | 15–60 min | Memory/sessionStorage |
| Refresh Token | 7–30 days | HttpOnly cookie |
| API Key | No expiry | Encrypted server-side |

## Security Requirements

- **Never store access tokens in localStorage** (XSS vulnerable)
- **Rotate refresh tokens** on each use
- **Validate `aud` claim** to prevent token confusion attacks
- **Check `iss` claim** against expected auth server
- **Use RS256/ES256**, not HS256 for distributed systems
- **Implement token revocation** (Redis blocklist or short TTL)

## Conclusion

OAuth 2.0 with Authorization Code + PKCE is the recommended pattern for user-facing applications. Client Credentials for service-to-service. Always validate JWT claims on every request — never trust tokens without verification.
