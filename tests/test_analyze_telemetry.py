"""Tests for scripts/analyze_telemetry.py — Phase 2.3 aggregation reports.

Covers:
  - load_events: valid JSONL, missing file, malformed lines, event splitting
  - report_retry_rate: Signal A rate, per-field breakdown, flag threshold
  - report_rejected_candidates: counts, unique docs, defect signals
  - report_convergence: mean attempts, non-convergence rate, per-domain
  - main(): --report flag routing, --flag-threshold, --input
"""

import json
import sys
from io import StringIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "Scripts"))

from analyze_telemetry import (
    FLAG_THRESHOLD,
    load_events,
    report_ask_usage,
    report_convergence,
    report_rejected_candidates,
    report_retry_rate,
    main,
)

# ─── FACTORIES ────────────────────────────────────────────────────────────────


def attempt(
    generation_id="gen-1",
    document_id="doc-1",
    attempt_num=1,
    converged=False,
    errors=None,
    model="groq-test",
    temperature=0,
) -> dict:
    return {
        "event_type": "generation_attempt",
        "event_id": "evt-1",
        "generation_id": generation_id,
        "document_id": document_id,
        "schema_version": "1.0.0",
        "attempt": attempt_num,
        "max_attempts": 3,
        "is_final_attempt": converged or attempt_num == 3,
        "converged": converged,
        "errors": errors or [],
        "model": model,
        "temperature": temperature,
        "top_p": 1,
        "timestamp": "2026-02-24T10:00:00.000Z",
        "duration_ms": 100,
    }


def summary(
    generation_id="gen-1",
    document_id="doc-1",
    total_attempts=1,
    converged=True,
    abort_reason=None,
    rejected_candidates=None,
    final_domain="api-design",
    model="groq-test",
    temperature=0,
) -> dict:
    return {
        "event_type": "generation_summary",
        "event_id": "evt-s1",
        "generation_id": generation_id,
        "document_id": document_id,
        "schema_version": "1.0.0",
        "total_attempts": total_attempts,
        "converged": converged,
        "abort_reason": abort_reason,
        "rejected_candidates": rejected_candidates or [],
        "final_domain": final_domain,
        "model": model,
        "temperature": temperature,
        "timestamp": "2026-02-24T10:00:01.000Z",
        "total_duration_ms": 500,
    }


def domain_error(received="backend") -> dict:
    return {
        "code": "E006_TAXONOMY_VIOLATION",
        "field": "domain",
        "expected": ["api-design", "backend-engineering"],
        "received": received,
        "severity": "error",
    }


