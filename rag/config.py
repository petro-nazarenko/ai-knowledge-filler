"""Configuration for Phase 1 RAG corpus indexing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RAGConfig:
    """Resolved settings for local corpus indexing."""

    corpus_dir: Path
    persist_directory: Path
    collection_name: str
    embedding_model: str
    markdown_glob: str
    batch_size: int


def load_config() -> RAGConfig:
    """Load RAG indexer settings from environment with safe defaults."""

    corpus_dir = Path(os.getenv("RAG_CORPUS_DIR", "corpus")).expanduser()
    persist_directory = Path(os.getenv("RAG_CHROMA_PATH", "rag/.chroma")).expanduser()
    collection_name = os.getenv("RAG_COLLECTION_NAME", "akf_corpus")
    embedding_model = os.getenv(
        "RAG_EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )
    markdown_glob = os.getenv("RAG_MARKDOWN_GLOB", "*.md")
    batch_size_raw = os.getenv("RAG_BATCH_SIZE", "64")

    try:
        batch_size = max(1, int(batch_size_raw))
    except ValueError:
        batch_size = 64

    return RAGConfig(
        corpus_dir=corpus_dir,
        persist_directory=persist_directory,
        collection_name=collection_name,
        embedding_model=embedding_model,
        markdown_glob=markdown_glob,
        batch_size=batch_size,
    )
