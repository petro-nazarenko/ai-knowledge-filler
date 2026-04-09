"""Tests for RAG context injection in Pipeline.generate() (Step 5).

Covers:
  1. RAG available, hits returned → system_prompt contains ## RELEVANT CORPUS CONTEXT
  2. RAG unavailable (import error) → generate proceeds normally, no exception
  3. RAG returns empty hits → system_prompt unchanged
  4. rag_enabled=False → _try_retrieve never called
  5. _try_retrieve() builds correct formatted string from RetrievalHit
"""

from unittest.mock import patch, MagicMock

import pytest

from rag.retriever import RetrievalResult, RetrievalHit

# ─── SHARED FIXTURES ──────────────────────────────────────────────────────────

MOCK_HIT = RetrievalHit(
    chunk_id="abc",
    content="## Decorators\nA decorator wraps a function.",
    metadata={"filename": "Python_Decorators.md"},
    distance=0.15,
)

MOCK_RESULT_WITH_HITS = RetrievalResult(
    query="Python decorators",
    top_k=3,
    hits=[MOCK_HIT],
)

MOCK_RESULT_EMPTY = RetrievalResult(
    query="Python decorators",
    top_k=3,
    hits=[],
)

VALID_GENERATED_CONTENT = """\
---
title: Python Decorators Guide
type: guide
domain: backend-engineering
level: intermediate
status: active
schema_version: "1.0.0"
created: 2026-01-01
updated: 2026-01-01
---

# Python Decorators

A decorator wraps a function to extend its behaviour.
"""

RAG_CONTEXT_SNIPPET = "[Python_Decorators.md]\n## Decorators\nA decorator wraps a function."


def _make_pipeline(**kwargs):
    """Helper: create a Pipeline with mocked internals."""
    from akf.pipeline import Pipeline

    p = Pipeline(output="/tmp/akf_test", model="auto", verbose=False, **kwargs)
    p._system_prompt = "You are a helpful knowledge assistant."
    return p


def _mock_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.display_name = "MockLLM"
    provider.model_name = "mock-model"
    provider.generate.return_value = VALID_GENERATED_CONTENT
    return provider


def _mock_commit(committed=True):
    result = MagicMock()
    result.committed = committed
    result.path = "/tmp/akf_test/out.md"
    result.file_path = "/tmp/akf_test/out.md"
    result.blocking_errors = []
    return result


# ─── TEST 1: RAG hits → system_prompt injected ────────────────────────────────


def test_rag_context_injected_when_hits_available():
    """When _try_retrieve returns non-empty context, system_prompt gets ## RELEVANT CORPUS CONTEXT."""
    pipeline = _make_pipeline(rag_enabled=True)
    provider = _mock_provider()

    captured_system_prompts = []

    def capture_generate(prompt, system_prompt):
        captured_system_prompts.append(system_prompt)
        return VALID_GENERATED_CONTENT

    provider.generate.side_effect = capture_generate

    with (
        patch("akf.pipeline._try_retrieve", return_value=RAG_CONTEXT_SNIPPET) as mock_retrieve,
        patch("llm_providers.get_provider", return_value=provider),
        patch("akf.telemetry.TelemetryWriter"),
        patch("akf.telemetry.new_generation_id", return_value="test-gen-id"),
        patch("akf.validator.validate", return_value=[]),
        patch("akf.commit_gate.commit", return_value=_mock_commit()),
    ):

        result = pipeline.generate("Python decorators guide")

    mock_retrieve.assert_called_once_with("Python decorators guide", top_k=3)
    assert len(captured_system_prompts) == 1
    assert "## RELEVANT CORPUS CONTEXT" in captured_system_prompts[0]
    assert RAG_CONTEXT_SNIPPET in captured_system_prompts[0]


# ─── TEST 2: RAG unavailable (import error) → proceeds without exception ──────


def test_rag_unavailable_proceeds_without_exception():
    """When _try_retrieve returns '' (e.g. ImportError swallowed), generate() continues normally."""
    pipeline = _make_pipeline(rag_enabled=True)
    provider = _mock_provider()

    with (
        patch("akf.pipeline._try_retrieve", return_value=""),
        patch("llm_providers.get_provider", return_value=provider),
        patch("akf.telemetry.TelemetryWriter"),
        patch("akf.telemetry.new_generation_id", return_value="test-gen-id"),
        patch("akf.validator.validate", return_value=[]),
        patch("akf.commit_gate.commit", return_value=_mock_commit()),
    ):

        result = pipeline.generate("Python decorators guide")

    # Should succeed without raising
    assert result is not None
    assert provider.generate.called


def test_try_retrieve_silently_swallows_import_error():
    """_try_retrieve() returns '' when rag.retriever cannot be imported."""
    from akf.pipeline import _try_retrieve

    with patch.dict("sys.modules", {"rag.retriever": None}):
        result = _try_retrieve("any query", top_k=3)

    assert result == ""


# ─── TEST 3: RAG returns empty hits → system_prompt unchanged ─────────────────


