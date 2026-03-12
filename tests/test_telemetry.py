"""Tests for akf/telemetry.py — JSONL writer, event schemas, thread safety."""

import json
import threading
import time
import uuid
from pathlib import Path

import pytest

from akf.telemetry import (
    AskQueryEvent,
    EnrichEvent,
    GenerationAttemptEvent,
    GenerationSummaryEvent,
    MarketAnalysisEvent,
    TelemetryWriter,
    ValidationErrorRecord,
    new_generation_id,
    ROTATION_BYTES,
)


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

@pytest.fixture
def gen_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def error_record() -> ValidationErrorRecord:
    return ValidationErrorRecord(
        code="E006_TAXONOMY_VIOLATION",
        field="domain",
        expected=["api-design", "backend-engineering"],
        received="backend",
        severity="error",
    )


@pytest.fixture
def attempt_event(gen_id, error_record) -> GenerationAttemptEvent:
    return GenerationAttemptEvent(
        generation_id=gen_id,
        document_id="ADR-001",
        schema_version="1.0.0",
        attempt=1,
        max_attempts=3,
        is_final_attempt=False,
        converged=False,
        errors=[error_record],
        model="groq-xyz",
        temperature=0,
        top_p=1,
        duration_ms=1240,
    )


@pytest.fixture
def summary_event(gen_id) -> GenerationSummaryEvent:
    return GenerationSummaryEvent(
        generation_id=gen_id,
        document_id="ADR-001",
        schema_version="1.0.0",
        total_attempts=2,
        converged=True,
        abort_reason=None,
        rejected_candidates=["backend", "api"],
        final_domain="api-design",
        model="groq-xyz",
        temperature=0,
        total_duration_ms=2890,
    )


@pytest.fixture
def writer(tmp_path) -> TelemetryWriter:
    return TelemetryWriter(path=tmp_path / "events.jsonl")


# ─── ValidationErrorRecord ────────────────────────────────────────────────────

class TestValidationErrorRecord:
    def test_to_dict_all_fields(self, error_record):
        d = error_record.to_dict()
        assert d["code"] == "E006_TAXONOMY_VIOLATION"
        assert d["field"] == "domain"
        assert d["expected"] == ["api-design", "backend-engineering"]
        assert d["received"] == "backend"
        assert d["severity"] == "error"

    def test_to_dict_keys_complete(self, error_record):
        assert set(error_record.to_dict().keys()) == {
            "code", "field", "expected", "received", "severity"
        }


# ─── GenerationAttemptEvent ───────────────────────────────────────────────────

class TestGenerationAttemptEvent:
    def test_event_type_fixed(self, attempt_event):
        assert attempt_event.event_type == "generation_attempt"

    def test_event_id_is_uuid(self, attempt_event):
        uuid.UUID(attempt_event.event_id)  # raises if invalid

    def test_timestamp_format(self, attempt_event):
        ts = attempt_event.timestamp
        assert ts.endswith("Z")
        assert "T" in ts

    def test_to_dict_required_fields(self, attempt_event):
        d = attempt_event.to_dict()
        required = {
            "event_type", "event_id", "generation_id", "document_id",
            "schema_version", "attempt", "max_attempts", "is_final_attempt",
            "converged", "errors", "model", "temperature", "top_p",
            "timestamp", "duration_ms",
        }
        assert required.issubset(set(d.keys()))

    def test_errors_serialized(self, attempt_event):
        d = attempt_event.to_dict()
        assert len(d["errors"]) == 1
        assert d["errors"][0]["code"] == "E006_TAXONOMY_VIOLATION"

    def test_converged_false_has_errors(self, attempt_event):
        assert attempt_event.converged is False
        assert len(attempt_event.errors) > 0

    def test_converged_true_empty_errors(self, gen_id):
        evt = GenerationAttemptEvent(
            generation_id=gen_id,
            document_id="doc",
            schema_version="1.0.0",
            attempt=2,
            max_attempts=3,
            is_final_attempt=True,
            converged=True,
            errors=[],
            model="groq-xyz",
            temperature=0,
            top_p=1,
            duration_ms=900,
        )
        assert evt.converged is True
        assert evt.errors == []
        assert evt.to_dict()["errors"] == []

    def test_two_instances_have_different_event_ids(self, gen_id):
        def make():
            return GenerationAttemptEvent(
                generation_id=gen_id, document_id="doc", schema_version="1.0.0",
                attempt=1, max_attempts=3, is_final_attempt=False, converged=False,
                errors=[], model="m", temperature=0, top_p=1, duration_ms=100,
            )
        assert make().event_id != make().event_id

    def test_determinism_fields(self, attempt_event):
        d = attempt_event.to_dict()
        assert d["temperature"] == 0
        assert d["top_p"] == 1


