"""Phase 1 corpus indexer for local RAG retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib

try:
    from rag.config import RAGConfig, load_config
except ModuleNotFoundError:
    # Support direct execution: `python rag/indexer.py`
    from config import RAGConfig, load_config  # type: ignore[no-redef]


@dataclass
class IndexStats:
    """Indexer execution summary."""

    files_indexed: int
    chunks_indexed: int
    collection_count: int


def _load_frontmatter_module() -> Any:
    try:
        import frontmatter
    except ImportError as exc:
        raise ImportError(
            "Missing dependency 'python-frontmatter'. Install with: pip install 'ai-knowledge-filler[rag]'"
        ) from exc
    return frontmatter


def _load_markdown_splitter_class() -> Any:
    try:
        from langchain_text_splitters import MarkdownHeaderTextSplitter
    except ImportError as exc:
        raise ImportError(
            "Missing dependency 'langchain-text-splitters'. Install with: "
            "pip install langchain-text-splitters"
        ) from exc
    return MarkdownHeaderTextSplitter


def _build_collection(config: RAGConfig) -> Any:
    try:
        from rag.vector_store import FlatIndex
    except ModuleNotFoundError:
        from vector_store import FlatIndex  # type: ignore[no-redef]

    config.persist_directory.mkdir(parents=True, exist_ok=True)
    return FlatIndex(
        persist_dir=config.persist_directory,
        collection_name=config.collection_name,
        embedding_model=config.embedding_model,
    )


def _chunk_id(source: str, idx: int, content: str) -> str:
    base = f"{source}:{idx}:{content}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _read_markdown(path: Path, frontmatter_module: Any) -> tuple[dict[str, Any], str]:
    post = frontmatter_module.load(path)
    metadata = dict(getattr(post, "metadata", {}) or {})
    content = str(getattr(post, "content", "") or "")
    return metadata, content


def _split_by_h2(content: str, splitter_class: Any) -> list[Any]:
    splitter = splitter_class(headers_to_split_on=[("##", "section")], strip_headers=False)
    docs: list[Any] = splitter.split_text(content)
    if not docs and content.strip():
        docs = splitter.split_text(f"## Content\n\n{content}")
    return docs


def index_corpus(config: RAGConfig | None = None) -> IndexStats:
    """Index Markdown files from corpus into a local flat numpy vector store."""

    resolved = config or load_config()
    corpus_dir = resolved.corpus_dir
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Corpus directory does not exist: {corpus_dir}")

    frontmatter_module = _load_frontmatter_module()
    splitter_class = _load_markdown_splitter_class()
    collection = _build_collection(resolved)

    files = sorted(corpus_dir.glob(resolved.markdown_glob))

    total_chunks = 0
    total_files = 0

    for file_path in files:
        metadata, content = _read_markdown(file_path, frontmatter_module)
        docs = _split_by_h2(content, splitter_class)
        if not docs:
            continue

        source = str(file_path)
        # Keep re-indexing idempotent by replacing chunks for this source file.
        collection.delete(where={"source": source})

        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        ids: list[str] = []

        for idx, doc in enumerate(docs):
            chunk_text = getattr(doc, "page_content", "")
            if not chunk_text or not chunk_text.strip():
                continue

            section = ""
            doc_metadata = getattr(doc, "metadata", {}) or {}
            if isinstance(doc_metadata, dict):
                section = str(doc_metadata.get("section", ""))

            chunk_metadata = {
                "source": source,
                "filename": file_path.name,
                "title": str(metadata.get("title", file_path.stem)),
                "section": section,
                "chunk_index": idx,
            }
            documents.append(chunk_text)
            metadatas.append(chunk_metadata)
            ids.append(_chunk_id(source, idx, chunk_text))

        if not documents:
            continue

        for start in range(0, len(documents), resolved.batch_size):
            end = start + resolved.batch_size
            collection.add(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )

        total_chunks += len(documents)
        total_files += 1

    collection_count = int(collection.count())
    return IndexStats(
        files_indexed=total_files,
        chunks_indexed=total_chunks,
        collection_count=collection_count,
    )


def main() -> int:
    stats = index_corpus()
    print(
        f"Indexed files={stats.files_indexed}, chunks={stats.chunks_indexed}, "
        f"collection_count={stats.collection_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
