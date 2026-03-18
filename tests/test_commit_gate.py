"""Tests for GenerationSummaryEvent emission in CommitGate (Task 5 / Phase 2.3).

Covers:
  - event emitted on successful commit (converged=True, final_domain set)
  - event emitted on blocking errors (converged=False, abort_reason="blocking_errors")
  - event emitted on schema_version mismatch (abort_reason="schema_version_mismatch")
  - writer=None → no emission, pipeline unaffected
  - generation_id=None → no emission
  - telemetry failure → pipeline continues (observe, never influence)
  - rejected_candidates propagated to event
  - final_domain extracted from document
  - event_type == "generation_summary"
"""

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from akf.commit_gate import commit, SCHEMA_VERSION
from akf.telemetry import TelemetryWriter
from akf.validation_error import (
    Severity,
    ValidationError,
    ErrorCode,
    taxonomy_violation,
)


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

GEN_ID = str(uuid.uuid4())
DOC_ID = "test_doc"
MODEL = "groq-test"

VALID_DOC = f"""---
title: Valid Document
type: guide
domain: api-design
level: intermediate
status: active
schema_version: "{SCHEMA_VERSION}"
created: 2026-02-24
updated: 2026-02-24
---

# Body
"""

WRONG_VERSION_DOC = f"""---
title: Wrong Version
type: guide
domain: api-design
level: intermediate
status: active
schema_version: "9.9.9"
created: 2026-02-24
updated: 2026-02-24
---

# Body
"""

NO_VERSION_DOC = f"""---
title: Missing Version
type: guide
domain: api-design
level: intermediate
status: active
created: 2026-02-24
updated: 2026-02-24
---

# Body
"""

def make_writer(tmp_path: Path) -> TelemetryWriter:
    return TelemetryWriter(path=tmp_path / "events.jsonl")


def blocking_error() -> ValidationError:
    return taxonomy_violation("domain", "backend", ["api-design"])


def read_events(writer: TelemetryWriter) -> list[dict]:
    if not writer.path.exists():
        return []
    return [json.loads(l) for l in writer.path.read_text().strip().split("\n") if l]


def run_commit(doc, output_path, errors, writer, rejected=None):
    return commit(
        document=doc,
        output_path=output_path,
        errors=errors,
        generation_id=GEN_ID,
        document_id=DOC_ID,
        schema_version=SCHEMA_VERSION,
        total_attempts=2,
        rejected_candidates=rejected or [],
        model=MODEL,
        temperature=0,
        total_duration_ms=1500,
        writer=writer,
    )


# ─── Success path ─────────────────────────────────────────────────────────────

class TestSummaryOnSuccess:
    def test_emits_one_summary_event(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer)
        events = read_events(writer)
        assert len(events) == 1

    def test_event_type_generation_summary(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer)
        assert read_events(writer)[0]["event_type"] == "generation_summary"

    def test_converged_true(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer)
        assert read_events(writer)[0]["converged"] is True

    def test_abort_reason_none(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer)
        assert read_events(writer)[0]["abort_reason"] is None

    def test_final_domain_extracted(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer)
        assert read_events(writer)[0]["final_domain"] == "api-design"

    def test_generation_id_in_event(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer)
        assert read_events(writer)[0]["generation_id"] == GEN_ID

    def test_model_and_temperature(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer)
        evt = read_events(writer)[0]
        assert evt["model"] == MODEL
        assert evt["temperature"] == 0

    def test_total_attempts_propagated(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer)
        assert read_events(writer)[0]["total_attempts"] == 2

    def test_total_duration_ms_propagated(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer)
        assert read_events(writer)[0]["total_duration_ms"] == 1500

    def test_rejected_candidates_propagated(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer, rejected=["backend", "api"])
        assert read_events(writer)[0]["rejected_candidates"] == ["backend", "api"]

    def test_empty_rejected_candidates(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [], writer)
        assert read_events(writer)[0]["rejected_candidates"] == []


# ─── Blocking errors path ─────────────────────────────────────────────────────