# ─── GenerationSummaryEvent ───────────────────────────────────────────────────

class TestGenerationSummaryEvent:
    def test_event_type_fixed(self, summary_event):
        assert summary_event.event_type == "generation_summary"

    def test_event_id_is_uuid(self, summary_event):
        uuid.UUID(summary_event.event_id)

    def test_to_dict_required_fields(self, summary_event):
        d = summary_event.to_dict()
        required = {
            "event_type", "event_id", "generation_id", "document_id",
            "schema_version", "total_attempts", "converged", "abort_reason",
            "rejected_candidates", "final_domain", "model", "temperature",
            "timestamp", "total_duration_ms",
        }
        assert required.issubset(set(d.keys()))

    def test_converged_abort_reason_none(self, summary_event):
        assert summary_event.converged is True
        assert summary_event.abort_reason is None

    def test_not_converged_abort_reason_set(self, gen_id):
        evt = GenerationSummaryEvent(
            generation_id=gen_id,
            document_id="doc",
            schema_version="1.0.0",
            total_attempts=3,
            converged=False,
            abort_reason="max_attempts_exceeded",
            rejected_candidates=["backend", "api", "services"],
            final_domain=None,
            model="groq-xyz",
            temperature=0,
            total_duration_ms=5000,
        )
        assert evt.converged is False
        assert evt.abort_reason == "max_attempts_exceeded"
        assert evt.final_domain is None

    def test_abort_reason_identical_error_hash(self, gen_id):
        evt = GenerationSummaryEvent(
            generation_id=gen_id,
            document_id="doc",
            schema_version="1.0.0",
            total_attempts=2,
            converged=False,
            abort_reason="identical_error_hash",
            rejected_candidates=["backend", "backend"],
            final_domain=None,
            model="groq-xyz",
            temperature=0,
            total_duration_ms=2000,
        )
        assert evt.abort_reason == "identical_error_hash"

    def test_rejected_candidates_order_preserved(self, summary_event):
        assert summary_event.to_dict()["rejected_candidates"] == ["backend", "api"]

    def test_generation_id_shared_with_attempts(self, gen_id, attempt_event, summary_event):
        assert attempt_event.generation_id == summary_event.generation_id == gen_id


# ─── TelemetryWriter ──────────────────────────────────────────────────────────

