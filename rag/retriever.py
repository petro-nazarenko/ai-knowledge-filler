"""Phase 2 retriever for semantic search over local Chroma index."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    from rag.config import RAGConfig, load_config
except ModuleNotFoundError:
    # Support direct execution: `python rag/retriever.py`
    from config import RAGConfig, load_config


def _build_collection(config: RAGConfig) -> Any:
    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    except ImportError as exc:
        raise ImportError(
            "Missing dependency 'chromadb'. Install with: pip install chromadb sentence-transformers"
        ) from exc

    config.persist_directory.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(config.persist_directory))
    embedding_function = SentenceTransformerEmbeddingFunction(model_name=config.embedding_model)
    return client.get_or_create_collection(
        name=config.collection_name,
        embedding_function=embedding_function,
    )


@dataclass
class RetrievalHit:
    """Single retrieved chunk with metadata and distance score."""

    chunk_id: str
    content: str
    metadata: dict[str, Any]
    distance: float


@dataclass
class RetrievalResult:
    """Top-K retrieval response."""

    query: str
    top_k: int
    hits: list[RetrievalHit]


def retrieve(query: str, top_k: int = 5, config: RAGConfig | None = None) -> RetrievalResult:
    """Retrieve top-k relevant chunks from local Chroma collection."""

    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query must not be empty")

    resolved_top_k = max(1, int(top_k))
    resolved = config or load_config()
    collection = _build_collection(resolved)

    result = collection.query(
        query_texts=[clean_query],
        n_results=resolved_top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    hits: list[RetrievalHit] = []
    for idx, chunk_id in enumerate(ids):
        content = documents[idx] if idx < len(documents) else ""
        metadata = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
        distance = float(distances[idx]) if idx < len(distances) else 0.0
        hits.append(
            RetrievalHit(
                chunk_id=str(chunk_id),
                content=str(content),
                metadata=dict(metadata),
                distance=distance,
            )
        )

    return RetrievalResult(query=clean_query, top_k=resolved_top_k, hits=hits)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Phase 2 RAG retriever")
    parser.add_argument("query", help="Natural language query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to return")
    args = parser.parse_args()

    result = retrieve(query=args.query, top_k=args.top_k)
    print(f"Query: {result.query}")
    print(f"Hits: {len(result.hits)}")
    for idx, hit in enumerate(result.hits, 1):
        source = hit.metadata.get("source", "unknown")
        section = hit.metadata.get("section", "")
        print(f"{idx}. distance={hit.distance:.4f} source={source} section={section}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