def test_rag_empty_hits_system_prompt_unchanged():
    """When _try_retrieve returns '', system_prompt does NOT contain RAG section."""
    pipeline = _make_pipeline(rag_enabled=True)
    provider = _mock_provider()

    captured_system_prompts = []

    def capture_generate(prompt, system_prompt):
        captured_system_prompts.append(system_prompt)
        return VALID_GENERATED_CONTENT

    provider.generate.side_effect = capture_generate

    with (
        patch("akf.pipeline._try_retrieve", return_value=""),
        patch("llm_providers.get_provider", return_value=provider),
        patch("akf.telemetry.TelemetryWriter"),
        patch("akf.telemetry.new_generation_id", return_value="test-gen-id"),
        patch("akf.validator.validate", return_value=[]),
        patch("akf.commit_gate.commit", return_value=_mock_commit()),
    ):

        result = pipeline.generate("Python decorators guide")

    assert len(captured_system_prompts) == 1
    assert "## RELEVANT CORPUS CONTEXT" not in captured_system_prompts[0]


# ─── TEST 4: rag_enabled=False → _try_retrieve never called ───────────────────


def test_no_rag_flag_skips_retrieval():
    """When Pipeline(rag_enabled=False), _try_retrieve is never invoked."""
    pipeline = _make_pipeline(rag_enabled=False)
    provider = _mock_provider()

    with (
        patch("akf.pipeline._try_retrieve") as mock_retrieve,
        patch("llm_providers.get_provider", return_value=provider),
        patch("akf.telemetry.TelemetryWriter"),
        patch("akf.telemetry.new_generation_id", return_value="test-gen-id"),
        patch("akf.validator.validate", return_value=[]),
        patch("akf.commit_gate.commit", return_value=_mock_commit()),
    ):

        result = pipeline.generate("Python decorators guide")

    mock_retrieve.assert_not_called()


# ─── TEST 5: _try_retrieve() formats hits correctly ───────────────────────────


def test_try_retrieve_formats_multiple_hits():
    """_try_retrieve() builds correct formatted string using filename metadata."""
    from akf.pipeline import _try_retrieve

    hit1 = RetrievalHit(
        chunk_id="id1",
        content="Content one.",
        metadata={"filename": "File_One.md"},
        distance=0.1,
    )
    hit2 = RetrievalHit(
        chunk_id="id2",
        content="Content two.",
        metadata={"filename": "File_Two.md"},
        distance=0.2,
    )
    mock_result = RetrievalResult(query="test query", top_k=2, hits=[hit1, hit2])

    with patch("rag.retriever.retrieve", return_value=mock_result):
        output = _try_retrieve("test query", top_k=2)

    assert "[File_One.md]\nContent one." in output
    assert "[File_Two.md]\nContent two." in output
    assert "\n\n---\n\n" in output


# ─── TEST 6: _sanitize_corpus_chunk guardrails (SEC-1) ────────────────────────


def test_sanitize_corpus_chunk_strips_control_chars():
    """_sanitize_corpus_chunk removes null bytes and other control characters."""
    from akf.pipeline import _sanitize_corpus_chunk

    dirty = "Normal text\x00with null\x01bytes\x1f and more"
    result = _sanitize_corpus_chunk(dirty)
    assert "\x00" not in result
    assert "\x01" not in result
    assert "\x1f" not in result
    assert "Normal text" in result
    assert "with null" in result


def test_sanitize_corpus_chunk_preserves_tabs_and_newlines():
    """_sanitize_corpus_chunk keeps tab, newline, and carriage return."""
    from akf.pipeline import _sanitize_corpus_chunk

    text = "Line one\nLine two\tindented\r\nWindows line"
    result = _sanitize_corpus_chunk(text)
    assert "\n" in result
    assert "\t" in result
    assert "\r" in result


def test_sanitize_corpus_chunk_truncates_long_content():
    """_sanitize_corpus_chunk truncates content exceeding _CORPUS_CHUNK_MAX_CHARS."""
    from akf.pipeline import _sanitize_corpus_chunk, _CORPUS_CHUNK_MAX_CHARS

    long_text = "x" * (_CORPUS_CHUNK_MAX_CHARS + 500)
    result = _sanitize_corpus_chunk(long_text)
    assert len(result) == _CORPUS_CHUNK_MAX_CHARS


def test_try_retrieve_sanitizes_chunk_content():
    """_try_retrieve sanitizes content before including it in context string."""
    from akf.pipeline import _try_retrieve

    dirty_hit = RetrievalHit(
        chunk_id="id1",
        content="Clean content\x00with null byte",
        metadata={"filename": "File\x01.md"},
        distance=0.1,
    )
    mock_result = RetrievalResult(query="test query", top_k=1, hits=[dirty_hit])

    with patch("rag.retriever.retrieve", return_value=mock_result):
        output = _try_retrieve("test query", top_k=1)

    assert "\x00" not in output
    assert "\x01" not in output
    assert "Clean content" in output
