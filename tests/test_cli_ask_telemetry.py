"""tests/test_cli_ask_telemetry.py

Fix 8 — verify that TelemetryWriter.write() is called with an AskQueryEvent
when `akf ask` is run from the CLI (cmd_ask).
"""
from __future__ import annotations

from dataclasses import dataclass

from unittest.mock import patch, MagicMock

import pytest

from cli import cmd_ask


@dataclass
class _Args:
    query: str
    top_k: int = 5
    model: str = "auto"
    no_llm: bool = False


@patch("akf.telemetry.TelemetryWriter.write")
def test_cmd_ask_emits_ask_query_event(mock_write, monkeypatch):
    """cmd_ask writes an AskQueryEvent to telemetry on a successful synthesis query."""
    from rag.copilot import CopilotAnswer

    def _fake_answer_question(query: str, top_k: int, model: str):
        return CopilotAnswer(
            query=query,
            answer="Telemetry is important.",
            sources=["telemetry.md"],
            model="mock-model",
            top_k=top_k,
            hits_used=1,
        )

    monkeypatch.setattr("rag.copilot.answer_question", _fake_answer_question)

    cmd_ask(_Args(query="How does telemetry work?"))

    mock_write.assert_called_once()
    event = mock_write.call_args[0][0]
    assert event.event_type == "ask_query"
    assert event.mode == "synthesis"
    assert event.no_llm is False
