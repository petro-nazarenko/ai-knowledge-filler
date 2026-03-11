---
title: "AKF RAG Copilot"
type: spec
project: akf
status: draft
version: v0.1
created: 2026-03-11
---

## Overview

A RAG-based copilot built into AKF. Transforms `corpus/` from a collection of files into a cognitive system — answers questions using knowledge from your own notes, in the context of your current task.

## Problem Statement

47+ reference files in `corpus/` are a valuable dataset, but without an activation mechanism. To use the knowledge, you need to remember where it lives and search manually. The copilot removes this barrier: ask in natural language, the system finds relevant context and answers.

## Scope

**In scope:**
- Indexing `corpus/` (Markdown with frontmatter)
- Q&A interface via CLI
- Filtering by `domain` / `tags` from frontmatter
- Source citation (which file the answer came from)

**Out of scope (v0.1):**
- Web UI
- Auto-reindex on file changes
- Multilingual search
- Writing feedback back into notes

---

## Architecture

```
corpus/ (47 .md files)
    │
    ▼
[Indexer]
    │  parse frontmatter + chunk content
    │  embed via sentence-transformers
    ▼
[Chroma DB] ── local, persistent
    │
    ▼
[Retriever]
    │  top-k relevant chunks
    │  filter by domain/tags
    ▼
[LLM — Claude API]
    │  system prompt + retrieved context + question
    ▼
[CLI Output]
    │  answer + source files cited
```

### Components

| Component | Technology | Reason |
|-----------|-----------|--------|
| Vector DB | ChromaDB | Local, zero-config, Python |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Free, no API call per chunk |
| LLM | Claude claude-sonnet-4-20250514 via API | Already configured |
| CLI | Python argparse | Mobile-first, Termux compatible |
| Chunking | LangChain `MarkdownHeaderTextSplitter` | Smart split by H2/H3 |

---

## File Structure

```
akf/
├── corpus/               # Existing 47 files (source of truth)
├── rag/
│   ├── __init__.py
│   ├── indexer.py        # Parse, chunk, embed, write to Chroma
│   ├── retriever.py      # Similarity search + filters
│   ├── copilot.py        # Prompt assembly, Claude API call
│   ├── cli.py            # Entry point
│   └── config.py         # Paths and parameters
├── .chroma/              # Local DB (gitignore)
├── requirements_rag.txt
└── STATUS.md
```

---

## Data Model

### Chunk metadata (stored in Chroma)

```python
{
    "source": "corpus/Backend_Service_Architecture_FastAPI.md",
    "title": "Backend Service Architecture with FastAPI",
    "domain": "backend-engineering",
    "tags": ["fastapi", "async", "python"],
    "level": "intermediate",
    "section": "Dependency Injection",  # from H2/H3 header
    "version": "v1.0"
}
```

### Chunk strategy

- Split by H2 sections
- Max 500 tokens per chunk
- 50 token overlap between adjacent chunks

---

## CLI Interface

```bash
# Basic question
python -m rag.cli "How to set up async database access in FastAPI?"

# Filter by domain
python -m rag.cli "cost optimization" --domain devops

# Reindex corpus
python -m rag.cli --reindex

# Show sources without LLM answer
python -m rag.cli "spot instances" --sources-only

# Number of chunks to retrieve
python -m rag.cli "repository pattern" --top-k 5
```

### Output format

```
Query: How to set up async database access in FastAPI?

Answer:
[Claude's answer based on retrieved context]

Sources:
  - corpus/Backend_Service_Architecture_FastAPI.md § Async Database Access (SQLAlchemy 2.0)
  - corpus/Backend_API_Production_Readiness.md § Database Configuration
```

---

## Prompt Template

```
System:
You are a personal knowledge assistant. Answer the user's question
using ONLY the provided context from their knowledge base.
If the context does not contain enough information, say so clearly.
Always cite which document and section your answer comes from.
Be concise and practical.

Context:
{retrieved_chunks}

Question: {user_query}
```

---

## Implementation Plan

### Phase 1 — MVP (target: 1 day)
- [ ] `indexer.py` — parse 2 test files + write to Chroma
- [ ] `retriever.py` — basic similarity search
- [ ] `copilot.py` — Claude API call with context
- [ ] `cli.py` — minimal interface
- [ ] Validate on FastAPI and AWS cost notes

### Phase 2 — Full corpus (target: +1 day)
- [ ] Index all 47 files
- [ ] Add domain/tags filters
- [ ] Add `--sources-only` mode
- [ ] Update `STATUS.md`

### Phase 3 — Polish (as needed)
- [ ] Auto-reindex when corpus/ changes
- [ ] Streaming output for long responses
- [ ] Bash alias `akf "question"` for quick access

---

## Dependencies

```
# requirements_rag.txt
chromadb>=0.4.0
sentence-transformers>=2.2.0
langchain>=0.1.0
langchain-community>=0.0.1
anthropic>=0.20.0
python-frontmatter>=1.0.0
```

---

## Config

```python
# rag/config.py
CORPUS_DIR = "../corpus"
CHROMA_DIR = "../.chroma"
COLLECTION_NAME = "akf_corpus"
EMBED_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "claude-sonnet-4-20250514"
TOP_K = 4
MAX_CHUNK_TOKENS = 500
CHUNK_OVERLAP = 50
```

---

## Success Criteria

- Answer to a FastAPI question in < 5 seconds
- Source always cited
- Runs in Termux with no additional services
- Full reindex of 47 files in < 2 minutes

---

## Open Questions

1. Should titles get a separate embedding boost over body text?
2. Should query history be stored to improve results over time?
3. Should `related` notes be automatically included in retrieved context?
