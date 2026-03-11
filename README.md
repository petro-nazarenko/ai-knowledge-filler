# AI Knowledge Filler

**Validation pipeline that prevents AI-generated files from reaching disk unless they pass schema checks**

[![CI](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/ci.yml/badge.svg)](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/ci.yml)
[![Tests](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/tests.yml/badge.svg)](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/ai-knowledge-filler.svg)](https://pypi.org/project/ai-knowledge-filler/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/tests.yml)

---

## The Problem

Every time you use an LLM to generate structured knowledge files, the output drifts — wrong enum values, missing fields, dates in the wrong format, tags as strings instead of arrays. The files look fine until something downstream breaks: a search query returning nothing, a CI check failing, a pipeline corrupting.

The standard fix is post-hoc validation — check after writing, fix manually. That doesn't scale past a few dozen files.

---

## How It Works

```
Prompt → LLM → Validation Engine → Error Normalizer → Retry Controller → Commit Gate → File
```

The LLM is the only non-deterministic component. Everything else is pure functions.

If output fails schema checks, **it never touches disk** — the Error Normalizer converts typed error codes into correction instructions and sends them back to the LLM for a retry.

If the same error fires twice on the same field, the pipeline **aborts instead of looping** — that pattern means your schema has a boundary problem, not the model.

---

## Quick Start

```bash
pip install ai-knowledge-filler

export ANTHROPIC_API_KEY="sk-ant-..."  # or GOOGLE_API_KEY, OPENAI_API_KEY, GROQ_API_KEY

akf generate "Write a guide on Docker networking"
akf validate ./vault/
```

Works with Claude, GPT-4, Gemini, Ollama.

### Quickstart by Interface

**CLI:**
```bash
akf init
akf generate "Create a guide on API rate limiting"
akf validate --path ./docs
```

**Python API:**
```python
from akf import Pipeline

pipeline = Pipeline(output="./output")
result = pipeline.generate("Create a guide on API rate limiting")
print(result.success, result.file_path)
```

**REST API:**
```bash
akf serve --port 8000
curl -X POST http://127.0.0.1:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create a guide on API rate limiting"}'
```

Minimal runnable examples are in `examples/cli_quickstart.sh`, `examples/python_api_quickstart.py`, and `examples/rest_api_quickstart.sh`.

---

## External Taxonomy Config

Your ontology lives in `akf.yaml` — not compiled into the tool:

```yaml
# akf.yaml
schema_version: "1.0.0"
vault_path: "./vault"

enums:
  type: [concept, guide, reference, checklist, project, roadmap, template, audit]
  level: [beginner, intermediate, advanced]
  status: [draft, active, completed, archived]
  domain:
    - ai-system
    - api-design
    - devops
    - security
    - system-design
```

Change your taxonomy without touching code or redeploying:

```bash
akf init          # generates akf.yaml for your vault
akf validate ./   # validates all files against your config
```

---

## Error Codes

Validation failures produce typed error codes, not free-form messages:

| Code | Field | Meaning |
|------|-------|---------|
| E001 | type / level / status | Value not in allowed enum set |
| E002 | any | Required field missing |
| E003 | created / updated | Date not ISO 8601 |
| E004 | title / tags | Type mismatch (e.g. `tags: "security"` instead of `tags: [security]`) |
| E005 | frontmatter | General schema violation |
| E006 | domain | Value not in taxonomy |
| E007 | created / updated | `created` is later than `updated` |
| E008 | related | Typed relationship label not in `relationship_types` |

The Error Normalizer translates these codes into deterministic correction instructions for the retry:

```
E006 on field "domain" (received: "backend")
→ "The 'domain' field must be one of: [api-design, backend-engineering, devops, ...]
   You used 'backend' which is not in the taxonomy. Choose the closest match."
```

---

## Retry as Signal

Retry pressure is not a failure metric.

When a domain value triggers elevated retries, the taxonomy has a **boundary problem** — not the model. The telemetry substrate (append-only JSONL) surfaces which enum values cause friction, so you can refine your ontology based on evidence rather than intuition.

---

## Interfaces

**CLI:**
```bash
akf generate "Create a guide on API rate limiting"
akf ask "How do I implement API rate limiting in FastAPI?" --top-k 5
akf ask "How do I implement API rate limiting in FastAPI?" --top-k 5 --no-llm
akf generate "Create Docker security checklist" --model gemini
akf validate ./vault/
akf validate --file outputs/Guide.md
akf serve --port 8000        # REST API
akf serve --mcp              # MCP server (v0.6.x)
```

**Python API:**
```python
from akf import Pipeline

pipeline = Pipeline(output="./vault/")
result = pipeline.generate("Create a guide on Docker networking")
results = pipeline.batch_generate(["Guide 1", "Guide 2", "Guide 3"])
```

**REST API:**
```
POST /v1/generate    →  validated file
POST /v1/ask         →  RAG answer (or retrieval-only with no_llm)
POST /v1/validate    →  schema check result
POST /v1/batch       →  multiple files
GET  /v1/models      →  available providers
```

**MCP** (v0.6.x, in progress):
```bash
akf serve --mcp
# Exposes: akf_generate, akf_validate, akf_enrich, akf_batch
```

---

## RAG Copilot (Phase 1: Indexer)

Phase 1 adds local corpus indexing for semantic search preparation.

Current scope:
- Parse Markdown files from `corpus/` with `python-frontmatter`
- Split content by H2 headers using `MarkdownHeaderTextSplitter`
- Generate embeddings with `sentence-transformers/all-MiniLM-L6-v2`
- Store vectors in local Chroma collection `akf_corpus`

Out of scope (planned for later phases):
- Retriever/query layer
- Dedicated CLI commands
- Claude API integration for Q&A

Install dependencies:

```bash
pip install -e .[rag]
```

Run indexer:

```bash
python rag/indexer.py
```

Optional environment variables:

```bash
export RAG_CORPUS_DIR="corpus"
export RAG_CHROMA_PATH="rag/.chroma"
export RAG_COLLECTION_NAME="akf_corpus"
export RAG_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
export RAG_MARKDOWN_GLOB="*.md"
export RAG_BATCH_SIZE="64"
```

Expected output format:

```text
Indexed files=<N>, chunks=<M>, collection_count=<K>
```

### Phase 2: Retriever (local semantic search)

After indexing, query the local vector store:

```bash
python rag/retriever.py "How do I implement API rate limiting?" --top-k 5
```

Programmatic usage:

```python
from rag.retriever import retrieve

result = retrieve("How do I implement API rate limiting?", top_k=5)
for hit in result.hits:
  print(hit.distance, hit.metadata.get("source"), hit.metadata.get("section"))
```

Current scope for Phase 2:
- Retrieval/query layer over Chroma index
- Returns top-k relevant chunks with metadata and distance

Still out of scope:
- Answer synthesis over retrieved chunks
- Dedicated AKF CLI subcommands for RAG
- Claude API integration for final response generation

### Phase 3: Copilot synthesis (retrieve + answer)

Generate an answer grounded in retrieved chunks:

```bash
python rag/copilot.py "How do I implement API rate limiting in FastAPI?" --top-k 5 --model auto
```

Programmatic usage:

```python
from rag.copilot import answer_question

result = answer_question(
  "How do I implement API rate limiting in FastAPI?",
  top_k=5,
  model="auto",
)
print(result.answer)
print(result.sources)
```

Phase 3 scope:
- Retrieval + synthesis flow
- Grounded answer generated from top-k chunks
- Source list returned with the answer

---

## What Every Committed File Guarantees

- Required fields present: `title`, `type`, `domain`, `level`, `status`, `tags`, `created`, `updated`
- Valid enums: `type`, `level`, `status` from controlled sets
- Domain from your configured taxonomy in `akf.yaml`
- ISO 8601 dates with `created ≤ updated`
- `tags` as array with ≥ 3 items, `title` as string — no type mismatches

No file reaches disk without passing all checks.

---

## Example Output

**Input:**
```
Create a guide on API rate limiting
```

**Output** (`vault/API_Rate_Limiting_Strategy.md`):
```yaml
---
title: "API Rate Limiting Strategy"
type: guide
domain: api-design
level: intermediate
status: active
version: v1.0
tags: [api, rate-limiting, performance, architecture]
related:
  - "[[API Design Principles]]"
  - "[[System Scalability Patterns]]"
created: 2026-03-06
updated: 2026-03-06
---

## Purpose
...
```

---

## Architecture

```
akf/
  pipeline.py          # Pipeline — generate(), validate(), batch_generate()
  validator.py         # Validation Engine — binary VALID/INVALID, E001–E007
  validation_error.py  # ValidationError dataclass
  error_normalizer.py  # Translates errors → LLM retry instructions
  retry_controller.py  # Convergence protection — aborts on identical error hash
  commit_gate.py       # Atomic write — only VALID files reach disk
  telemetry.py         # Append-only JSONL event stream
  config.py            # Loads akf.yaml or bundled defaults
  server.py            # FastAPI REST API
  mcp_server.py        # MCP server (FastMCP)
  market_pipeline.py   # Three-stage market analysis pipeline
  defaults/
    akf.yaml           # Default taxonomy

cli.py                 # Entry point
llm_providers.py       # Claude / Gemini / GPT-4 / Ollama
```

---

## Model Support

| Provider | Key | Notes |
|----------|-----|-------|
| Claude | `ANTHROPIC_API_KEY` | Recommended for complex content |
| Gemini | `GOOGLE_API_KEY` | Fast, cost-effective |
| GPT-4 | `OPENAI_API_KEY` | General purpose |
| Groq | `GROQ_API_KEY` | Free tier, fast |
| Ollama | — | Local, offline, private |

---

## Tests

```bash
pytest --cov=akf --cov-report=term-missing -v
```

560+ tests, 91% coverage, CI green on Python 3.10 / 3.11 / 3.12.

---

## Tooling Policy

- Source of truth for lint/format rules: `pyproject.toml`
- Primary local quality tools: `ruff`, `black`, `mypy`
- Legacy configs `.flake8`, `.pylintrc`, `.pydocstyle` are removed to avoid conflicting rules
- Codecov policy (stabilization): upload on `main` pushes only, non-blocking
- Node 24 GitHub Actions compatibility: self-hosted runners must be `>=2.327.1`

Recommended local checks:

```bash
ruff check .
black --check .
mypy cli.py llm_providers.py exceptions.py logger.py akf/ --ignore-missing-imports
```

---

## Installation

```bash
# PyPI
pip install ai-knowledge-filler

# With MCP support
pip install ai-knowledge-filler[mcp]

# From source
git clone https://github.com/petro-nazarenko/ai-knowledge-filler.git
cd ai-knowledge-filler
pip install -e .
```

Installation policy:

- Canonical dependency declaration path: `pyproject.toml`
- `requirements.txt` is a thin compatibility entrypoint used to install from the locked constraints in `requirements.lock`
- CI and release jobs install with `pip install -c requirements.lock -e ".[all,dev]"`

---

## Documentation

- [Architecture](ARCHITECTURE.md) — module map, data flow, pipeline decisions
- [CLI Reference](docs/cli-reference.md) — all commands, flags, exit codes
- [User Guide](docs/user-guide.md) — installation, configuration, troubleshooting
- [REST API Threat Model](docs/rest-api-threat-model.md) — auth, endpoint exposure, limits, logging/PII
- [Contributing](CONTRIBUTING.md) — dev setup, quality gates, adding providers

---

## License

MIT — free for commercial and personal use.

---

**PyPI:** https://pypi.org/project/ai-knowledge-filler
**Version:** 1.0.0
