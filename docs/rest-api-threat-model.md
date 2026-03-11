---
title: "REST API Threat Model"
type: reference
domain: akf-docs
level: intermediate
status: active
version: v1.0
tags: [security, rest-api, threat-model, auth, rate-limits, pii]
related:
  - "wiki/REST-API.md"
  - "SECURITY.md"
created: 2026-03-11
updated: 2026-03-11
---

## Scope

This model covers the AKF FastAPI server in `akf/server.py` and deployed REST endpoints.

## Endpoint Classification

Public (no auth by default in dev):
- `GET /health`
- `GET /ready`

Protected (auth required in prod, optional in dev if `AKF_API_KEY` is unset):
- `GET /metrics`
- `GET /v1/models`
- `POST /v1/generate`
- `POST /v1/validate`
- `POST /v1/batch`
- `POST /v1/ask`

Internal-only recommendation:
- Restrict `/metrics` to internal networks/reverse proxy allowlist.
- Expose `/health` and `/ready` only if required by orchestration.

## Auth Model

- Environment gate:
  - `AKF_ENV=prod`: `AKF_API_KEY` is mandatory at startup.
  - `AKF_ENV=dev`: auth is optional unless key is configured.
- Transport auth:
  - Bearer token via `Authorization: Bearer <AKF_API_KEY>`.
- Tenant attribution:
  - Optional `X-AKF-Tenant-ID` header for telemetry segregation.

Risks:
- Dev deployments can accidentally run without auth.
- Single static API key increases blast radius if leaked.

Mitigations:
- Enforce `AKF_ENV=prod` in production manifests.
- Rotate `AKF_API_KEY` periodically and on personnel changes.
- Run behind trusted ingress (TLS termination, IP filtering, WAF).

## Rate Limiting and Abuse Controls

Implemented in `slowapi` with per-endpoint quotas:
- `AKF_RATE_LIMIT_GENERATE` default `10/minute`
- `AKF_RATE_LIMIT_ASK` default `10/minute`
- `AKF_RATE_LIMIT_VALIDATE` default `30/minute`
- `AKF_RATE_LIMIT_BATCH` default `3/minute`
- Global default `AKF_RATE_LIMIT_DEFAULT` `60/minute`

Additional controls:
- `AKF_MAX_REQUEST_BYTES` to cap payload size (default 1 MiB).
- `AKF_MAX_CONCURRENCY` to cap expensive concurrent POST workload.

## Logging, Telemetry, and PII

Current behavior:
- Request metadata logged: method, path, status, latency, request_id.
- Telemetry events written to JSONL (`AKF_TELEMETRY_PATH`).
- User content can appear in generated output and ask payloads.

PII policy:
- Treat prompts/content as potentially sensitive.
- Do not log raw secrets or full bearer tokens.
- Protect telemetry files with filesystem ACLs and retention policy.

Operational recommendations:
- Centralize logs with redaction at ingestion.
- Define retention: short for request logs, longer for aggregated metrics.
- Include 401/429 anomaly alerts.

## Primary Threats and Controls

- Unauthorized access:
  - Threat: missing auth in production or key leak.
  - Control: mandatory prod key, rotation, restricted network perimeter.

- Abuse/DoS:
  - Threat: high-rate expensive generation/ask requests.
  - Control: per-route limits, concurrency semaphore, body-size limits.

- Prompt/data leakage:
  - Threat: sensitive content in logs/telemetry.
  - Control: redaction policy, protected storage, minimal payload logging.

- Path traversal / unsafe write path:
  - Threat: attacker-controlled output path.
  - Control: `_safe_output_path()` allows filename-only and resolves under `AKF_OUTPUT_DIR`.

- Dependency/supply-chain drift:
  - Threat: stale GitHub Action versions.
  - Control: Dependabot + pinned major versions + regular CI updates.

## Residual Risk

- API key model is coarse-grained (no scopes, no per-tenant keys).
- No built-in audit trail for auth failures beyond logs.
- No native DLP for prompt/content payloads.

## Near-Term Hardening Backlog

1. Add optional per-tenant API keys and key scopes.
2. Add configurable deny/allow list for endpoints at startup.
3. Add structured redaction helper for sensitive fields before logging.
4. Publish branch protection guidance for Codecov and required checks.
