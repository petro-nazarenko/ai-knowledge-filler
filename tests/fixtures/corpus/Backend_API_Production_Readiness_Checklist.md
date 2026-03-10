---
title: "Backend API Production Readiness Review"
type: checklist
domain: backend-engineering
level: intermediate
status: active
tags: [backend, api, production, readiness, checklist]
related:
  - "[[Backend_Service_Architecture_FastAPI]]"
  - "[[Application_Security_Checklist_REST_APIs]]"
  - "[[Observability_Stack_Design]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Comprehensive production readiness checklist for backend APIs. Covers functionality, performance, security, observability, and operational aspects.

## API Design

- [ ] All endpoints return consistent response shapes
- [ ] Error responses include `detail` and `type` fields
- [ ] HTTP status codes follow RFC 7231 conventions
- [ ] Pagination implemented on all list endpoints
- [ ] API versioning strategy in place
- [ ] OpenAPI spec generated and published
- [ ] Breaking changes documented and backward-compatibility maintained

## Authentication and Authorization

- [ ] All non-public endpoints require authentication
- [ ] Authorization checks at resource level (not just route level)
- [ ] Token expiration configured (access: 15–60 min, refresh: 7–30 days)
- [ ] API key management implemented for service-to-service
- [ ] Rate limiting per user/key configured

## Input Validation

- [ ] All request bodies validated with Pydantic or equivalent
- [ ] Path and query parameters validated
- [ ] File upload restrictions (type, size)
- [ ] Request size limit enforced

## Database

- [ ] Connection pooling configured
- [ ] All queries use parameterized statements (no string interpolation)
- [ ] Indexes on all frequently queried columns
- [ ] Slow query logging enabled
- [ ] Database migrations tested and reversible
- [ ] Connection timeout and retry logic implemented

## Performance

- [ ] Response times meet SLO targets (e.g., p99 < 200ms)
- [ ] Load tested at 2× expected peak traffic
- [ ] Caching implemented for read-heavy endpoints
- [ ] N+1 query patterns eliminated
- [ ] Background tasks offloaded for non-critical operations
- [ ] Database query performance profiled

## Reliability

- [ ] Health check endpoints implemented (`/healthz/live`, `/healthz/ready`)
- [ ] Graceful shutdown implemented (drain connections before stop)
- [ ] Circuit breakers for external dependencies
- [ ] Timeout values set on all external calls
- [ ] Retry logic with backoff for transient failures

## Observability

- [ ] Structured logging (JSON) to stdout
- [ ] Request/response logging with correlation IDs
- [ ] Prometheus metrics exported (`/metrics`)
- [ ] Key metrics instrumented: request rate, error rate, latency
- [ ] Alerts configured for SLO breaches
- [ ] Distributed tracing enabled (OpenTelemetry)

## Security

- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] Security headers present (see security checklist)
- [ ] CORS policy configured restrictively
- [ ] Secrets loaded from environment or secret manager (not code)
- [ ] Dependency CVE scan passing

## Deployment

- [ ] Docker image builds reproducibly
- [ ] Container runs as non-root user
- [ ] Resource limits set in deployment spec
- [ ] Rollback procedure tested and documented
- [ ] CI/CD pipeline deploys to staging before production
- [ ] Environment parity (staging ≈ production config)

## Documentation

- [ ] README with setup and local development instructions
- [ ] API reference (OpenAPI) up to date
- [ ] Runbook for common operational tasks
- [ ] Incident response plan documented

## Sign-Off

**Reviewed by:** _______________
**Service:** _______________
**Date:** _______________
**Approved:** [ ] Yes [ ] No
