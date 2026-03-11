"""Unit tests for RAG Phase 1 indexer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rag.config import RAGConfig
from rag.indexer import index_corpus


@dataclass
class _FakeDoc:
    page_content: str
    metadata: dict


class _FakeSplitter:
    def __init__(self, headers_to_split_on=None, strip_headers=False):
        self.headers_to_split_on = headers_to_split_on
        self.strip_headers = strip_headers

    def split_text(self, text: str):
        parts = text.split("## ")
        docs = []
        for part in parts:
            cleaned = part.strip()
            if not cleaned:
                continue
            lines = cleaned.splitlines()
            section = lines[0].strip()
            docs.append(_FakeDoc(page_content=cleaned, metadata={"section": section}))
        return docs


class _FakeFrontmatterPost:
    def __init__(self, metadata: dict, content: str):
        self.metadata = metadata
        self.content = content


class _FakeFrontmatterModule:
    @staticmethod
    def load(path: Path):
        raw = path.read_text(encoding="utf-8")
        # Minimal parser for test fixtures only.
        if raw.startswith("---"):
            _, header, body = raw.split("---", 2)
            metadata = {}
            for line in header.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    metadata[k.strip()] = v.strip().strip('"')
            return _FakeFrontmatterPost(metadata=metadata, content=body.strip())
        return _FakeFrontmatterPost(metadata={}, content=raw)


class _FakeCollection:
    def __init__(self):
        self.docs = []

    def delete(self, where=None):
        if not where or "source" not in where:
            return
        source = where["source"]
        self.docs = [d for d in self.docs if d["metadata"].get("source") != source]

    def add(self, ids, documents, metadatas):
        for idx, doc_id in enumerate(ids):
            self.docs.append(
                {
                    "id": doc_id,
                    "document": documents[idx],
                    "metadata": metadatas[idx],
                }
            )

    def count(self):
        return len(self.docs)


def test_index_corpus_two_markdown_files(monkeypatch, tmp_path):
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir(parents=True)

    (corpus_dir / "first.md").write_text(
        """---
title: \"First\"
---

## Intro
Alpha content.

## Details
Beta content.
""",
        encoding="utf-8",
    )
    (corpus_dir / "second.md").write_text(
        """---
title: \"Second\"
---

## Overview
Gamma content.
""",
        encoding="utf-8",
    )

    fake_collection = _FakeCollection()

    monkeypatch.setattr("rag.indexer._load_frontmatter_module", lambda: _FakeFrontmatterModule())
    monkeypatch.setattr("rag.indexer._load_markdown_splitter_class", lambda: _FakeSplitter)
    monkeypatch.setattr("rag.indexer._build_collection", lambda config: fake_collection)

    config = RAGConfig(
        corpus_dir=corpus_dir,
        persist_directory=tmp_path / ".chroma",
        collection_name="akf_corpus",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        markdown_glob="*.md",
        batch_size=10,
    )

    stats = index_corpus(config)

    assert stats.files_indexed == 2
    assert stats.chunks_indexed == 3
    assert stats.collection_count == 3

    sources = {item["metadata"]["filename"] for item in fake_collection.docs}
    assert sources == {"first.md", "second.md"}
