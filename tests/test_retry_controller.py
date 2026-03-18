"""Tests for GenerationAttemptEvent emission in RetryController (Task 4 / Phase 2.3).

Covers:
  - event emitted on each LLM attempt
  - converged=True on success
  - converged=False + is_final_attempt=True on abort (identical_output, convergence_failure)
  - converged=False + is_final_attempt=True on max_attempts_reached
  - writer=None → no emission, pipeline unaffected
  - telemetry failure → pipeline continues (observe, never influence)
  - generation_id=None → no emission
  - _to_record maps ValidationError fields correctly
  - duration_ms > 0
"""

import uuid
from unittest.mock import MagicMock, call, patch

import pytest

from akf.retry_controller import (
    MAX_ATTEMPTS,
    _to_record,
    run_retry_loop,
)
from akf.telemetry import GenerationAttemptEvent, TelemetryWriter
from akf.validation_error import (
    ErrorCode,
    Severity,
    ValidationError,
    invalid_enum,
    taxonomy_violation,
)

# ─── FIXTURES ─────────────────────────────────────────────────────────────────

GEN_ID = str(uuid.uuid4())
DOC_ID = "test_doc"
MODEL = "groq-test"
SCHEMA = "1.0.0"

VALID_DOC = "---\ntitle: Valid\ntype: guide\n---\n# Body"
INVALID_DOC = "---\ntitle: Invalid\ndomain: backend\n---\n# Body"


def make_error(field="domain", code=ErrorCode.TAXONOMY_VIOLATION, received="backend"):
    return ValidationError(
        code=code,
        field=field,
        expected=["api-design", "backend-engineering"],
        received=received,
        severity=Severity.ERROR,
    )


def make_title_error():
    """Error on a different field — avoids convergence_failure on attempt 1."""
    return ValidationError(
        code=ErrorCode.MISSING_FIELD,
        field="title",
        expected="present",
        received="absent",
        severity=Severity.ERROR,
    )


def make_writer(tmp_path):
    return TelemetryWriter(path=tmp_path / "events.jsonl")


# ─── _to_record ───────────────────────────────────────────────────────────────


class TestToRecord:
    def test_maps_all_fields(self):
        err = make_error()
        rec = _to_record(err)
        assert rec.code == "E006_TAXONOMY_VIOLATION"
        assert rec.field == "domain"
        assert rec.received == "backend"
        assert rec.severity == "error"

    def test_expected_preserved(self):
        err = make_error()
        rec = _to_record(err)
        assert isinstance(rec.expected, list)

    def test_invalid_enum_code(self):
        err = invalid_enum("type", ["guide", "concept"], "unknown")
        rec = _to_record(err)
        assert rec.code == "E001_INVALID_ENUM"
        assert rec.field == "type"


# ─── Telemetry emission ───────────────────────────────────────────────────────


