# AI Knowledge Filler

**Validation pipeline that prevents AI-generated files from reaching disk unless they pass schema checks**

[![Tests](https://github.com/petrnzrnk-creator/ai-knowledge-filler/workflows/Tests/badge.svg)](https://github.com/petrnzrnk-creator/ai-knowledge-filler/actions/workflows/tests.yml)
[![Lint](https://github.com/petrnzrnk-creator/ai-knowledge-filler/workflows/Lint/badge.svg)](https://github.com/petrnzrnk-creator/ai-knowledge-filler/actions/workflows/lint.yml)
[![PyPI](https://img.shields.io/pypi/v/ai-knowledge-filler.svg)](https://pypi.org/project/ai-knowledge-filler/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)](https://github.com/petrnzrnk-creator/ai-knowledge-filler/actions/workflows/tests.yml)

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

## Market Analysis Pipeline

Run a three-stage AI research pipeline that produces structured, validated Markdown reports:

```
Market Request → Stage 1: Market Analysis
                         ↓ (context)
               Stage 2: Competitor Comparison
                         ↓ (context)
               Stage 3: Positioning Determination
```

Each stage feeds its output as context into the next. If an earlier stage fails, downstream stages are automatically skipped.

```bash
# Full pipeline (all 3 stages)
akf market-analysis "B2B SaaS project management tools for SMEs"

# Select LLM and output directory
akf market-analysis "EdTech market in Eastern Europe" --model claude --output ./reports/

# Run only the market analysis stage
akf market-analysis "Fintech payments" --stages market
```

**What each stage produces:**

| Stage | Report | Key sections |
|-------|--------|-------------|
| 1 — Market Analysis | `market_analysis_*.md` | Size & CAGR, segments, customer pain points, tech trends, regulatory factors |
| 2 — Competitor Analysis | `market_competitors_*.md` | Key players, SWOT per player, comparison matrix, whitespace / gaps |
| 3 — Positioning | `market_positioning_*.md` | USP, positioning statement, messaging pillars, differentiation, go-to-market |

**Python API:**

```python
from akf.market_pipeline import MarketAnalysisPipeline

pipeline = MarketAnalysisPipeline(output="./reports/", model="claude")
result = pipeline.analyze("B2B SaaS project management tools for SMEs")

for fp in result.files:
    print(fp)  # three validated Markdown files

# Run individual stages
stage1 = pipeline.analyze_market(request)
stage2 = pipeline.analyze_competitors(request, stage1.content)
stage3 = pipeline.determine_positioning(request, stage1.content, stage2.content)
```

Stage 3 requires a concrete market request — it validates that both market and competitor context are present before calling the LLM.

---

## Interfaces

**CLI:**
```bash
akf generate "Create a guide on API rate limiting"
akf generate "Create Docker security checklist" --model gemini
akf market-analysis "B2B SaaS tools for SMEs" --output ./reports/
akf validate ./vault/
akf validate --file outputs/Guide.md
akf serve --port 8000        # REST API
akf serve --mcp              # MCP server (v0.6.x)
```

**Python API:**
```python
from akf import Pipeline
from akf.market_pipeline import MarketAnalysisPipeline

pipeline = Pipeline(output="./vault/")
result = pipeline.generate("Create a guide on Docker networking")
results = pipeline.batch_generate(["Guide 1", "Guide 2", "Guide 3"])
```

**REST API:**
```
POST /v1/generate    →  validated file
POST /v1/validate    →  schema check result
POST /v1/batch       →  multiple files
GET  /v1/models      →  available providers
```

**MCP** (v0.6.x):
```bash
akf serve --mcp
# Exposes: akf_generate, akf_validate, akf_enrich, akf_batch
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
  market_pipeline.py   # MarketAnalysisPipeline — 3-stage market analysis
  validator.py         # Validation Engine — binary VALID/INVALID, E001–E007
  validation_error.py  # ValidationError dataclass
  error_normalizer.py  # Translates errors → LLM retry instructions
  retry_controller.py  # Convergence protection — aborts on identical error hash
  commit_gate.py       # Atomic write — only VALID files reach disk
  telemetry.py         # Append-only JSONL event stream
  config.py            # Loads akf.yaml or bundled defaults
  server.py            # FastAPI REST API
  mcp_server.py        # MCP server (FastMCP)
  defaults/
    akf.yaml           # Default taxonomy

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

560+ tests, 91% coverage, CI green on Python 3.10 / 3.11 / 3.12.

---

## Installation

```bash
# PyPI
pip install ai-knowledge-filler

# With MCP support
pip install ai-knowledge-filler[mcp]

# From source
git clone https://github.com/petrnzrnk-creator/ai-knowledge-filler.git
cd ai-knowledge-filler
pip install -e .
```

---

## Documentation

- [Architecture](ARCHITECTURE.md) — module map, data flow, pipeline decisions
- [CLI Reference](docs/cli-reference.md) — all commands, flags, exit codes
- [User Guide](docs/user-guide.md) — installation, configuration, troubleshooting
- [Contributing](CONTRIBUTING.md) — dev setup, quality gates, adding providers

---

## License

MIT — free for commercial and personal use.

---

**PyPI:** https://pypi.org/project/ai-knowledge-filler
**Version:** 0.7.0
