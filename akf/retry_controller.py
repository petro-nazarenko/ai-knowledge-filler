"""
AKF Phase 2.1 — Retry Controller
ADR-001: Validation Layer Architecture

The ONLY non-deterministic component in the pipeline.
Contains the LLM call. All other stages are pure functions.

Convergence protection:
  - max_attempts: 3
  - Hash comparison: abort if LLM returns identical output
  - E-code convergence: abort if same (field, E-code) pair fails twice

Phase 2.3 — Telemetry:
  GenerationAttemptEvent emitted after each LLM call.
  Writer is optional — pass writer=None to disable telemetry.
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Callable, Optional

from akf.error_normalizer import normalize_errors
from akf.telemetry import (
    GenerationAttemptEvent,
    TelemetryWriter,
    ValidationErrorRecord,
)
from akf.validation_error import ErrorCode, ValidationError

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# Callable that takes a document string + retry payload text → new document string
GenerateFn = Callable[[str, str], str]

# Callable that takes a document string → list of ValidationErrors
ValidateFn = Callable[[str], list[ValidationError]]


@dataclass
class RetryResult:
    """Outcome of a retry cycle."""

    success: bool
    document: str  # final document (valid or last attempt)
    attempts: int  # how many LLM calls were made
    abort_reason: Optional[str]  # set when success=False
    errors: list[ValidationError]  # remaining errors if not success

    def __str__(self) -> str:
        if self.success:
            return f"RetryResult(success=True, attempts={self.attempts})"
        return (
            f"RetryResult(success=False, attempts={self.attempts}, "
            f"abort_reason={self.abort_reason!r})"
        )


# ---------------------------------------------------------------------------
# Retry Controller
# ---------------------------------------------------------------------------

MAX_ATTEMPTS = 3


def run_retry_loop(
    document: str,
    errors: list[ValidationError],
    generate_fn: GenerateFn,
    validate_fn: ValidateFn,
    max_attempts: int = MAX_ATTEMPTS,
    # ── Telemetry (Phase 2.3) ──────────────────────────────────────────────
    generation_id: Optional[str] = None,
    document_id: Optional[str] = None,
    schema_version: str = "1.0.0",
    model: str = "unknown",
    temperature: float = 0,
    top_p: float = 1,
    writer: Optional[TelemetryWriter] = None,
) -> RetryResult:
    """
    Execute the controlled repair loop.

    Args:
        document:       Raw LLM output that failed validation.
        errors:         Validation errors from first pass.
        generate_fn:    LLM callable — takes (document, retry_prompt) → new document.
        validate_fn:    Validation callable — takes document → list[ValidationError].
        max_attempts:   Hard cap on LLM calls (default 3).
        generation_id:  UUID shared across all attempts for this generation session.
                        Required for telemetry. Pass new_generation_id() from caller.
        document_id:    File identifier (basename without extension).
        schema_version: Schema version active at generation time.
        model:          LLM model identifier. Required to separate model drift
                        from ontology drift in telemetry.
        temperature:    Must be 0 per Determinism Contract.
        top_p:          Must be 1 per Determinism Contract.
        writer:         TelemetryWriter instance. Pass None to disable telemetry.

    Returns:
        RetryResult with success status, final document, attempt count.
    """
    seen_hashes: set[str] = set()

    current_doc = document
    current_errors = errors

    for attempt in range(1, max_attempts + 1):
        # Build retry payload
        payload = normalize_errors(current_errors)

        if not payload.has_blocking_errors:
            return RetryResult(
                success=True,
                document=current_doc,
                attempts=attempt - 1,
                abort_reason=None,
                errors=[],
            )

        # Call LLM (non-deterministic) — timed for telemetry
        retry_prompt = payload.to_prompt_text()
        t0 = time.monotonic()
        new_doc = generate_fn(current_doc, retry_prompt)
        duration_ms = int((time.monotonic() - t0) * 1000)

        # Hash check FIRST — detect identical regeneration
        doc_hash = _hash(new_doc)
        if doc_hash in seen_hashes:
            _emit_attempt(
                writer=writer,
                generation_id=generation_id,
                document_id=document_id,
                schema_version=schema_version,
                attempt=attempt,
                max_attempts=max_attempts,
                is_final_attempt=True,
                converged=False,
                errors=current_errors,
                model=model,
                temperature=temperature,
                top_p=top_p,
                duration_ms=duration_ms,
            )
            return RetryResult(
                success=False,
                document=new_doc,
                attempts=attempt,
                abort_reason="identical_output: LLM returned same document twice",
                errors=current_errors,
            )
        seen_hashes.add(doc_hash)

        # Validate new document
        new_errors = validate_fn(new_doc)
        blocking = [e for e in new_errors if e.severity.value == "error"]

        if not blocking:
            _emit_attempt(
                writer=writer,
                generation_id=generation_id,
                document_id=document_id,
                schema_version=schema_version,
                attempt=attempt,
                max_attempts=max_attempts,
                is_final_attempt=True,
                converged=True,
                errors=[],
                model=model,
                temperature=temperature,
                top_p=top_p,
                duration_ms=duration_ms,
            )
            return RetryResult(
                success=True,
                document=new_doc,
                attempts=attempt,
                abort_reason=None,
                errors=new_errors,  # may contain warnings
            )

        # Convergence check — same (field, E-code) failing consecutively → abort
        abort_reason = _check_convergence(current_errors, blocking)
        is_final = bool(abort_reason) or attempt == max_attempts

        _emit_attempt(
            writer=writer,
            generation_id=generation_id,
            document_id=document_id,
            schema_version=schema_version,
            attempt=attempt,
            max_attempts=max_attempts,
            is_final_attempt=is_final,
            converged=False,
            errors=blocking,
            model=model,
            temperature=temperature,
            top_p=top_p,
            duration_ms=duration_ms,
        )

        if abort_reason:
            return RetryResult(
                success=False,
                document=new_doc,
                attempts=attempt,
                abort_reason=abort_reason,
                errors=blocking,
            )

        current_doc = new_doc
        current_errors = blocking

    # Exhausted all attempts
    return RetryResult(
        success=False,
        document=current_doc,
        attempts=max_attempts,
        abort_reason=f"max_attempts_reached: failed after {max_attempts} retries",
        errors=current_errors,
    )


# ---------------------------------------------------------------------------
# Telemetry helpers (Phase 2.3)
# ---------------------------------------------------------------------------


def _emit_attempt(
    *,
    writer: Optional[TelemetryWriter],
    generation_id: Optional[str],
    document_id: Optional[str],
    schema_version: str,
    attempt: int,
    max_attempts: int,
    is_final_attempt: bool,
    converged: bool,
    errors: list[ValidationError],
    model: str,
    temperature: float,
    top_p: float,
    duration_ms: int,
) -> None:
    """Emit GenerationAttemptEvent if writer and generation_id are provided.

    Silent no-op when writer=None — telemetry is optional.
    Errors in telemetry write are caught and suppressed to never
    interrupt the generation pipeline (observe, never influence).
    """
    if writer is None or generation_id is None:
        return

    try:
        event = GenerationAttemptEvent(
            generation_id=generation_id,
            document_id=document_id or "unknown",
            schema_version=schema_version,
            attempt=attempt,
            max_attempts=max_attempts,
            is_final_attempt=is_final_attempt,
            converged=converged,
            errors=[_to_record(e) for e in errors],
            model=model,
            temperature=temperature,
            top_p=top_p,
            duration_ms=duration_ms,
        )
        writer.write(event)
    except Exception:
        # Telemetry failure must never interrupt the pipeline.
        pass


def _to_record(e: ValidationError) -> ValidationErrorRecord:
    """Convert ValidationError → ValidationErrorRecord for telemetry."""
    return ValidationErrorRecord(
        code=e.code.value if isinstance(e.code, ErrorCode) else str(e.code),
        field=e.field,
        expected=e.expected if hasattr(e, "expected") else None,
        received=e.received if hasattr(e, "received") else None,
        severity=e.severity.value if hasattr(e.severity, "value") else str(e.severity),
    )


# ---------------------------------------------------------------------------
# Convergence helpers (deterministic)
# ---------------------------------------------------------------------------


def _check_convergence(
    previous_errors: list[ValidationError],
    new_errors: list[ValidationError],
) -> Optional[str]:
    """
    Check if any (field, E-code) pair failed in BOTH consecutive attempts.
    If so, return abort reason. Otherwise return None.

    Rule from ADR-001:
      Same E-code twice for same field (consecutive) → abort.
    """
    previous_keys = {(e.field, e.code) for e in previous_errors}
    for error in new_errors:
        key = (error.field, error.code)
        if key in previous_keys:
            return (
                f"convergence_failure: field='{error.field}' "
                f"code={error.code.value} failed on consecutive attempts"
            )
    return None


def _hash(text: str) -> str:
    """SHA-256 hash of document text for identity comparison."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
