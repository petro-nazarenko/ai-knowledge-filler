# AI Knowledge Filler

**Validation pipeline for LLM-generated structured Markdown**

[![Tests](https://github.com/petrnzrnk-creator/ai-knowledge-filler/workflows/Tests/badge.svg)](https://github.com/petrnzrnk-creator/ai-knowledge-filler/actions/workflows/tests.yml)
[![Lint](https://github.com/petrnzrnk-creator/ai-knowledge-filler/workflows/Lint/badge.svg)](https://github.com/petrnzrnk-creator/ai-knowledge-filler/actions/workflows/lint.yml)
[![Validate](https://github.com/petrnzrnk-creator/ai-knowledge-filler/workflows/Validate%20Metadata/badge.svg)](https://github.com/petrnzrnk-creator/ai-knowledge-filler/actions/workflows/validate.yml)
[![PyPI](https://img.shields.io/pypi/v/ai-knowledge-filler.svg)](https://pypi.org/project/ai-knowledge-filler/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-91.50%25-brightgreen.svg)](https://github.com/petrnzrnk-creator/ai-knowledge-filler/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## The Problem

LLMs generate text. You need structured, schema-compliant files.

Without a validation layer, AI-generated Markdown produces:

| Error | Raw LLM output | What you need |
|-------|---------------|---------------|
| Enum violation | `level: expert` | `beginner \| intermediate \| advanced` |
| Domain violation | `domain: Technology` | `domain: system-design` |
| Type mismatch | `tags: security` | `tags: [security, api, auth]` |
| Date format | `created: 12-02-2026` | `created: 2026-02-12` |

One file? Fixable manually. A hundred files? The schema collapses.

**AKF enforces the contract at generation time, not review time.**

---

## How It Works

```
Prompt
  → LLM                  (only non-deterministic component)
  → Validation Engine    (binary: VALID or INVALID + typed E-codes)
  → Error Normalizer     (deterministic repair instructions from E-codes)
  → Retry Controller     (max 3 attempts — aborts on identical failure hash)
  → Commit Gate          (atomic write — only VALID output reaches disk)
```

No silent failures. No partial commits. No guessing.

**Retry = ontology signal.** When a domain triggers elevated retries, the taxonomy has a boundary problem — not the model. Telemetry captures this.

---

## Quick Start

```bash
pip install ai-knowledge-filler

export GROQ_API_KEY="gsk_..."   # free tier, fastest

# Generate new file
akf generate "Create a Docker networking guide"
# → Docker_Networking_Guide.md (validated, schema-compliant)

# Enrich existing files — add YAML to files that have none
akf enrich docs/

# Validate an entire directory
akf validate --path docs/
```

---

## AKF Documents Itself

This repo uses AKF to validate its own documentation on every PR.

**Setup:**
```bash
# 1. Define your taxonomy
cat akf.yaml
```
```yaml
schema_version: "1.0.0"
vault_path: "./docs"
taxonomy:
  domains:
    - akf-core
    - akf-docs
    - akf-ops
    - akf-spec
```

```bash
# 2. Enrich existing docs — AKF adds frontmatter via LLM
akf enrich docs/ --model groq

# 3. Validate
akf validate --path docs/
# ✅ docs/cli-reference.md
# ✅ docs/user-guide.md
# → Total: 2 | OK: 2 | Errors: 0
```

**CI gate (`.github/workflows/validate.yml`):**
```yaml
- name: Validate docs/
  run: akf validate --path docs/
```

Every PR that introduces invalid metadata fails the check. The **Validate** badge above is AKF validating AKF's own docs.

---

## `akf enrich`

Add YAML frontmatter to existing Markdown files — bulk or single.

```bash
akf enrich docs/                    # enrich all .md files
akf enrich docs/ --dry-run          # preview only, no writes
akf enrich docs/ --force            # overwrite valid frontmatter
akf enrich docs/ --output enriched/ # copy to output dir
```

| File state | Default | `--force` |
|------------|---------|-----------|
| No frontmatter | Generate + validate + write | Same |
| Incomplete frontmatter | Fill missing fields only | Regenerate all |
| Valid frontmatter | Skip | Regenerate all |
| Empty file | Skip with warning | Skip |

Enrich runs through the same validation pipeline as `generate` — retry loop, commit gate, telemetry.

---

## Python API

```python
from akf import Pipeline

pipeline = Pipeline(output="./vault/", model="groq")

# Generate new file
result = pipeline.generate("Create API rate limiting guide")
print(result.success)        # True
print(result.path)           # PosixPath('vault/API_Rate_Limiting_Guide.md')
print(result.attempts)       # 1 (retried if schema violation)

# Enrich existing file
result = pipeline.enrich("docs/old-note.md")
print(result.status)         # "enriched" | "skipped" | "failed"

# Enrich directory
results = pipeline.enrich_dir("docs/")

# Batch generate
results = pipeline.batch_generate([
    "Docker deployment best practices",
    "Kubernetes security hardening",
    "API authentication strategies",
])

# Validate
v = pipeline.validate("vault/my_file.md")
print(v.valid, v.errors)
```

---

## REST API

```bash
akf serve --port 8000

curl -X POST http://localhost:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create Docker security checklist", "model": "groq"}'

curl -X POST http://localhost:8000/v1/batch \
  -H "Content-Type: application/json" \
  -d '{"prompts": ["Docker guide", "Kubernetes guide"]}'

curl -X POST http://localhost:8000/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"content": "---\ntitle: Test\n..."}'
```

Endpoints: `POST /v1/generate` · `POST /v1/enrich` · `POST /v1/validate` · `POST /v1/batch` · `GET /v1/models` · `GET /health`

Swagger UI: `http://localhost:8000/docs`

---

## MCP Server

AKF exposes four MCP tools for Claude Desktop, Cursor, Zed, and any other MCP-compatible client.

```bash
pip install 'ai-knowledge-filler[mcp]'

# stdio — local clients (Claude Desktop, Cursor, Zed)
akf serve --mcp

# streamable-http — remote / web deployments
akf serve --mcp --transport streamable-http
```

**Claude Desktop** (`claude_desktop_config.json`):
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

**Available tools:** `akf_generate` · `akf_validate` · `akf_enrich` · `akf_batch`

All four tools run through the same validation pipeline as the CLI — retry loop, commit gate, telemetry.

---

- Required fields: `title`, `type`, `domain`, `level`, `status`, `tags`, `created`, `updated`
- Valid enums: `type`, `level`, `status` from controlled sets
- Domain from configured taxonomy (`akf.yaml`) — not hardcoded
- ISO 8601 dates with `created ≤ updated`
- `tags` as array (≥3), `title` as string

### Error Codes

| Code | Field | Meaning |
|------|-------|---------|
| E001 | type / level / status | Invalid enum value |
| E002 | any | Required field missing |
| E003 | created / updated | Date not ISO 8601 |
| E004 | title / tags | Type mismatch |
| E005 | frontmatter | General schema violation |
| E006 | domain | Not in taxonomy |
| E007 | created / updated | `created > updated` |

---

## Configuration

```yaml
# akf.yaml
schema_version: "1.0.0"
vault_path: "./vault"

taxonomy:
  domains:
    - ai-system
    - api-design
    - devops
    - security
    - system-design
    # add your own

enums:
  type: [concept, guide, reference, checklist, project, roadmap, template, audit]
  level: [beginner, intermediate, advanced]
  status: [draft, active, completed, archived]
```

```bash
akf init          # creates akf.yaml in current directory
akf init --force  # overwrite existing
```

---

## CLI Reference

```bash
# Generate
akf generate "prompt" [--model groq|claude|gemini|gpt4|ollama] [--output PATH]

# Enrich
akf enrich PATH [--dry-run] [--force] [--model MODEL] [--output DIR]

# Validate
akf validate [--file FILE] [--path PATH] [--strict]

# Server
akf serve [--host HOST] [--port PORT]
akf serve --mcp [--transport stdio|streamable-http]

# Models / Init
akf models
akf init [--path DIR] [--force]
```

---

## Model Selection

| Model | Key | Speed | Cost | Notes |
|-------|-----|-------|------|-------|
| **Groq** | `GROQ_API_KEY` | ⚡ | Free tier | Recommended for CI, high volume |
| **Claude** | `ANTHROPIC_API_KEY` | Medium | $$$ | Technical docs, architecture |
| **Gemini** | `GOOGLE_API_KEY` | Fast | $ | Quick drafts |
| **GPT-4** | `OPENAI_API_KEY` | Medium | $$ | General purpose |
| **Grok** | `XAI_API_KEY` | Fast | $$ | General purpose |
| **Ollama** | — | Fast | Free | Local / offline / private |

Auto-selection order: Groq → Grok → Claude → Gemini → GPT-4 → Ollama.

---

## Telemetry

Each generation appends a structured event to `telemetry/events.jsonl`:

```json
{
  "generation_id": "uuid-v4",
  "document_id": "abc123",
  "schema_version": "1.0.0",
  "attempt": 1,
  "converged": true,
  "timestamp": "2026-02-27T14:22:01Z",
  "model": "groq",
  "temperature": 0
}
```

Append-only. Never influences the pipeline at runtime.

---

## Security

```bash
export AKF_API_KEY="your-secret"          # optional — unset = dev mode
export AKF_CORS_ORIGINS="https://app.com"
```

Rate limits: `POST /v1/generate` 10/min · `POST /v1/validate` 30/min · `POST /v1/batch` 3/min

---

## Quality

- **563 tests**, 91.50% coverage
- CI green on Python 3.10 / 3.11 / 3.12
- Type hints: 100%
- Pylint: 9.55/10

---

## Roadmap

### Shipped
- [x] `akf generate`, `akf enrich`, `akf validate`, `akf serve`, `akf init`
- [x] Validation pipeline — E001–E007, retry loop, commit gate
- [x] Telemetry — append-only JSONL, ontology friction metrics
- [x] Config layer — external `akf.yaml`, no code changes for taxonomy
- [x] Pipeline API — `from akf import Pipeline`
- [x] REST API — FastAPI, rate limiting, optional auth
- [x] Self-documentation — AKF validates its own `docs/` on every PR
- [x] `akf generate --batch plan.json` — batch generation from JSON plan
- [x] MCP server — `akf serve --mcp`, 4 tools, stdio + streamable-http

### Planned
- [ ] Layered `akf.yaml` with `extends:` (ADR-002)
- [ ] Graph extraction layer
- [ ] n8n / Make integration templates

---

## Documentation

- [Architecture](ARCHITECTURE.md) — Module map, data flow, extension points
- [CLI Reference](docs/cli-reference.md) — All commands, flags, env vars, exit codes
- [User Guide](docs/user-guide.md) — Quickstart, enrich workflow, CI integration
- [Contributing](CONTRIBUTING.md) — Dev setup, adding providers

---

## License

MIT — Free for commercial and personal use.

---

**PyPI:** https://pypi.org/project/ai-knowledge-filler/ | **Version:** 0.6.1
