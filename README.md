# AI Knowledge Filler

**AI-powered content production system for structured Markdown — generate, validate, and commit schema-correct files at scale.**

[![CI](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/ci.yml/badge.svg)](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/ci.yml)
[![Tests](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/tests.yml/badge.svg)](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/tests.yml)
[![PyPI](https://img.shields.io/pypi/v/ai-knowledge-filler.svg)](https://pypi.org/project/ai-knowledge-filler/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen.svg)](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/tests.yml)

---

## The Problem

LLM output drifts. Wrong enum values, missing required fields, dates in the wrong format, `tags: "security"` instead of `tags: [security]`. The files look fine until something downstream breaks: a Dataview query returning nothing, a CI check failing, a search index corrupting.

Structured prompts reduce first-pass errors. They don't prevent them — model updates, provider switches, and schema edge cases still produce invalid output. **Upstream reduces errors. Downstream guarantees correctness.**

AKF is the production system that closes that gap.

---

## How It Works

```
Prompt → LLM → Validation Engine → Error Normalizer → Retry Controller → Commit Gate → File
```

The LLM is the only non-deterministic component. Everything else is pure functions.

If output fails schema checks, **it never touches disk** — the Error Normalizer converts typed error codes into deterministic correction instructions and sends them back to the LLM.

If the same error fires twice on the same field, the pipeline **aborts instead of looping** — identical failure on the same field means your taxonomy has a boundary problem, not the model. More retries won't fix it.

---

## Quick Start

```bash
pip install ai-knowledge-filler

export ANTHROPIC_API_KEY="sk-ant-..."  # or GOOGLE_API_KEY, OPENAI_API_KEY, GROQ_API_KEY

akf generate "Write a guide on Docker networking"
akf validate ./vault/
```

Works with Claude, GPT-4, Gemini, Groq, Ollama.

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

The Error Normalizer translates these into deterministic correction instructions for the retry:

```
E006 on field "domain" (received: "backend")
→ "The 'domain' field must be one of: [api-design, devops, security, ...]
   You used 'backend' which is not in the taxonomy. Choose the closest match."
```

---

## Retry Pressure as Ontology Signal

When the same domain value triggers elevated retries across multiple generation runs, the taxonomy has a **boundary problem** — the model is consistently trying to say something your schema doesn't have a slot for.

The telemetry substrate (append-only JSONL) records which fields cause friction. This turns retry pressure from a failure metric into a schema health signal: evidence for refining your ontology rather than tuning your prompt.

---

## Interfaces

**CLI:**
```bash
akf generate "Create a guide on API rate limiting"
akf generate "Create Docker security checklist" --model gemini
akf ask "How do I implement API rate limiting in FastAPI?" --top-k 5
akf ask "How do I implement API rate limiting in FastAPI?" --top-k 5 --no-llm
akf validate ./vault/
akf validate --file outputs/Guide.md
akf serve --port 8000        # REST API
akf serve --mcp              # MCP server
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
POST /v1/enrich      →  add frontmatter to existing file
POST /v1/ask         →  RAG answer (or retrieval-only with no_llm)
POST /v1/validate    →  schema check result
POST /v1/batch       →  multiple files
GET  /v1/models      →  available providers
```

**MCP** (`pip install ai-knowledge-filler[mcp]`):
```bash
akf serve --mcp
# Tools: akf_generate, akf_validate, akf_enrich, akf_batch
```

Claude Desktop config (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "akf": {
      "command": "akf",
      "args": ["serve", "--mcp"]
    }
  }
}
```

---

## What Every Committed File Guarantees

- Required fields present: `title`, `type`, `domain`, `level`, `status`, `tags`, `created`, `updated`
- Valid enums: `type`, `level`, `status` from controlled sets
- Domain from your configured taxonomy in `akf.yaml`
- ISO 8601 dates with `created ≤ updated`
- `tags` as array with ≥ 3 items, `title` as string — no type mismatches

No file reaches disk without passing all checks.

---

## CI Integration

```yaml
# .github/workflows/validate.yml
- name: Validate docs/
  run: akf validate --path docs/
```

Exit code `1` on any schema error — fails the PR automatically.

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
  validator.py         # Validation Engine — binary VALID/INVALID, E001–E008
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

rag/
  indexer.py           # Corpus indexer (akf index)
  retriever.py         # Semantic search layer
  copilot.py           # Retrieval + synthesis (akf ask)

cli.py                 # Entry point
llm_providers.py       # Claude / Gemini / GPT-4 / Groq / Ollama
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

715 tests, 92% coverage, CI green on Python 3.10 / 3.11 / 3.12.

---

## Installation

```bash
pip install ai-knowledge-filler

# With MCP support
pip install ai-knowledge-filler[mcp]

# With RAG support
pip install ai-knowledge-filler[rag]

# From source
git clone https://github.com/petro-nazarenko/ai-knowledge-filler.git
cd ai-knowledge-filler
pip install -e .
```

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
**Version:** 1.0.1