class TestTelemetryWriter:
    def test_write_creates_file(self, writer, attempt_event):
        writer.write(attempt_event)
        assert writer.path.exists()

    def test_write_attempt_event_valid_json(self, writer, attempt_event):
        writer.write(attempt_event)
        lines = writer.path.read_text().strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["event_type"] == "generation_attempt"

    def test_write_summary_event_valid_json(self, writer, summary_event):
        writer.write(summary_event)
        lines = writer.path.read_text().strip().split("\n")
        data = json.loads(lines[0])
        assert data["event_type"] == "generation_summary"

    def test_append_multiple_events(self, writer, attempt_event, summary_event):
        writer.write(attempt_event)
        writer.write(summary_event)
        lines = writer.path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_each_line_independent_json(self, writer, attempt_event, summary_event):
        writer.write(attempt_event)
        writer.write(summary_event)
        for line in writer.path.read_text().strip().split("\n"):
            json.loads(line)  # must not raise

    def test_invalid_event_type_raises(self, writer):
        with pytest.raises(TypeError):
            writer.write({"event_type": "fake"})  # type: ignore

    def test_creates_parent_dirs(self, tmp_path):
        deep_path = tmp_path / "a" / "b" / "events.jsonl"
        w = TelemetryWriter(path=deep_path)
        evt = GenerationAttemptEvent(
            generation_id=str(uuid.uuid4()), document_id="doc",
            schema_version="1.0.0", attempt=1, max_attempts=3,
            is_final_attempt=False, converged=True, errors=[],
            model="m", temperature=0, top_p=1, duration_ms=100,
        )
        w.write(evt)
        assert deep_path.exists()

    def test_thread_safety(self, tmp_path):
        """100 concurrent writes must produce 100 valid JSONL lines."""
        path = tmp_path / "events.jsonl"
        w = TelemetryWriter(path=path)
        errors_encountered = []

        def write_one(i):
            try:
                evt = GenerationAttemptEvent(
                    generation_id=str(uuid.uuid4()),
                    document_id=f"doc-{i}",
                    schema_version="1.0.0",
                    attempt=1,
                    max_attempts=3,
                    is_final_attempt=True,
                    converged=True,
                    errors=[],
                    model="m",
                    temperature=0,
                    top_p=1,
                    duration_ms=10,
                )
                w.write(evt)
            except Exception as e:
                errors_encountered.append(e)

        threads = [threading.Thread(target=write_one, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors_encountered == [], f"Thread errors: {errors_encountered}"
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 100
        for line in lines:
            json.loads(line)  # all lines must be valid JSON

    def test_rotation_creates_new_file(self, tmp_path):
        """Writer rotates to dated filename when file exceeds ROTATION_BYTES."""
        path = tmp_path / "events.jsonl"
        # Pre-fill file to just over rotation threshold
        path.write_bytes(b"x" * ROTATION_BYTES)

        w = TelemetryWriter(path=path)
        evt = GenerationAttemptEvent(
            generation_id=str(uuid.uuid4()), document_id="doc",
            schema_version="1.0.0", attempt=1, max_attempts=3,
            is_final_attempt=True, converged=True, errors=[],
            model="m", temperature=0, top_p=1, duration_ms=50,
        )
        w.write(evt)

        # After rotation, writer path should differ from original
        assert w.path != path
        assert w.path.exists()
        # Rotated file contains the new event
        data = json.loads(w.path.read_text().strip())
        assert data["event_type"] == "generation_attempt"


# ─── new_generation_id ────────────────────────────────────────────────────────

class TestNewGenerationId:
    def test_returns_valid_uuid(self):
        gid = new_generation_id()
        uuid.UUID(gid)  # raises if invalid

    def test_unique_per_call(self):
        assert new_generation_id() != new_generation_id()


# ─── AskQueryEvent ───────────────────────────────────────────────────────────

class TestAskQueryEvent:
    def test_event_type_fixed(self):
        evt = AskQueryEvent(
            generation_id=str(uuid.uuid4()),
            tenant_id="team-a",
            mode="retrieval-only",
            model="none",
            top_k=5,
            no_llm=True,
            max_distance=0.5,
            hits_used=2,
            insufficient_context=False,
            duration_ms=12,
        )
        assert evt.event_type == "ask_query"

    def test_writer_accepts_ask_event(self, writer):
        evt = AskQueryEvent(
            generation_id=str(uuid.uuid4()),
            tenant_id="team-a",
            mode="synthesis",
            model="claude",
            top_k=3,
            no_llm=False,
            max_distance=None,
            hits_used=3,
            insufficient_context=False,
            duration_ms=89,
        )
        writer.write(evt)
        data = json.loads(writer.path.read_text().strip())
        assert data["event_type"] == "ask_query"
        assert data["mode"] == "synthesis"
        assert data["tenant_id"] == "team-a"


# ─── MarketAnalysisEvent ──────────────────────────────────────────────────────

class TestMarketAnalysisEvent:
    def _make(self, **kwargs) -> MarketAnalysisEvent:
        defaults = dict(
            generation_id=str(uuid.uuid4()),
            request="B2B SaaS tools for SMEs",
            stage="market_analysis",
            success=True,
            duration_ms=120,
            model="auto",
        )
        defaults.update(kwargs)
        return MarketAnalysisEvent(**defaults)

    def test_event_type_fixed(self):
        assert self._make().event_type == "market_analysis"

    def test_event_id_is_uuid(self):
        evt = self._make()
        uuid.UUID(evt.event_id)  # raises ValueError if invalid

    def test_default_error_is_empty(self):
        assert self._make().error == ""

    def test_to_dict_keys(self):
        evt = self._make()
        d = evt.to_dict()
        expected = {
            "event_type", "event_id", "timestamp", "generation_id",
            "request", "stage", "success", "duration_ms", "model", "error",
        }
        assert set(d.keys()) == expected

    def test_to_dict_values(self):
        gen_id = str(uuid.uuid4())
        evt = self._make(generation_id=gen_id, stage="competitor_analysis", success=False, error="oops")
        d = evt.to_dict()
        assert d["generation_id"] == gen_id
        assert d["stage"] == "competitor_analysis"
        assert d["success"] is False
        assert d["error"] == "oops"

    def test_writer_accepts_market_analysis_event(self, writer):
        evt = self._make(stage="positioning", success=True, duration_ms=250)
        writer.write(evt)
        data = json.loads(writer.path.read_text().strip())
        assert data["event_type"] == "market_analysis"
        assert data["stage"] == "positioning"


# ─── EnrichEvent (writer acceptance) ─────────────────────────────────────────

class TestEnrichEventWriterAcceptance:
    """Verify TelemetryWriter.write() accepts EnrichEvent (was missing from isinstance guard)."""

    def test_writer_accepts_enrich_event(self, writer):
        evt = EnrichEvent(
            generation_id=str(uuid.uuid4()),
            file="docs/guide.md",
            schema_version="1.0.0",
            existing_fields=["title"],
            generated_fields=["type", "domain"],
            attempts=1,
            converged=True,
            skipped=False,
            skip_reason="",
            model="auto",
        )
        writer.write(evt)
        data = json.loads(writer.path.read_text().strip())
        assert data["event_type"] == "enrich"
        assert data["file"] == "docs/guide.md"
