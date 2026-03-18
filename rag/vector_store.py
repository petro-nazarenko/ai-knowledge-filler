"""Android-compatible flat numpy vector store for RAG.

Replaces chromadb with a pure-Python/numpy solution that works on Android/Termux
without requiring Rust/maturin compilation. Index is persisted as JSON + .npy files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def _cosine_distances(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Return cosine distance (1 - similarity) from query to each row in matrix."""
    q_norm = float(np.linalg.norm(query_vec))
    if q_norm == 0.0:
        return np.ones(len(matrix), dtype=np.float32)
    q = query_vec / q_norm
    row_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    row_norms = np.where(row_norms == 0.0, 1.0, row_norms)
    normalized = matrix / row_norms
    similarities = normalized @ q
    return (1.0 - similarities).astype(np.float32)


class FlatIndex:
    """Pure-numpy vector store persisted as JSON + .npy files.

    Public interface mirrors the subset of the chromadb Collection API used by
    indexer.py and retriever.py:
        add(ids, documents, metadatas)
        delete(where)
        count()
        query(query_texts, n_results, include)
    """

    def __init__(self, persist_dir: Path, collection_name: str, embedding_model: str) -> None:
        try:
            import numpy  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "Missing dependency 'numpy'. Install with: pip install numpy"
            ) from exc

        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._docs_path = persist_dir / f"{collection_name}_docs.json"
        self._emb_path = persist_dir / f"{collection_name}_embeddings.npy"
        self._model: Any = None

        self._docs: list[dict[str, Any]] = []
        self._embeddings: np.ndarray = np.empty((0, 0), dtype=np.float32)
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._docs_path.exists():
            with open(self._docs_path, encoding="utf-8") as f:
                self._docs = json.load(f)
        if self._emb_path.exists() and self._docs:
            self._embeddings = np.load(self._emb_path)
        else:
            self._embeddings = np.empty((0, 0), dtype=np.float32)

    def _save(self) -> None:
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        with open(self._docs_path, "w", encoding="utf-8") as f:
            json.dump(self._docs, f, ensure_ascii=False)
        if self._docs:
            np.save(self._emb_path, self._embeddings)
        elif self._emb_path.exists():
            self._emb_path.unlink()

    # ------------------------------------------------------------------
    # Embedding helper
    # ------------------------------------------------------------------

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "Missing dependency 'sentence-transformers'. "
                    "Install with: pip install sentence-transformers"
                ) from exc
            self._model = SentenceTransformer(self._embedding_model)
        return self._model

    def _embed(self, texts: list[str]) -> np.ndarray:
        return (
            self._get_model()
            .encode(texts, normalize_embeddings=True, convert_to_numpy=True)
            .astype(np.float32)
        )

    # ------------------------------------------------------------------
    # Collection API
    # ------------------------------------------------------------------

    def delete(self, where: dict[str, Any] | None = None) -> None:
        """Remove all chunks whose metadata matches *where* filter."""
        if not where or "source" not in where:
            return
        source = where["source"]
        keep = [i for i, d in enumerate(self._docs) if d["metadata"].get("source") != source]
        if len(keep) == len(self._docs):
            return  # nothing removed
        self._docs = [self._docs[i] for i in keep]
        if not keep:
            self._embeddings = np.empty((0, 0), dtype=np.float32)
        elif self._embeddings.shape[0] > 0:
            self._embeddings = self._embeddings[keep]
        self._save()

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Embed *documents* and append them to the index."""
        new_emb = self._embed(documents)
        for i, doc_id in enumerate(ids):
            self._docs.append({"id": doc_id, "document": documents[i], "metadata": metadatas[i]})
        if self._embeddings.shape[0] == 0:
            self._embeddings = new_emb
        else:
            self._embeddings = np.vstack([self._embeddings, new_emb])
        self._save()

    def count(self) -> int:
        return len(self._docs)

    def query(
        self,
        query_texts: list[str],
        n_results: int,
        include: list[str],
    ) -> dict[str, Any]:
        """Return top-n_results chunks closest to query_texts[0]."""
        empty: dict[str, Any] = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        if not self._docs:
            return empty

        query_emb = self._embed(query_texts[:1])[0]
        distances = _cosine_distances(query_emb, self._embeddings)
        top_k = min(n_results, len(self._docs))
        top_indices = np.argsort(distances)[:top_k].tolist()

        return {
            "ids": [[self._docs[i]["id"] for i in top_indices]],
            "documents": [[self._docs[i]["document"] for i in top_indices]],
            "metadatas": [[self._docs[i]["metadata"] for i in top_indices]],
            "distances": [[float(distances[i]) for i in top_indices]],
        }
