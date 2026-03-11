# REST API Threat Model

This page summarizes core threats and controls for AKF REST API deployments.

---

## Scope

Covers `akf/server.py` endpoints and runtime controls for auth, limits, logging, and data handling.

---

## Endpoint Classification

Public (typically exposed for platform checks):
- `GET /health`
- `GET /ready`

Protected (auth required in prod):
- `GET /metrics`
- `GET /v1/models`
- `POST /v1/generate`
- `POST /v1/validate`
- `POST /v1/batch`
- `POST /v1/ask`

Operational recommendation:
- Keep `/metrics` internal-only via reverse proxy/network policy.

---

## Auth Model

- `AKF_ENV=prod` requires `AKF_API_KEY` at startup.
- Requests use `Authorization: Bearer <AKF_API_KEY>` when auth is enabled.
- Optional `X-AKF-Tenant-ID` can be used for tenant attribution.

Primary risk:
- Accidental `dev` deployments without auth.

Primary mitigation:
- Enforce `AKF_ENV=prod` in production manifests and rotate API keys.

---

## Rate Limiting and Abuse Controls

Built-in per-route limits:
- `AKF_RATE_LIMIT_GENERATE` (`10/minute` default)
- `AKF_RATE_LIMIT_ASK` (`10/minute` default)
- `AKF_RATE_LIMIT_VALIDATE` (`30/minute` default)
- `AKF_RATE_LIMIT_BATCH` (`3/minute` default)

Additional guards:
- `AKF_MAX_REQUEST_BYTES` for payload cap
- `AKF_MAX_CONCURRENCY` for expensive POST workloads

---

## Logging and PII

- Request metadata is logged (method/path/status/latency/request_id).
- Treat prompts and content as potentially sensitive.
- Do not log bearer tokens or raw secrets.
- Protect telemetry/log storage and enforce retention rules.

---

## Supply Chain

- Keep Dependabot enabled for GitHub Actions and Python dependencies.
- Use Node 24-compatible action majors.
- If using self-hosted runners, keep versions current (`>=2.327.1`, and `>=2.329.0` for container-action credential persistence scenarios).

---

## Short Hardening Backlog

1. Optional per-tenant/scoped API keys.
2. Startup deny/allow list for endpoint exposure.
3. Centralized log redaction for sensitive payload fields.
4. Branch protection with explicit required checks for coverage policy.