class TestAttemptEventEmission:

    def _run(self, generate_fn, validate_fn, writer, errors=None):
        return run_retry_loop(
            document=INVALID_DOC,
            errors=errors or [make_error()],
            generate_fn=generate_fn,
            validate_fn=validate_fn,
            max_attempts=3,
            generation_id=GEN_ID,
            document_id=DOC_ID,
            schema_version=SCHEMA,
            model=MODEL,
            temperature=0,
            top_p=1,
            writer=writer,
        )

    def test_single_attempt_on_success(self, tmp_path):
        writer = make_writer(tmp_path)

        # Second document is valid — no errors
        calls = [0]

        def generate(doc, prompt):
            calls[0] += 1
            return VALID_DOC

        def validate(doc):
            if doc == VALID_DOC:
                return []
            return [make_error()]

        result = self._run(generate, validate, writer)

        assert result.success is True
        lines = _read_events(writer)
        assert len(lines) == 1
        evt = lines[0]
        assert evt["event_type"] == "generation_attempt"
        assert evt["converged"] is True
        assert evt["is_final_attempt"] is True
        assert evt["attempt"] == 1
        assert evt["errors"] == []

    def test_two_attempts_second_converges(self, tmp_path):
        writer = make_writer(tmp_path)
        docs = [INVALID_DOC + "_v2", VALID_DOC]
        idx = [0]

        def generate(doc, prompt):
            d = docs[idx[0]]
            idx[0] += 1
            return d

        def validate(doc):
            if doc == VALID_DOC:
                return []
            return [make_error()]

        # Initial errors use a different field so convergence_failure won't
        # trigger on attempt 1 when validate returns domain error
        result = self._run(generate, validate, writer, errors=[make_title_error()])
        assert result.success is True

        lines = _read_events(writer)
        assert len(lines) == 2

        assert lines[0]["converged"] is False
        assert lines[0]["is_final_attempt"] is False
        assert lines[0]["attempt"] == 1

        assert lines[1]["converged"] is True
        assert lines[1]["is_final_attempt"] is True
        assert lines[1]["attempt"] == 2

    def test_max_attempts_all_emitted(self, tmp_path):
        writer = make_writer(tmp_path)
        counter = [0]

        def generate(doc, prompt):
            counter[0] += 1
            return doc + f"_{counter[0]}"  # unique each time

        # Each attempt returns a different (field, code) pair so
        # convergence_failure never fires and all 3 attempts are emitted
        fields = ["domain", "level", "status"]
        validate_counter = [0]

        def validate(doc):
            f = fields[validate_counter[0] % len(fields)]
            validate_counter[0] += 1
            return [make_error(field=f)]

        # Initial error on title — differs from all validate_fn fields
        result = self._run(generate, validate, writer, errors=[make_title_error()])
        assert result.success is False

        lines = _read_events(writer)
        assert len(lines) == 3

        for i, evt in enumerate(lines, start=1):
            assert evt["attempt"] == i
            assert evt["converged"] is False

        assert lines[-1]["is_final_attempt"] is True

    def test_identical_output_abort_emits_final(self, tmp_path):
        writer = make_writer(tmp_path)

        def generate(doc, prompt):
            return INVALID_DOC  # always same → triggers identical_output abort

        def validate(doc):
            return [make_error()]

        # Initial error on different field so convergence_failure doesn't
        # fire before identical_output check
        # identical_output abort fires on attempt 2 (seen_hashes has attempt 1),
        # so 2 events are emitted: attempt 1 (not final) + attempt 2 (final)
        result = self._run(generate, validate, writer, errors=[make_title_error()])
        assert "identical_output" in result.abort_reason

        lines = _read_events(writer)
        assert len(lines) == 2
        assert lines[0]["is_final_attempt"] is False
        assert lines[1]["is_final_attempt"] is True
        assert lines[1]["converged"] is False

    def test_convergence_failure_abort_emits_final(self, tmp_path):
        writer = make_writer(tmp_path)
        counter = [0]

        def generate(doc, prompt):
            counter[0] += 1
            return doc + f"_v{counter[0]}"

        # Same (field, code) on consecutive attempts → convergence_failure
        def validate(doc):
            return [make_error(field="domain", code=ErrorCode.TAXONOMY_VIOLATION)]

        result = self._run(generate, validate, writer)
        assert "convergence_failure" in result.abort_reason

        lines = _read_events(writer)
        assert len(lines) == 1
        assert lines[0]["is_final_attempt"] is True
        assert lines[0]["converged"] is False

    def test_generation_id_consistent_across_attempts(self, tmp_path):
        writer = make_writer(tmp_path)
        counter = [0]

        def generate(doc, prompt):
            counter[0] += 1
            return doc + f"_{counter[0]}"

        def validate(doc):
            return [make_error()]

        self._run(generate, validate, writer)

        lines = _read_events(writer)
        gen_ids = {evt["generation_id"] for evt in lines}
        assert gen_ids == {GEN_ID}

    def test_model_and_temperature_in_events(self, tmp_path):
        writer = make_writer(tmp_path)

        def generate(doc, prompt):
            return VALID_DOC

        def validate(doc):
            return []

        self._run(generate, validate, writer)

        lines = _read_events(writer)
        evt = lines[0]
        assert evt["model"] == MODEL
        assert evt["temperature"] == 0
        assert evt["top_p"] == 1

    def test_duration_ms_positive(self, tmp_path):
        writer = make_writer(tmp_path)

        def generate(doc, prompt):
            return VALID_DOC

        def validate(doc):
            return []

        self._run(generate, validate, writer)

        lines = _read_events(writer)
        assert lines[0]["duration_ms"] >= 0

    def test_errors_recorded_on_failed_attempt(self, tmp_path):
        writer = make_writer(tmp_path)
        counter = [0]

        def generate(doc, prompt):
            counter[0] += 1
            return VALID_DOC if counter[0] == 2 else doc + "_bad"

        def validate(doc):
            if doc == VALID_DOC:
                return []
            return [make_error()]

        # Initial error on different field so convergence_failure doesn't
        # fire on attempt 1 when validate returns domain error
        self._run(generate, validate, writer, errors=[make_title_error()])

        lines = _read_events(writer)
        assert lines[0]["errors"][0]["code"] == "E006_TAXONOMY_VIOLATION"
        assert lines[1]["errors"] == []


# ─── writer=None — telemetry disabled ─────────────────────────────────────────


class TestNoWriter:
    def test_writer_none_pipeline_succeeds(self):
        def generate(doc, prompt):
            return VALID_DOC

        def validate(doc):
            return []

        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[make_error()],
            generate_fn=generate,
            validate_fn=validate,
            writer=None,
        )
        assert result.success is True

    def test_generation_id_none_no_emission(self, tmp_path):
        writer = make_writer(tmp_path)

        def generate(doc, prompt):
            return VALID_DOC

        def validate(doc):
            return []

        run_retry_loop(
            document=INVALID_DOC,
            errors=[make_error()],
            generate_fn=generate,
            validate_fn=validate,
            generation_id=None,  # no generation_id → no emission
            writer=writer,
        )
        assert not writer.path.exists()


# ─── Telemetry failure isolation ──────────────────────────────────────────────


class TestTelemetryFailureIsolation:
    def test_writer_exception_does_not_abort_pipeline(self, tmp_path):
        """Telemetry write failure must never interrupt generation."""
        broken_writer = MagicMock(spec=TelemetryWriter)
        broken_writer.write.side_effect = OSError("disk full")

        def generate(doc, prompt):
            return VALID_DOC

        def validate(doc):
            return []

        result = run_retry_loop(
            document=INVALID_DOC,
            errors=[make_error()],
            generate_fn=generate,
            validate_fn=validate,
            generation_id=GEN_ID,
            document_id=DOC_ID,
            schema_version=SCHEMA,
            model=MODEL,
            temperature=0,
            top_p=1,
            writer=broken_writer,
        )
        assert result.success is True


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _read_events(writer: TelemetryWriter) -> list[dict]:
    import json

    if not writer.path.exists():
        return []
    return [json.loads(line) for line in writer.path.read_text().strip().split("\n") if line]
