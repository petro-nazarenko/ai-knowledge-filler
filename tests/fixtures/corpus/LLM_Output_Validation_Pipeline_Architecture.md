---
title: "LLM Output Validation Pipeline Architecture"
type: reference
domain: ai-system
level: advanced
status: active
version: v1.0
tags: [llm, validation, pipeline, architecture, ai-engineering]
related:
  - "[[Schema_as_Contract_Pattern]]"
  - "[[Deterministic_Retry_Logic]]"
  - "[[AI_Pipeline_Reliability_Audit]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference architecture for validating LLM outputs in production AI pipelines. Covers schema enforcement, error classification, retry strategies, and observability.

## Architecture Overview

```
LLM Request → Generate → Parse → Validate → [Pass | Retry Loop] → Commit → Output
```

## Core Components

### 1. Schema Contract Layer

Defines the expected output structure before generation:
- YAML frontmatter spec (required fields, enum constraints)
- JSON Schema or Pydantic models for structured outputs
- Domain taxonomy enforcement

### 2. Parser

Extracts structured data from raw LLM output:
- Frontmatter extraction (regex or YAML parser)
- Content body separation
- Encoding normalization

### 3. Validation Engine

Binary judgment: VALID or INVALID. Checks:

| Check | Error Code | Severity |
|-------|-----------|----------|
| Required fields present | E002 | ERROR |
| Enum field values | E001 | ERROR |
| Domain taxonomy match | E006 | ERROR |
| Date format ISO 8601 | E003 | ERROR |
| Date sequence (created ≤ updated) | E007 | ERROR |
| Tags min count (≥3) | E004 | ERROR |
| Related links present | W001 | WARNING |

### 4. Retry Controller

Triggered when blocking errors exist:
- Max attempts: 3 (configurable)
- Prompt reconstruction with error context
- Exponential backoff between attempts
- Convergence tracking

### 5. Commit Gate

Final gatekeeper before file write:
- Re-validates after retry loop
- Writes only if all blocking errors resolved
- Falls back to raw write with warning if not converged

### 6. Telemetry Emitter

Emits structured events at each stage:
- `generation.started` / `generation.completed`
- `validation.failed` / `retry.attempted`
- `commit.success` / `commit.blocked`

## Validation Strategy

### Blocking vs Non-blocking Errors

```
Blocking (prevent commit):
  - Missing required fields
  - Invalid enum values
  - Invalid domain
  - Invalid date format

Non-blocking (warnings only):
  - Missing related links
  - Deprecated field values
```

### Error Normalization

Errors are normalized before building retry prompts:
- Grouped by field
- Ranked by severity
- Formatted as actionable feedback to LLM

## Implementation Patterns

### Schema-First Design
Define validation schema before writing generation prompts. The schema acts as the contract between the system prompt and the validation layer.

### Idempotent Validation
Validation must produce identical results for identical inputs. Avoid time-dependent checks in the validation layer.

### Fail-Fast Parsing
If frontmatter cannot be parsed, abort immediately — do not attempt field-level checks on malformed YAML.

## Configuration

```yaml
# akf.yaml
enums:
  type: [concept, guide, reference, checklist]
  level: [beginner, intermediate, advanced]
  status: [draft, active, completed, archived]
taxonomy:
  domains:
    - ai-system
    - api-design
    - devops
```

## Conclusion

A robust LLM output validation pipeline enforces schema contracts at generation time, reducing hallucination and structural drift. The key insight: validate early, retry with context, commit atomically.
