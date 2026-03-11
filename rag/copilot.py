"""Phase 3 RAG copilot: retrieval + answer synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm_providers import get_provider

try:
    from rag.retriever import RetrievalHit, RetrievalResult, retrieve
except ModuleNotFoundError:
    # Support direct execution: `python rag/copilot.py`
    from retriever import RetrievalHit, RetrievalResult, retrieve


_SYSTEM_PROMPT = """You are AKF RAG Copilot.
Answer the user's question only using the provided context chunks.
If context is insufficient, explicitly say what is missing.
Keep the answer concise, practical, and factual.
Always include a short 'Sources' section with source file names.
"""


@dataclass
class CopilotAnswer:
    """Final answer generated from retrieved context."""

    query: str
    answer: str
    sources: list[str]
    model: str
    top_k: int
    hits_used: int
    insufficient_context: bool = False


def _format_context(hits: list[RetrievalHit]) -> str:
    blocks: list[str] = []
    for idx, hit in enumerate(hits, 1):
        source = str(hit.metadata.get("source", "unknown"))
        section = str(hit.metadata.get("section", ""))
        distance = f"{hit.distance:.4f}"
        blocks.append(
            "\n".join(
                [
                    f"[CHUNK {idx}]",
                    f"source: {source}",
                    f"section: {section}",
                    f"distance: {distance}",
                    "content:",
                    hit.content,
                ]
            )
        )
    return "\n\n".join(blocks)


def _build_user_prompt(query: str, retrieval: RetrievalResult) -> str:
    context_text = _format_context(retrieval.hits)
    return (
        f"Question:\n{query}\n\n"
        "Context chunks:\n"
        f"{context_text}\n\n"
        "Instructions:\n"
        "1) Answer using only the context chunks.\n"
        "2) If uncertain, state uncertainty explicitly.\n"
        "3) End with 'Sources:' and bullet list of source file names."
    )


def _filter_hits_by_distance(hits: list[RetrievalHit], max_distance: float | None) -> list[RetrievalHit]:
    if max_distance is None:
        return hits
    return [hit for hit in hits if hit.distance <= max_distance]


def answer_question(
    query: str,
    top_k: int = 5,
    model: str = "auto",
    max_distance: float | None = None,
) -> CopilotAnswer:
    """Retrieve relevant chunks and synthesize a final answer via selected LLM."""

    retrieval = retrieve(query=query, top_k=top_k)
    filtered_hits = _filter_hits_by_distance(retrieval.hits, max_distance)
    if not filtered_hits:
        return CopilotAnswer(
            query=query,
            answer=(
                "Insufficient relevant context in the local index for a grounded answer. "
                "Try re-running indexing, broadening the query, or relaxing max_distance."
            ),
            sources=[],
            model="none",
            top_k=top_k,
            hits_used=0,
            insufficient_context=True,
        )

    filtered_retrieval = RetrievalResult(
        query=retrieval.query,
        top_k=retrieval.top_k,
        hits=filtered_hits,
    )

    provider = get_provider(model)
    user_prompt = _build_user_prompt(query, filtered_retrieval)
    answer = provider.generate(user_prompt, _SYSTEM_PROMPT).strip()

    source_set = {
        str(hit.metadata.get("source", "unknown"))
        for hit in filtered_hits
        if hit.metadata.get("source")
    }
    sources = sorted(source_set)

    return CopilotAnswer(
        query=query,
        answer=answer,
        sources=sources,
        model=provider.name,
        top_k=filtered_retrieval.top_k,
        hits_used=len(filtered_hits),
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Phase 3 RAG copilot")
    parser.add_argument("query", help="Natural language question")
    parser.add_argument("--top-k", type=int, default=5, help="Retrieved chunks")
    parser.add_argument("--model", default="auto", help="LLM provider name or auto")
    args = parser.parse_args()

    result = answer_question(query=args.query, top_k=args.top_k, model=args.model)

    print(f"Model: {result.model}")
    print(f"Hits used: {result.hits_used}")
    print()
    print(result.answer)
    if result.sources:
        print()
        print("Sources:")
        for source in result.sources:
            print(f"- {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
