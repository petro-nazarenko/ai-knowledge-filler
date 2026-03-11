# AI Knowledge Filler — Wiki

**Validation pipeline that prevents AI-generated files from reaching disk unless they pass schema checks.**

[![PyPI](https://img.shields.io/pypi/v/ai-knowledge-filler.svg)](https://pypi.org/project/ai-knowledge-filler/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen.svg)](https://github.com/petro-nazarenko/ai-knowledge-filler/actions/workflows/tests.yml)

---

## What is AI Knowledge Filler?

AI Knowledge Filler (AKF) solves a fundamental problem with LLM-generated structured content: **output drift**. Every time you use an LLM to generate structured knowledge files, the output drifts — wrong enum values, missing fields, dates in the wrong format, tags as strings instead of arrays.

AKF intercepts validation failures **before** they touch disk. The pipeline converts typed error codes into deterministic repair instructions and sends them back to the LLM for retry. If the same error fires twice on the same field, the pipeline aborts — that pattern signals a schema boundary problem, not a model failure.

### Pipeline Flow

```
Prompt → LLM → Validation Engine → Error Normalizer → Retry Controller → Commit Gate → File
```

The LLM is the only non-deterministic component. Everything else is pure functions.

---

## Quick Start

```bash
pip install ai-knowledge-filler
export ANTHROPIC_API_KEY="sk-ant-..."  # or GOOGLE_API_KEY, OPENAI_API_KEY, GROQ_API_KEY
akf generate "Write a guide on Docker networking"
akf validate ./vault/
```

### Quickstart by Interface

```bash
# CLI
akf init
akf generate "Create a guide on API rate limiting"
akf validate --path ./docs
```

```python
# Python API
from akf import Pipeline

pipeline = Pipeline(output="./output")
result = pipeline.generate("Create a guide on API rate limiting")
print(result.success, result.file_path)
```

```bash
# REST API
akf serve --port 8000
curl -X POST http://127.0.0.1:8000/v1/generate \
	-H "Content-Type: application/json" \
	-d '{"prompt":"Create a guide on API rate limiting"}'
```

Minimal examples are in:
- `examples/cli_quickstart.sh`
- `examples/python_api_quickstart.py`
- `examples/rest_api_quickstart.sh`

---

## Wiki Pages

| Page | Description |
|------|-------------|
| [Installation](Installation) | Install AKF, set up API keys, verify setup |
| [Configuration](Configuration) | `akf.yaml` schema, taxonomy, enums, options |
| [CLI Reference](CLI-Reference) | All commands, flags, environment variables, exit codes |
| [Python API](Python-API) | Python SDK — `Pipeline` class, methods, result types |
| [REST API](REST-API) | HTTP endpoints, request/response schemas, auth, rate limits |
| [REST API Threat Model](REST-API-Threat-Model) | Public/internal endpoints, auth, limits, logging, PII |
| [MCP Server](MCP-Server) | Model Context Protocol server for Claude Desktop, Cursor, Zed |
| [Error Codes](Error-Codes) | E001–E008 error codes, meanings, and repair instructions |
| [Architecture](Architecture) | Pipeline architecture, module map, determinism boundary |
| [Contributing](Contributing) | Dev setup, quality gates, adding providers, PR process |
| [FAQ](FAQ) | Frequently asked questions and troubleshooting |

---

## Key Features

- **Typed error codes (E001–E008)** instead of free-form messages — each code maps to a deterministic repair instruction
- **Convergence protection** — aborts on identical error hash, preventing infinite retry loops
- **External taxonomy** in `akf.yaml` — change your ontology without touching code or redeploying
- **Multi-LLM support** — Claude, GPT-4, Gemini, Groq, Ollama
- **Four interfaces** — CLI, Python SDK, REST API, MCP Server
- **560+ tests, 91% coverage**, CI green on Python 3.10 / 3.11 / 3.12

---

## What Every Committed File Guarantees

- Required fields present: `title`, `type`, `domain`, `level`, `status`, `tags`, `created`, `updated`
- Valid enums: `type`, `level`, `status` from controlled sets
- `domain` from your configured taxonomy in `akf.yaml`
- ISO 8601 dates with `created ≤ updated`
- `tags` as array with ≥ 3 items, `title` as string — no type mismatches

No file reaches disk without passing all checks.

---

## Model Support

| Provider | Environment Variable | Notes |
|----------|---------------------|-------|
| Claude | `ANTHROPIC_API_KEY` | Recommended for complex content |
| Gemini | `GOOGLE_API_KEY` | Fast, cost-effective |
| GPT-4 | `OPENAI_API_KEY` | General purpose |
| Groq | `GROQ_API_KEY` | Free tier, fast |
| Grok (xAI) | `XAI_API_KEY` | xAI Grok |
| Ollama | — | Local, offline, private |

**Auto-selection order:** `groq → grok → claude → gemini → gpt4 → ollama`

---

## Links

- **Repository:** https://github.com/petro-nazarenko/ai-knowledge-filler
- **PyPI:** https://pypi.org/project/ai-knowledge-filler
- **Issues:** https://github.com/petro-nazarenko/ai-knowledge-filler/issues
- **License:** MIT

---

## CI and Coverage Policy

- Codecov upload runs on `push` to `main` only and is non-blocking during stabilization.
- Blocking coverage gate for PRs is enforced by `pytest --cov-fail-under=...` in CI.
- GitHub Actions workflow stack uses Node 24-compatible action majors.
- Self-hosted runners must be `>=2.327.1` (and `>=2.329.0` for container-action credential persistence scenarios).
