"""Unit tests for RAG Phase 3 copilot synthesis."""

from __future__ import annotations

from rag.copilot import CopilotAnswer, answer_question
from rag.retriever import RetrievalHit, RetrievalResult


class _FakeProvider:
    name = "fake"

    def generate(self, prompt: str, system_prompt: str) -> str:
        assert "Question:" in prompt
        assert "Context chunks:" in prompt
        assert "AKF RAG Copilot" in system_prompt
        return "Use slowapi middleware and return rate-limit headers."


def test_answer_question_with_hits(monkeypatch):
    retrieval = RetrievalResult(
        query="How to rate limit?",
        top_k=2,
        hits=[
            RetrievalHit(
                chunk_id="c1",
                content="Use slowapi limiter.",
                metadata={"source": "a.md", "section": "Implementation"},
                distance=0.1,
            ),
            RetrievalHit(
                chunk_id="c2",
                content="Expose headers.",
                metadata={"source": "b.md", "section": "Headers"},
                distance=0.2,
            ),
        ],
    )

    monkeypatch.setattr("rag.copilot.retrieve", lambda query, top_k: retrieval)
    monkeypatch.setattr("rag.copilot.get_provider", lambda model: _FakeProvider())

    result = answer_question("How to rate limit?", top_k=2, model="auto")

    assert isinstance(result, CopilotAnswer)
    assert result.model == "fake"
    assert result.hits_used == 2
    assert "slowapi" in result.answer
    assert result.sources == ["a.md", "b.md"]


def test_answer_question_no_hits(monkeypatch):
    retrieval = RetrievalResult(query="q", top_k=3, hits=[])
    monkeypatch.setattr("rag.copilot.retrieve", lambda query, top_k: retrieval)

    result = answer_question("q", top_k=3)

    assert result.model == "none"
    assert result.hits_used == 0
    assert "could not find relevant context" in result.answer.lower()
