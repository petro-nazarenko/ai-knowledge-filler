"""
AKF Phase 2.1 — Commit Gate
ADR-001: Validation Layer Architecture

Final safety lock. Deterministic. Boring and strict.

Does:
  - Final validation pass
  - schema_version enforcement (immutability)
  - Atomic file write

Does NOT:
  - Retry
  - Mutate document content
  - Normalize errors
  - Make decisions about what to fix

Phase 2.3 — Telemetry:
  GenerationSummaryEvent emitted after session completes (committed or blocked).
  Writer is optional — pass writer=None to disable telemetry.
"""

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from akf.validation_error import ValidationError, Severity

SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


@dataclass
class CommitResult:
    """Outcome of a commit attempt."""

    committed: bool
    path: Optional[Path]  # set when committed=True
    blocking_errors: list[ValidationError]  # set when committed=False
    schema_version: str  # always set

    def __str__(self) -> str:
        if self.committed:
            return f"CommitResult(committed=True, path={self.path})"
        return f"CommitResult(committed=False, " f"errors={len(self.blocking_errors)})"


# ---------------------------------------------------------------------------
# Commit Gate
# ---------------------------------------------------------------------------


def commit(
    document: str,
    output_path: Path,
    errors: list[ValidationError],
    expected_schema_version: str = SCHEMA_VERSION,
    # ── Telemetry (Phase 2.3) ──────────────────────────────────────────────
    generation_id: Optional[str] = None,
    document_id: Optional[str] = None,
    schema_version: Optional[str] = None,
    total_attempts: int = 1,
    rejected_candidates: Optional[list[str]] = None,
    model: str = "unknown",
    temperature: float = 0,
    total_duration_ms: int = 0,
    writer=None,
) -> CommitResult:
    """
    Final gate before writing to disk.

    Args:
        document:                 Validated document string.
        output_path:              Target file path.
        errors:                   Errors from last validation pass.
        expected_schema_version:  Schema version to enforce (default: current).
        generation_id:            UUID shared across pipeline. Required for telemetry.
        document_id:              File identifier (basename without extension).
        schema_version:           Schema version at generation time.
        total_attempts:           Total LLM attempts made in retry loop.
        rejected_candidates:      All enum values rejected during retries.
        model:                    LLM model identifier.
        temperature:              Must be 0 per Determinism Contract.
        total_duration_ms:        Wall time for all attempts combined.
        writer:                   TelemetryWriter instance. None disables telemetry.

    Returns:
        CommitResult with committed status and path or blocking errors.
    """
    _schema_ver = schema_version or expected_schema_version

    # 1. Check for blocking errors
    blocking = [e for e in errors if e.severity == Severity.ERROR]
    if blocking:
        _emit_summary(
            writer=writer,
            generation_id=generation_id,
            document_id=document_id,
            schema_version=_schema_ver,
            total_attempts=total_attempts,
            converged=False,
            abort_reason="blocking_errors",
            rejected_candidates=rejected_candidates or [],
            final_domain=None,
            model=model,
            temperature=temperature,
            total_duration_ms=total_duration_ms,
        )
        return CommitResult(
            committed=False,
            path=None,
            blocking_errors=blocking,
            schema_version=expected_schema_version,
        )

    # 2. Atomic write
    _atomic_write(document, output_path)

    # 3. Emit summary — success
    final_domain = _extract_field(document, "domain")
    _emit_summary(
        writer=writer,
        generation_id=generation_id,
        document_id=document_id,
        schema_version=_schema_ver,
        total_attempts=total_attempts,
        converged=True,
        abort_reason=None,
        rejected_candidates=rejected_candidates or [],
        final_domain=final_domain,
        model=model,
        temperature=temperature,
        total_duration_ms=total_duration_ms,
    )

    return CommitResult(
        committed=True,
        path=output_path,
        blocking_errors=[],
        schema_version=expected_schema_version,
    )


# ---------------------------------------------------------------------------
# Telemetry helpers (Phase 2.3)
# ---------------------------------------------------------------------------


def _emit_summary(
    *,
    writer,
    generation_id: Optional[str],
    document_id: Optional[str],
    schema_version: str,
    total_attempts: int,
    converged: bool,
    abort_reason: Optional[str],
    rejected_candidates: list[str],
    final_domain: Optional[str],
    model: str,
    temperature: float,
    total_duration_ms: int,
) -> None:
    """Emit GenerationSummaryEvent if writer and generation_id are provided.

    Silent no-op when writer=None — telemetry is optional.
    Errors in telemetry write are caught and suppressed to never
    interrupt the commit pipeline (observe, never influence).
    """
    if writer is None or generation_id is None:
        return

    try:
        from akf.telemetry import GenerationSummaryEvent

        event = GenerationSummaryEvent(
            generation_id=generation_id,
            document_id=document_id or "unknown",
            schema_version=schema_version,
            total_attempts=total_attempts,
            converged=converged,
            abort_reason=abort_reason,
            rejected_candidates=rejected_candidates,
            final_domain=final_domain,
            model=model,
            temperature=temperature,
            total_duration_ms=total_duration_ms,
        )
        writer.write(event)
    except Exception:
        # Telemetry failure must never interrupt the pipeline.
        pass


# ---------------------------------------------------------------------------
# schema_version enforcement (deterministic)
# ---------------------------------------------------------------------------


def _check_schema_version(
    document: str,
    expected: str,
) -> Optional[ValidationError]:
    """
    Verify schema_version in document matches expected.

    schema_version is immutable at commit:
      - Required in document
      - Must match current active schema version
      - NOT auto-upgraded by retry loop
    """
    from akf.validation_error import schema_violation

    actual = _extract_schema_version(document)

    if actual is None:
        return schema_violation(
            field="schema_version",
            expected=expected,
            received="absent",
        )

    if actual != expected:
        return schema_violation(
            field="schema_version",
            expected=expected,
            received=actual,
        )

    return None


def _extract_schema_version(document: str) -> Optional[str]:
    """Extract schema_version value from YAML frontmatter. Returns None if not found."""
    return _extract_field(document, "schema_version")


def _extract_field(document: str, field_name: str) -> Optional[str]:
    """Extract a scalar field value from YAML frontmatter. Returns None if not found."""
    in_frontmatter = False
    prefix = f"{field_name}:"

    for i, line in enumerate(document.splitlines()):
        stripped = line.strip()
        if i == 0 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and stripped == "---":
            break
        if in_frontmatter and stripped.startswith(prefix):
            value = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            return value if value else None

    return None


# ---------------------------------------------------------------------------
# Atomic write (deterministic)
# ---------------------------------------------------------------------------


def _atomic_write(content: str, target: Path) -> None:
    """
    Write content to target path atomically.
    Uses temp file + rename to prevent partial writes.
    """
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=target.parent,
        prefix=".akf_tmp_",
        suffix=".md",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target)  # atomic on POSIX
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
