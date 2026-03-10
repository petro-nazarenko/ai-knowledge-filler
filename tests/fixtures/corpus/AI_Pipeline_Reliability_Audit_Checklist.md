---
title: "AI Pipeline Reliability Audit Checklist"
type: checklist
domain: ai-system
level: advanced
status: active
tags: [ai-pipeline, reliability, audit, production, checklist]
related:
  - "[[LLM_Output_Validation_Pipeline_Architecture]]"
  - "[[Deterministic_Retry_Logic]]"
  - "[[Schema_as_Contract_Pattern]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Pre-production reliability audit checklist for LLM-powered pipelines. Covers schema contracts, retry logic, observability, error handling, and operational readiness.

## Schema and Validation

- [ ] Output schema defined and versioned before pipeline deployment
- [ ] All required fields enumerated in schema contract
- [ ] Enum constraints enforced at validation layer (not just prompt)
- [ ] Domain taxonomy loaded from config, not hardcoded
- [ ] Validation is idempotent (same input → same result)
- [ ] Validation errors classified as blocking vs non-blocking
- [ ] Schema version tracked in telemetry events

## Retry Logic

- [ ] Max retry attempts configured (recommend: 3)
- [ ] Retry prompt includes original errors as context
- [ ] Backoff strategy implemented (exponential preferred)
- [ ] Retry loop has explicit convergence check
- [ ] Rejected candidates logged for analysis
- [ ] Retry count included in telemetry/output metadata

## Error Handling

- [ ] LLM timeout errors handled separately from logic errors
- [ ] Empty response detection and handling
- [ ] Auth/rate-limit errors distinguished from transient errors
- [ ] Error normalization before building retry prompts
- [ ] Pipeline does not silently swallow validation failures
- [ ] Fatal errors trigger immediate abort (no retry)

## Observability

- [ ] Telemetry events emitted at each pipeline stage
- [ ] Generation ID assigned per request for traceability
- [ ] Attempt count recorded in output metadata
- [ ] Duration metrics captured (ms)
- [ ] Provider name and model version logged
- [ ] Failed generations recorded (not only successes)

## Commit and Storage

- [ ] Files written atomically (commit gate pattern)
- [ ] Path traversal prevention implemented
- [ ] Filename sanitization for reserved OS names
- [ ] Output directory created if missing
- [ ] File collision handling (timestamp suffix)

## Provider Resilience

- [ ] Provider fallback chain configured
- [ ] API key validation at startup (not first request)
- [ ] Timeout values set on all provider calls
- [ ] Multiple provider availability tested before deployment

## Configuration Management

- [ ] Schema config externalized (not hardcoded)
- [ ] Config loaded from file, not environment strings
- [ ] Config changes require version bump
- [ ] Defaults defined for all optional config values

## Pre-Production Final Review

- [ ] End-to-end test with valid prompt → valid output
- [ ] End-to-end test with invalid prompt → retry → success
- [ ] End-to-end test with persistently invalid → graceful failure
- [ ] Telemetry events validated in staging
- [ ] Load test (concurrent generation requests)
- [ ] Recovery test (provider outage simulation)

## Sign-Off

**Reviewed by:** _______________
**Environment:** _______________
**Date:** _______________
**Approved:** [ ] Yes [ ] No