def write_jsonl(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")


def ask_event(
    tenant_id="team-a",
    mode="synthesis",
    model="claude",
    top_k=5,
    no_llm=False,
    max_distance=None,
    hits_used=3,
    insufficient_context=False,
    duration_ms=120,
) -> dict:
    return {
        "event_type": "ask_query",
        "event_id": "evt-a1",
        "generation_id": "gen-ask-1",
        "tenant_id": tenant_id,
        "mode": mode,
        "model": model,
        "top_k": top_k,
        "no_llm": no_llm,
        "max_distance": max_distance,
        "hits_used": hits_used,
        "insufficient_context": insufficient_context,
        "duration_ms": duration_ms,
        "timestamp": "2026-03-11T10:00:00.000Z",
    }


# ─── load_events ──────────────────────────────────────────────────────────────


class TestLoadEvents:
    def test_splits_attempt_and_summary(self, tmp_path):
        path = tmp_path / "events.jsonl"
        write_jsonl(path, [attempt(), summary()])
        attempts, summaries, asks = load_events(path)
        assert len(attempts) == 1
        assert len(summaries) == 1
        assert len(asks) == 0

    def test_splits_ask_events(self, tmp_path):
        path = tmp_path / "events.jsonl"
        write_jsonl(path, [attempt(), summary(), ask_event()])
        attempts, summaries, asks = load_events(path)
        assert len(attempts) == 1
        assert len(summaries) == 1
        assert len(asks) == 1

    def test_multiple_attempts(self, tmp_path):
        path = tmp_path / "events.jsonl"
        write_jsonl(path, [attempt(attempt_num=1), attempt(attempt_num=2)])
        attempts, summaries, asks = load_events(path)
        assert len(attempts) == 2
        assert len(summaries) == 0
        assert len(asks) == 0

    def test_skips_malformed_lines(self, tmp_path, capsys):
        path = tmp_path / "events.jsonl"
        path.write_text(
            json.dumps(attempt()) + "\nnot valid json\n" + json.dumps(summary()),
            encoding="utf-8",
        )
        attempts, summaries, asks = load_events(path)
        assert len(attempts) == 1
        assert len(summaries) == 1
        assert len(asks) == 0
        captured = capsys.readouterr()
        assert "invalid JSON" in captured.out

    def test_skips_empty_lines(self, tmp_path):
        path = tmp_path / "events.jsonl"
        path.write_text(
            json.dumps(attempt()) + "\n\n\n" + json.dumps(summary()),
            encoding="utf-8",
        )
        attempts, summaries, asks = load_events(path)
        assert len(attempts) == 1
        assert len(summaries) == 1
        assert len(asks) == 0

    def test_missing_file_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            load_events(tmp_path / "nonexistent.jsonl")

    def test_unknown_event_type_ignored(self, tmp_path):
        path = tmp_path / "events.jsonl"
        path.write_text(
            json.dumps({"event_type": "unknown", "data": "x"}),
            encoding="utf-8",
        )
        attempts, summaries, asks = load_events(path)
        assert attempts == []
        assert summaries == []
        assert asks == []


class TestReportAskUsage:
    def test_no_ask_events_prints_message(self, capsys):
        report_ask_usage([])
        assert "No ask events" in capsys.readouterr().out

    def test_groups_by_tenant(self, capsys):
        events = [
            ask_event(tenant_id="team-a", mode="synthesis", insufficient_context=False),
            ask_event(tenant_id="team-a", mode="retrieval-only", no_llm=True),
            ask_event(tenant_id="team-b", mode="synthesis", insufficient_context=True),
        ]
        report_ask_usage(events)
        out = capsys.readouterr().out
        assert "team-a" in out
        assert "team-b" in out

    def test_high_no_answer_flag(self, capsys):
        events = [
            ask_event(tenant_id="team-a", insufficient_context=True),
            ask_event(tenant_id="team-a", insufficient_context=True),
            ask_event(tenant_id="team-a", insufficient_context=False),
        ]
        report_ask_usage(events)
        out = capsys.readouterr().out.lower()
        assert "high no-answer" in out


# ─── report_retry_rate ────────────────────────────────────────────────────────


class TestReportRetryRate:
    def test_no_attempts_prints_message(self, capsys):
        report_retry_rate([])
        assert "No attempt events" in capsys.readouterr().out

    def test_signal_a_rate_all_pass(self, capsys):
        events = [attempt(attempt_num=1, converged=True, errors=[])]
        report_retry_rate(events)
        out = capsys.readouterr().out
        assert "0.0%" in out

    def test_signal_a_rate_all_fail(self, capsys):
        events = [
            attempt(attempt_num=1, converged=False, errors=[domain_error()]),
            attempt(attempt_num=1, converged=False, errors=[domain_error()], document_id="doc-2"),
        ]
        report_retry_rate(events)
        out = capsys.readouterr().out
        assert "100.0%" in out

    def test_signal_a_rate_mixed(self, capsys):
        events = [
            attempt(attempt_num=1, converged=False, errors=[domain_error()]),
            attempt(attempt_num=1, converged=True, errors=[], document_id="doc-2"),
        ]
        report_retry_rate(events)
        out = capsys.readouterr().out
        assert "50.0%" in out

    def test_flag_shown_above_threshold(self, capsys):
        # 10 docs all failing on same domain value → 100% > 15% threshold
        events = [
            attempt(
                attempt_num=1,
                converged=False,
                errors=[domain_error("consulting")],
                document_id=f"doc-{i}",
            )
            for i in range(10)
        ]
        report_retry_rate(events, flag_threshold=0.15)
        assert "REVIEW" in capsys.readouterr().out

    def test_no_flag_below_threshold(self, capsys):
        # 1 failure out of 20 docs → 5% < 15%
        events = [
            attempt(attempt_num=1, converged=True, errors=[], document_id=f"doc-{i}")
            for i in range(19)
        ] + [attempt(attempt_num=1, converged=False, errors=[domain_error()], document_id="doc-19")]
        report_retry_rate(events, flag_threshold=0.15)
        assert "REVIEW" not in capsys.readouterr().out

    def test_only_first_attempts_counted(self, capsys):
        # attempt 2 should not affect Signal A
        events = [
            attempt(attempt_num=1, converged=False, errors=[domain_error()]),
            attempt(attempt_num=2, converged=True, errors=[]),
        ]
        report_retry_rate(events)
        out = capsys.readouterr().out
        # Only 1 first attempt, 1 failed → 100%
        assert "100.0%" in out

    def test_no_violations_shows_ok_message(self, capsys):
        events = [attempt(attempt_num=1, converged=True, errors=[])]
        report_retry_rate(events)
        assert "No enum violations" in capsys.readouterr().out


# ─── report_rejected_candidates ──────────────────────────────────────────────


class TestReportRejectedCandidates:
    def test_no_summaries_prints_message(self, capsys):
        report_rejected_candidates([])
        assert "No summary events" in capsys.readouterr().out

    def test_no_rejections_shows_ok(self, capsys):
        report_rejected_candidates([summary(rejected_candidates=[])])
        assert "No rejected candidates" in capsys.readouterr().out

    def test_counts_total_rejections(self, capsys):
        events = [
            summary(document_id="doc-1", rejected_candidates=["backend", "api"]),
            summary(document_id="doc-2", rejected_candidates=["backend"]),
        ]
        report_rejected_candidates(events)
        out = capsys.readouterr().out
        # "backend" appears 2 times total
        assert "backend" in out

    def test_unique_doc_count_separate_docs(self, capsys):
        events = [
            summary(document_id="doc-1", rejected_candidates=["consulting"]),
            summary(document_id="doc-2", rejected_candidates=["consulting"]),
            summary(document_id="doc-3", rejected_candidates=["consulting"]),
        ]
        report_rejected_candidates(events)
        # 3 unique docs
        assert "3" in capsys.readouterr().out

    def test_defect_signal_missing_category(self, capsys):
        # High unique docs + mostly not converged → missing category
        events = [
            summary(
                document_id=f"doc-{i}",
                rejected_candidates=["consulting"],
                converged=False,
            )
            for i in range(5)
        ]
        report_rejected_candidates(events)
        out = capsys.readouterr().out
        assert "missing category" in out.lower() or "boundary" in out.lower()

    def test_defect_signal_lexical_misalignment(self, capsys):
        # High unique docs + mostly converged → lexical misalignment
        events = [
            summary(
                document_id=f"doc-{i}",
                rejected_candidates=["api"],
                converged=True,
            )
            for i in range(5)
        ]
        report_rejected_candidates(events)
        out = capsys.readouterr().out
        assert "lexical" in out.lower()

    def test_sessions_with_rejections_count(self, capsys):
        events = [
            summary(document_id="doc-1", rejected_candidates=["backend"]),
            summary(document_id="doc-2", rejected_candidates=[]),
        ]
        report_rejected_candidates(events)
        out = capsys.readouterr().out
        assert "1" in out  # 1 session with rejections out of 2


# ─── report_convergence ───────────────────────────────────────────────────────


class TestReportConvergence:
    def test_no_summaries_prints_message(self, capsys):
        report_convergence([])
        assert "No summary events" in capsys.readouterr().out

    def test_all_converged_zero_non_convergence(self, capsys):
        events = [
            summary(total_attempts=1, converged=True, final_domain="api-design"),
            summary(
                total_attempts=2, converged=True, final_domain="api-design", document_id="doc-2"
            ),
        ]
        report_convergence(events)
        out = capsys.readouterr().out
        assert "0.0%" in out

    def test_non_convergence_rate_calculated(self, capsys):
        events = [
            summary(
                total_attempts=3,
                converged=False,
                final_domain=None,
                abort_reason="max_attempts_exceeded",
            ),
            summary(
                total_attempts=1, converged=True, final_domain="api-design", document_id="doc-2"
            ),
        ]
        report_convergence(events)
        out = capsys.readouterr().out
        assert "50.0%" in out

    def test_mean_attempts_converged_only(self, capsys):
        # Converged: 1 + 3 = 4 / 2 = 2.0 mean
        # Non-converged (3 attempts) must NOT affect mean
        events = [
            summary(total_attempts=1, converged=True, final_domain="api-design"),
            summary(
                total_attempts=3, converged=True, final_domain="api-design", document_id="doc-2"
            ),
            summary(total_attempts=3, converged=False, final_domain=None, document_id="doc-3"),
        ]
        report_convergence(events)
        assert "2.00" in capsys.readouterr().out

    def test_single_domain_no_breakdown(self, capsys):
        events = [summary(total_attempts=1, converged=True, final_domain="api-design")]
        report_convergence(events)
        out = capsys.readouterr().out
        assert "Insufficient" in out

    def test_multiple_domains_shown(self, capsys):
        events = [
            summary(total_attempts=1, converged=True, final_domain="api-design"),
            summary(total_attempts=2, converged=True, final_domain="devops", document_id="doc-2"),
        ]
        report_convergence(events)
        out = capsys.readouterr().out
        assert "api-design" in out
        assert "devops" in out

    def test_high_friction_domain_flagged(self, capsys):
        # domain "consulting" → 5/5 not converged → 100% > 15% threshold
        events = [
            summary(
                document_id=f"doc-{i}",
                total_attempts=3,
                converged=False,
                final_domain=None,
                abort_reason="max_attempts_exceeded",
            )
            for i in range(5)
        ] + [
            summary(
                document_id="doc-ok",
                total_attempts=1,
                converged=True,
                final_domain="api-design",
            )
        ]
        report_convergence(events)
        assert "HIGH FRICTION" in capsys.readouterr().out


# ─── main() ───────────────────────────────────────────────────────────────────


class TestMain:
    def _write_sample(self, tmp_path: Path) -> Path:
        path = tmp_path / "events.jsonl"
        events = [
            attempt(attempt_num=1, converged=False, errors=[domain_error()]),
            attempt(attempt_num=2, converged=True, errors=[]),
            summary(
                total_attempts=2,
                converged=True,
                rejected_candidates=["backend"],
                final_domain="api-design",
            ),
        ]
        write_jsonl(path, events)
        return path

    def test_all_reports_run(self, tmp_path, capsys, monkeypatch):
        path = self._write_sample(tmp_path)
        monkeypatch.setattr(sys, "argv", ["analyze_telemetry", "--input", str(path)])
        main()
        out = capsys.readouterr().out
        assert "Report A" in out
        assert "Report B" in out
        assert "Report C" in out

    def test_retry_rate_only(self, tmp_path, capsys, monkeypatch):
        path = self._write_sample(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            ["analyze_telemetry", "--input", str(path), "--report", "retry-rate"],
        )
        main()
        out = capsys.readouterr().out
        assert "Report A" in out
        assert "Report B" not in out
        assert "Report C" not in out

    def test_candidates_only(self, tmp_path, capsys, monkeypatch):
        path = self._write_sample(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            ["analyze_telemetry", "--input", str(path), "--report", "candidates"],
        )
        main()
        out = capsys.readouterr().out
        assert "Report B" in out
        assert "Report A" not in out

    def test_convergence_only(self, tmp_path, capsys, monkeypatch):
        path = self._write_sample(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            ["analyze_telemetry", "--input", str(path), "--report", "convergence"],
        )
        main()
        out = capsys.readouterr().out
        assert "Report C" in out
        assert "Report A" not in out

    def test_custom_flag_threshold(self, tmp_path, capsys, monkeypatch):
        path = self._write_sample(tmp_path)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "analyze_telemetry",
                "--input",
                str(path),
                "--report",
                "retry-rate",
                "--flag-threshold",
                "0.01",
            ],
        )
        main()
        # Very low threshold → everything flagged
        assert "REVIEW" in capsys.readouterr().out

    def test_missing_file_exits(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            sys,
            "argv",
            ["analyze_telemetry", "--input", str(tmp_path / "nope.jsonl")],
        )
        with pytest.raises(SystemExit):
            main()
