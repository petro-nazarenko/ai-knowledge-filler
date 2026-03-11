"""RAG indexing package for corpus vectorization."""

from rag.config import RAGConfig, load_config
from rag.copilot import CopilotAnswer, answer_question
from rag.indexer import IndexStats, index_corpus
from rag.retriever import RetrievalHit, RetrievalResult, retrieve

__all__ = [
	"RAGConfig",
	"load_config",
	"CopilotAnswer",
	"answer_question",
	"IndexStats",
	"index_corpus",
	"RetrievalHit",
	"RetrievalResult",
	"retrieve",
]