class TestSummaryOnBlockingErrors:
    def test_emits_summary_on_blocking_error(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [blocking_error()], writer)
        events = read_events(writer)
        assert len(events) == 1

    def test_converged_false(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [blocking_error()], writer)
        assert read_events(writer)[0]["converged"] is False

    def test_abort_reason_blocking_errors(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [blocking_error()], writer)
        assert read_events(writer)[0]["abort_reason"] == "blocking_errors"

    def test_final_domain_none_on_failure(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(VALID_DOC, tmp_path / "out.md", [blocking_error()], writer)
        assert read_events(writer)[0]["final_domain"] is None

    def test_file_not_written_on_blocking(self, tmp_path):
        writer = make_writer(tmp_path)
        out = tmp_path / "out.md"
        run_commit(VALID_DOC, out, [blocking_error()], writer)
        assert not out.exists()


# ─── Schema version mismatch path ─────────────────────────────────────────────

class TestSummaryOnSchemaVersionMismatch:
    def test_emits_summary_on_version_mismatch(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(WRONG_VERSION_DOC, tmp_path / "out.md", [], writer)
        events = read_events(writer)
        assert len(events) == 1

    def test_converged_false_on_mismatch(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(WRONG_VERSION_DOC, tmp_path / "out.md", [], writer)
        assert read_events(writer)[0]["converged"] is False

    def test_abort_reason_blocking_errors_on_mismatch(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(WRONG_VERSION_DOC, tmp_path / "out.md", [], writer)
        assert read_events(writer)[0]["abort_reason"] == "blocking_errors"

    def test_file_not_written_on_version_mismatch(self, tmp_path):
        writer = make_writer(tmp_path)
        out = tmp_path / "out.md"
        result = run_commit(WRONG_VERSION_DOC, out, [], writer)
        assert not out.exists()
        assert result.committed is False


# ─── Missing schema_version path ──────────────────────────────────────────────

class TestMissingSchemaVersion:
    def test_commit_blocked_when_schema_version_absent(self, tmp_path):
        writer = make_writer(tmp_path)
        out = tmp_path / "out.md"
        result = run_commit(NO_VERSION_DOC, out, [], writer)
        assert result.committed is False
        assert not out.exists()

    def test_emits_summary_on_absent_schema_version(self, tmp_path):
        writer = make_writer(tmp_path)
        run_commit(NO_VERSION_DOC, tmp_path / "out.md", [], writer)
        events = read_events(writer)
        assert len(events) == 1
        assert events[0]["converged"] is False
        assert events[0]["abort_reason"] == "blocking_errors"


# ─── writer=None and generation_id=None ───────────────────────────────────────

class TestNoTelemetry:
    def test_writer_none_commit_succeeds(self, tmp_path):
        out = tmp_path / "out.md"
        result = commit(
            document=VALID_DOC,
            output_path=out,
            errors=[],
            writer=None,
        )
        assert result.committed is True
        assert out.exists()

    def test_writer_none_no_file_created(self, tmp_path):
        telemetry_path = tmp_path / "events.jsonl"
        commit(document=VALID_DOC, output_path=tmp_path / "out.md", errors=[], writer=None)
        assert not telemetry_path.exists()

    def test_generation_id_none_no_emission(self, tmp_path):
        writer = make_writer(tmp_path)
        commit(
            document=VALID_DOC,
            output_path=tmp_path / "out.md",
            errors=[],
            generation_id=None,
            writer=writer,
        )
        assert not writer.path.exists()


# ─── Telemetry failure isolation ──────────────────────────────────────────────

class TestTelemetryFailureIsolation:
    def test_writer_exception_does_not_abort_commit(self, tmp_path):
        broken_writer = MagicMock(spec=TelemetryWriter)
        broken_writer.write.side_effect = OSError("disk full")
        out = tmp_path / "out.md"

        result = commit(
            document=VALID_DOC,
            output_path=out,
            errors=[],
            generation_id=GEN_ID,
            document_id=DOC_ID,
            model=MODEL,
            temperature=0,
            writer=broken_writer,
        )
        assert result.committed is True
        assert out.exists()