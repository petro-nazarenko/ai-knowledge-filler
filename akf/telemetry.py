"""AKF Telemetry — append-only JSONL event writer.

Implements the canonical event schema defined in AKF_Telemetry_Schema_v1.0.

Two event types:
  - GenerationAttemptEvent  — emitted by RetryController after each attempt
  - GenerationSummaryEvent  — emitted by CommitGate after session completes

Design constraints (ADR-001 v1.6):
  - Telemetry observes. Never influences runtime behavior.
  - Each retry = new event. No mutation. No rewriting history.
  - Documents ≠ telemetry. Never mixed.
  - model + temperature required to separate ontology drift from model drift.

Storage: append-only JSONL at telemetry/events.jsonl (repo, not vault).
Thread safety: threading.Lock per writer instance.
Rotation: new file when current exceeds ROTATION_BYTES (default 10MB).
"""

import json
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

DEFAULT_TELEMETRY_PATH = Path("telemetry/events.jsonl")
ROTATION_BYTES = 10 * 1024 * 1024  # 10MB


# ─── VALUE OBJECTS ────────────────────────────────────────────────────────────

@dataclass
class ValidationErrorRecord:
    """Serializable representation of a ValidationError for telemetry.

    Mirrors ValidationError contract from ADR-001 Decision 3.
    """
    code: str       # E001–E006
    field: str      # YAML field name
    expected: Any   # Valid set or pattern
    received: Any   # Value that failed validation
    severity: str   # "error" | "warning"

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "field": self.field,
            "expected": self.expected,
            "received": self.received,
            "severity": self.severity,
        }


# ─── EVENTS ───────────────────────────────────────────────────────────────────

@dataclass
class GenerationAttemptEvent:
    """One event per generation attempt.

    A document requiring 3 retries produces 3 GenerationAttemptEvents,
    all sharing the same generation_id.

    Emitted by: RetryController after each attempt.
    """
    # Identity
    generation_id: str
    document_id: str
    schema_version: str

    # Attempt context
    attempt: int          # 1-indexed
    max_attempts: int     # RetryController ceiling (currently 3)
    is_final_attempt: bool
    converged: bool       # True if ValidationEngine returned VALID

    # Validation outcome
    errors: list[ValidationErrorRecord]

    # LLM config (required for drift separation)
    model: str
    temperature: float    # Must be 0 per Determinism Contract
    top_p: float          # Must be 1 per Determinism Contract

    # Timing
    duration_ms: int

    # Auto-populated
    event_type: str = field(default="generation_attempt", init=False)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: _utc_now())

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "generation_id": self.generation_id,
            "document_id": self.document_id,
            "schema_version": self.schema_version,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "is_final_attempt": self.is_final_attempt,
            "converged": self.converged,
            "errors": [e.to_dict() for e in self.errors],
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


@dataclass
class GenerationSummaryEvent:
    """One event per generation session — aggregates all attempt outcomes.

    Emitted by: CommitGate after session completes (converged or aborted).
    """
    # Identity
    generation_id: str
    document_id: str
    schema_version: str

    # Session outcome
    total_attempts: int
    converged: bool
    abort_reason: Optional[str]   # None if converged.
                                  # "identical_error_hash" | "max_attempts_exceeded"

    # Ontology signals
    rejected_candidates: list[str]   # All enum values attempted and rejected, in order
    final_domain: Optional[str]      # Committed domain value. None if not converged.

    # LLM config
    model: str
    temperature: float

    # Timing
    total_duration_ms: int

    # Auto-populated
    event_type: str = field(default="generation_summary", init=False)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: _utc_now())

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "generation_id": self.generation_id,
            "document_id": self.document_id,
            "schema_version": self.schema_version,
            "total_attempts": self.total_attempts,
            "converged": self.converged,
            "abort_reason": self.abort_reason,
            "rejected_candidates": self.rejected_candidates,
            "final_domain": self.final_domain,
            "model": self.model,
            "temperature": self.temperature,
            "timestamp": self.timestamp,
            "total_duration_ms": self.total_duration_ms,
        }


# ─── WRITER ───────────────────────────────────────────────────────────────────



@dataclass
class EnrichEvent:
    """One telemetry event per enriched file (ADR-001 Decision 9)."""
    generation_id: str
    file: str
    schema_version: str
    existing_fields: list[str]
    generated_fields: list[str]
    attempts: int
    converged: bool
    skipped: bool
    skip_reason: str
    model: str
    temperature: float = 0.0
    event_type: str = field(default="enrich", init=False)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: _utc_now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "generation_id": self.generation_id,
            "file": self.file,
            "schema_version": self.schema_version,
            "existing_fields": self.existing_fields,
            "generated_fields": self.generated_fields,
            "attempts": self.attempts,
            "converged": self.converged,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "model": self.model,
            "temperature": self.temperature,
        }


class TelemetryWriter:
    """Append-only thread-safe JSONL writer for AKF telemetry events.

    Usage:
        writer = TelemetryWriter()
        writer.write(attempt_event)
        writer.write(summary_event)

    Thread safety: single Lock per instance. Safe for concurrent use
    within one process. Multi-process safety requires external coordination.

    Rotation: when file exceeds ROTATION_BYTES, new file opened with
    date suffix: events_2026-02.jsonl
    """

    def __init__(self, path: Path = DEFAULT_TELEMETRY_PATH) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()

    def write(self, event: GenerationAttemptEvent | GenerationSummaryEvent | EnrichEvent) -> None:
        """Serialize event to JSONL and append to telemetry file.

        Args:
            event: GenerationAttemptEvent or GenerationSummaryEvent instance.

        Raises:
            TypeError: if event is not a recognized type.
            OSError: if file cannot be written.
        """
        if not isinstance(event, (GenerationAttemptEvent, GenerationSummaryEvent, EnrichEvent)):
            raise TypeError(
                f"Expected GenerationAttemptEvent, GenerationSummaryEvent, or EnrichEvent, "
                f"got {type(event).__name__}"
            )

        line = json.dumps(event.to_dict(), ensure_ascii=False)

        with self._lock:
            target = self._resolve_path()
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def _resolve_path(self) -> Path:
        """Return current write target, rotating if file exceeds ROTATION_BYTES."""
        if self._path.exists() and self._path.stat().st_size >= ROTATION_BYTES:
            suffix = datetime.now(timezone.utc).strftime("%Y-%m")
            rotated = self._path.with_name(
                f"{self._path.stem}_{suffix}{self._path.suffix}"
            )
            self._path = rotated
        return self._path

    @property
    def path(self) -> Path:
        return self._path


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def new_generation_id() -> str:
    """Generate a UUID v4 for use as generation_id across pipeline components."""
    return str(uuid.uuid4())


def _utc_now() -> str:
    """Return current UTC time in ISO 8601 format with millisecond precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"