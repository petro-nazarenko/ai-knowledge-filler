---
title: "Deterministic Retry Logic in LLM Pipelines"
type: guide
domain: ai-system
level: intermediate
status: active
version: v1.0
tags: [retry, llm, pipeline, determinism, error-handling]
related:
  - "[[LLM_Output_Validation_Pipeline_Architecture|implements]]"
  - "[[Schema_as_Contract_Pattern|references]]"
  - "[[AI_Pipeline_Reliability_Audit]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to implementing deterministic retry logic in LLM pipelines — ensuring that validation failures trigger structured, reproducible repair attempts rather than random regeneration.

## Prerequisites

- Working LLM pipeline with validation layer
- Understanding of error classification (blocking vs non-blocking)
- Access to structured error objects with field and code information

## Why Deterministic Retry?

Standard LLM retry: re-send the original prompt and hope for a different result.

Deterministic retry: construct a targeted repair prompt from the validation errors, making the LLM's correction task explicit and bounded.

## Step 1: Collect Blocking Errors

```python
from akf.validator import validate
from akf.validation_error import Severity

def get_blocking_errors(document: str) -> list:
    all_errors = validate(document)
    return [e for e in all_errors if e.severity == Severity.ERROR]
```

## Step 2: Build Repair Prompt

```python
def build_repair_prompt(document: str, errors: list) -> str:
    error_lines = "\n".join(
        f"- Field '{e.field}': {e.code} — expected {e.expected}, got {e.received}"
        for e in errors
    )
    return f"""The following document has validation errors. Fix ONLY the listed errors.
Do not change any other content.

ERRORS:
{error_lines}

DOCUMENT:
{document}"""
```

## Step 3: Implement the Retry Loop

```python
MAX_ATTEMPTS = 3

def run_retry_loop(document: str, errors: list, generate_fn, validate_fn) -> dict:
    attempts = 1

    for attempt in range(2, MAX_ATTEMPTS + 1):
        repair_prompt = build_repair_prompt(document, errors)
        document = generate_fn(document, repair_prompt)
        errors = [e for e in validate_fn(document) if e.severity == "error"]
        attempts = attempt

        if not errors:
            break

    return {
        "document": document,
        "errors": errors,
        "attempts": attempts,
        "converged": len(errors) == 0,
    }
```

## Step 4: Handle Non-Convergence

```python
def commit_or_warn(result: dict, output_path: Path):
    if result["converged"]:
        output_path.write_text(result["document"], encoding="utf-8")
        print(f"Saved: {output_path}")
    else:
        # Save anyway but warn
        output_path.write_text(result["document"], encoding="utf-8")
        print(f"Warning: {len(result['errors'])} errors remain after {result['attempts']} attempts")
```

## Determinism Principles

### 1. Error-Driven Prompts
Each retry prompt is constructed solely from the validation errors — not from random variation. Same errors → same repair prompt.

### 2. Temperature = 0
Use `temperature=0` for retry attempts to maximize reproducibility. Initial generation may use higher temperature.

### 3. Fixed Attempt Count
Do not vary max attempts based on error count or type. Fixed bounds make behavior predictable.

### 4. Idempotent Validation
Validation must return identical results for identical documents. Time-dependent checks break determinism.

## Telemetry Integration

```python
# Emit event for each retry attempt
writer.write(RetryEvent(
    generation_id=generation_id,
    attempt=attempt,
    errors=[e.code for e in errors],
    converged=len(errors) == 0,
))
```

## Conclusion

Deterministic retry transforms LLM repair from a stochastic process into a controlled feedback loop. By building repair prompts from structured error data, each attempt is targeted and reproducible — making the pipeline debuggable and auditable.
