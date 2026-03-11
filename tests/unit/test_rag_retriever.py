"""Unit tests for RAG Phase 2 retriever."""

from __future__ import annotations

import pytest

from rag.config import RAGConfig
from rag.retriever import RetrievalResult, retrieve


class _FakeCollection:
    def query(self, query_texts, n_results, include):
        assert query_texts == ["api rate limiting"]
        assert n_results == 2
        assert "documents" in include
        return {
            "ids": [["chunk-1", "chunk-2"]],
            "documents": [["First chunk", "Second chunk"]],
            "metadatas": [[{"source": "a.md", "section": "Intro"}, {"source": "b.md"}]],
            "distances": [[0.11, 0.37]],
        }


def _config(tmp_path):
    return RAGConfig(
        corpus_dir=tmp_path / "corpus",
        persist_directory=tmp_path / ".chroma",
        collection_name="akf_corpus",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        markdown_glob="*.md",
        batch_size=8,
    )


def test_retrieve_returns_ranked_hits(monkeypatch, tmp_path):
    monkeypatch.setattr("rag.retriever._build_collection", lambda config: _FakeCollection())

    result = retrieve("api rate limiting", top_k=2, config=_config(tmp_path))

    assert isinstance(result, RetrievalResult)
    assert result.top_k == 2
    assert len(result.hits) == 2
    assert result.hits[0].chunk_id == "chunk-1"
    assert result.hits[0].metadata["source"] == "a.md"
    assert result.hits[1].distance == pytest.approx(0.37)


def test_retrieve_rejects_empty_query(tmp_path):
    with pytest.raises(ValueError, match="query must not be empty"):
        retrieve("   ", config=_config(tmp_path))
