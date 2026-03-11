"""Unit tests for `akf ask` CLI command."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from cli import cmd_ask


@dataclass
class _Args:
    query: str
    top_k: int = 5
    model: str = "auto"


def test_cmd_ask_prints_answer_and_sources(monkeypatch, capsys):
    from rag.copilot import CopilotAnswer

    def _fake_answer_question(query: str, top_k: int, model: str):
        assert query == "How to rate limit FastAPI?"
        assert top_k == 3
        assert model == "auto"
        return CopilotAnswer(
            query=query,
            answer="Use SlowAPI middleware and return limit headers.",
            sources=["a.md", "b.md"],
            model="fake",
            top_k=top_k,
            hits_used=2,
        )

    monkeypatch.setattr("rag.copilot.answer_question", _fake_answer_question)

    cmd_ask(_Args(query="How to rate limit FastAPI?", top_k=3, model="auto"))

    out = capsys.readouterr().out
    assert "SlowAPI" in out
    assert "Sources:" in out
    assert "a.md" in out
    assert "b.md" in out


def test_cmd_ask_empty_query_exits(monkeypatch):
    with pytest.raises(SystemExit) as exc:
        cmd_ask(_Args(query="   "))
    assert exc.value.code == 1


def test_cmd_ask_runtime_error_exits(monkeypatch, capsys):
    def _boom(query: str, top_k: int, model: str):
        raise RuntimeError("index missing")

    monkeypatch.setattr("rag.copilot.answer_question", _boom)

    with pytest.raises(SystemExit) as exc:
        cmd_ask(_Args(query="What is AKF?", top_k=2, model="auto"))

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "RAG ask failed" in out
