# CLAUDE.md — AI Assistant Guide for ai-knowledge-filler

This file provides context for AI assistants (Claude, Copilot, etc.) working on
this repository. Read this before making any code changes.

---

## Project Overview

**ai-knowledge-filler** (`akf`) is a validation pipeline (v1.0.0) that prevents
AI-generated Markdown knowledge files from reaching disk unless they pass schema
checks. It interjects a deterministic validation layer between LLM output and the
filesystem.

**Core architecture:**

```
Prompt → LLM → Validation Engine → Error Normalizer → Retry Controller → Commit Gate → File
```

- External taxonomy lives in `akf.yaml` (not in code)
- Typed error codes: E001–E007
- Automatic retry with convergence protection (max 3 attempts)
- Telemetry in append-only JSONL (`telemetry/events.jsonl`)

**Interfaces:** CLI (`akf`), Python SDK (`akf.pipeline.Pipeline`), REST API (FastAPI), MCP server

---

## Repository Layout

```
ai-knowledge-filler/
├── cli.py                    # CLI entry point — all `akf` commands
├── llm_providers.py          # LLM provider abstraction (Claude, Gemini, GPT-4, Groq, Ollama)
├── exceptions.py             # Top-level exception types
├── logger.py                 # Logging setup
├── akf/                      # Core library package
│   ├── pipeline.py           # High-level Pipeline class (generate, validate, enrich, batch)
│   ├── validator.py          # Validation engine — E001–E007 checks
│   ├── config.py             # Config loader (akf.yaml, env var, package defaults)
│   ├── error_normalizer.py   # Errors → structured retry payload (pure function)
│   ├── retry_controller.py   # Retry loop with convergence protection
│   ├── commit_gate.py        # Atomic write gate (only valid docs reach disk)
│   ├── telemetry.py          # Append-only JSONL telemetry writer
│   ├── enricher.py           # Add frontmatter to existing Markdown files
│   ├── market_pipeline.py    # Three-stage market analysis pipeline
│   ├── mcp_server.py         # MCP server (Model Context Protocol)
│   ├── server.py             # FastAPI REST server
│   ├── validation_error.py   # ValidationError dataclass, ErrorCode/Severity enums
│   ├── system_prompt.md      # LLM system prompt (loaded at runtime)
│   └── defaults/akf.yaml     # Bundled default taxonomy config
├── tests/
│   ├── unit/                 # Unit tests per module
│   ├── integration/          # Integration tests (API, CLI, file ops)
│   └── test_*.py             # Module-level tests at root
├── docs/                     # Project documentation
├── examples/                 # Example akf.yaml configurations
├── Scripts/                  # Developer utility scripts
├── .github/workflows/        # CI/CD pipelines
├── akf.yaml                  # Repository's own taxonomy config
├── pyproject.toml            # Package metadata and tooling config
├── pytest.ini                # Test runner config
├── mypy.ini                  # Type checker config
├── .flake8                   # Linter config
└── .pylintrc                 # Pylint config
```

---

## Development Setup

```bash
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -e ".[all]"             # Install all extras (server, mcp, all providers)
# or minimal:
pip install -e ".[anthropic]"       # Claude only
```

**Required env vars** (copy to `.env`, not committed):

```bash
ANTHROPIC_API_KEY=...     # Claude (recommended)
GOOGLE_API_KEY=...        # Gemini
OPENAI_API_KEY=...        # GPT-4
GROQ_API_KEY=...          # Groq (free tier)
```

**Optional configuration env vars:**

```bash
AKF_CONFIG_PATH=./akf.yaml          # Override config location
AKF_OUTPUT_DIR=.                    # Default output directory
AKF_TELEMETRY_PATH=./telemetry/events.jsonl
AKF_API_KEY=...                     # Bearer token for REST API
AKF_CORS_ORIGINS=http://localhost:3000
```

---

## Running Tests

```bash
# All tests with coverage
pytest --cov=akf --cov-report=term-missing -v

# Unit tests only
pytest tests/unit/ -v -m unit

# Integration tests only
pytest tests/integration/ -v -m integration

# Skip slow tests
pytest -m "not slow"

# Single file
pytest tests/test_validator.py -v
```

**Coverage requirements:**
- CI enforces: ≥ 75% (`tests.yml`)
- Contributors must maintain: ≥ 91% (`CONTRIBUTING.md`)
- Local fail threshold: 60% (`pytest.ini`)

---

## Code Quality Gates

All must pass before merging:

```bash
black --check --line-length 100 .   # Formatting check
black --line-length 100 .           # Auto-format
flake8 --max-line-length 120 .      # Linting
pylint akf/ cli.py                  # Pylint score >= 9.0
mypy akf/ cli.py                    # Type checking
akf validate --path docs/           # Validate docs frontmatter
```

**Config summary:**
- Black: 100-char lines, targets Python 3.11
- Flake8: 120-char lines, cyclomatic complexity ≤ 10; ignores E203, W503, E501, E402
- Pylint: max-complexity 10
- Mypy: strict mode configured in `mypy.ini`

---

## Key Conventions

### Error Codes (E001–E007)

| Code | Name | Severity | Description |
|------|------|----------|-------------|
| E001 | INVALID_ENUM | ERROR | Invalid value for type/level/status |
| E002 | MISSING_FIELD | ERROR | Required field absent |
| E003 | INVALID_DATE_FORMAT | ERROR | Not ISO 8601 (YYYY-MM-DD) |
| E004 | TYPE_MISMATCH | ERROR | tags is string instead of array |
| E005 | SCHEMA_VIOLATION | ERROR | General schema violation |
| E006 | TAXONOMY_VIOLATION | ERROR | Domain not in akf.yaml |
| E007 | DATE_SEQUENCE | WARNING | created > updated |

Severity `ERROR` blocks commit; `WARNING` is logged only.

### Required Frontmatter Fields

Every Markdown file processed by `akf` must have:
```yaml
---
title: string
type: concept | guide | reference | checklist | project | roadmap | template | audit
domain: <one of the domains in akf.yaml>
level: beginner | intermediate | advanced
status: draft | active | completed | archived
tags: [array, of, at, least, three, items]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

### Determinism Boundary

These components are **pure functions** — same input must always produce same output:
- `akf/validator.py`: `validate()`
- `akf/error_normalizer.py`: `normalize_errors()`
- `akf/retry_controller.py`: `run_retry_loop()`
- `akf/commit_gate.py`: `commit()`
- `akf/telemetry.py`: `TelemetryWriter` (append-only, thread-safe)

Only `llm_providers.py` is non-deterministic (the LLM call itself).

Do not add side effects, randomness, or I/O to the deterministic components.

### Config Loading Order

`akf/config.py` searches in this order:
1. `AKF_CONFIG_PATH` environment variable
2. `./akf.yaml` in current working directory
3. Package defaults at `akf/defaults/akf.yaml`

### Retry Convergence Protection

`retry_controller.py` aborts the retry loop if:
- The same error hash appears twice (identical error, same field)
- MAX_ATTEMPTS (3) is reached

Do not change `MAX_ATTEMPTS` without updating tests and the retry contract.

### Security Rules

- **SEC-M2**: `sanitize_filename()` in `cli.py` prevents path traversal — never bypass
- **SEC-L3**: Windows reserved filename blocking in `sanitize_filename()` — keep intact
- **SEC-L2**: `akf.yaml` backed up before `--force` overwrite in `akf init`
- Never write files outside the designated output directory
- `AKF_API_KEY` bearer token is optional but must be validated if set

---

## Module Reference

### `akf/pipeline.py` — Primary SDK Interface

```python
from akf.pipeline import Pipeline

p = Pipeline(model="claude-opus-4-6", config_path="./akf.yaml")

result = p.generate(prompt, output="path/to/file.md")
# result.success, result.content, result.file_path, result.attempts,
# result.errors, result.generation_id, result.duration_ms

result = p.validate(path)
# result.valid, result.errors, result.warnings, result.filepath

result = p.enrich(path, force=False)
# result.success, result.path, result.status, result.attempts, result.generation_id

results = p.batch_generate(prompts)  # list[GenerateResult]
```

### `akf/validator.py` — Validation Engine

```python
from akf.validator import validate

errors = validate(document_str, taxonomy_path="./akf.yaml")
# Returns list[ValidationError]; empty list = valid
```

### `akf/error_normalizer.py` — Error → Retry Payload

```python
from akf.error_normalizer import normalize_errors

payload = normalize_errors(errors)
prompt_text = payload.to_prompt_text()  # Inject into LLM retry prompt
```

### `akf/validation_error.py` — Error Types

```python
from akf.validation_error import ValidationError, ErrorCode, Severity

# Helper constructors:
ValidationError.missing_field("title")
ValidationError.invalid_enum("type", ["concept", "guide"], "unknown")
ValidationError.invalid_date_format("created", "not-a-date")
ValidationError.type_mismatch("tags", "array", "string")
```

### `akf/commit_gate.py` — Atomic Write Gate

```python
from akf.commit_gate import commit

result = commit(document, output_path, errors, schema_version="1.0.0")
# result.committed (bool), result.path, result.blocking_errors
```

---

## CLI Commands

```bash
akf validate <path>             # Validate file or directory
akf generate "<prompt>"         # Generate one file from prompt
akf batch <plan.json>           # Batch generation from JSON plan
akf enrich <path>               # Add frontmatter to existing Markdown
akf init                        # Scaffold akf.yaml in current dir
akf serve                       # Start REST API server
akf models                      # List available LLM providers
akf market "<request>"          # Three-stage market analysis
```

Common flags: `--model`, `--output`, `--config`, `--dry-run`, `--force`, `--verbose`

---

## REST API Endpoints

Base URL when running `akf serve` (default port 8000):

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /v1/generate | Generate one file |
| POST | /v1/enrich | Enrich existing file |
| POST | /v1/validate | Validate a document |
| POST | /v1/batch | Batch generation |
| GET | /v1/models | List providers |
| GET | /docs | Swagger UI |

Auth: `Authorization: Bearer <AKF_API_KEY>` (if env var is set)
Rate limit: 60 requests/minute (configurable)

---

## Testing Conventions

- Unit tests live in `tests/unit/` or `tests/test_<module>.py`
- Integration tests live in `tests/integration/`
- Use `pytest-mock` (`mocker` fixture) for mocking LLM calls — never make real API calls in tests
- Mark tests: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Fixture sharing via `tests/conftest.py`
- Test files named `test_<module>.py` matching the module they cover

**When adding a new module:**
1. Create `tests/test_<module>.py` with at least unit tests for every public function
2. Mock all external I/O (LLM calls, file writes, network)
3. Test both the happy path and each error code the module can raise
4. Maintain ≥ 91% coverage on the `akf/` package

---

## Branching & Commit Conventions

**Branch naming:** `claude/<description>-<session-id>`, `feature/<ticket>-<description>`

**Commit message format** (from `.gitmessage`):
```
<type>: <short imperative summary>

[optional body explaining why, not what]
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `security`

Examples:
```
feat: add three-stage market analysis pipeline
fix: SEC-L3 block Windows reserved filenames in sanitize_filename
test: add convergence protection cases for retry_controller
```

**PR process:** All changes go through PRs; never push directly to `main`.

---

## Known Issues (from ARCHITECTURE.md)

| ID | Description | Status |
|----|-------------|--------|
| BUG-1 | Enricher overwrote created date on re-enrich | Fixed in v1.0.0 |
| SEC-M2 | Path traversal via crafted filename | Fixed in v0.6.1 |
| SEC-L2 | akf.yaml overwrite without backup | Fixed in v0.6.2 |
| SEC-L3 | Windows reserved filenames not blocked | Fixed in v1.0.0 |
| COV-1 | mcp_server.py below 91% coverage | Open |
| COV-2 | market_pipeline.py error paths undertested | Open |

---

## LLM Provider Notes

Recommended model for generation: `claude-opus-4-6` (or `claude-sonnet-4-6` for speed).

Provider selection priority when multiple keys are available:
1. Explicit `--model` flag
2. Environment variable presence (ANTHROPIC > GOOGLE > OPENAI > GROQ)
3. Ollama (local, no key needed)

Retry config in `llm_providers.py`: `DEFAULT_MAX_RETRIES=3`, exponential backoff (1s, 2s, 4s).

**Fatal signals** (do not retry): 401, 403, invalid API key, 404
**Retryable signals**: timeout, rate limit, 429, 503, 502, connection error

---

## Telemetry

Events are written to `telemetry/events.jsonl` (append-only, 10MB rotation).

Two event types:
- `GenerationAttemptEvent`: One per retry attempt, shares `generation_id`
- `GenerationSummaryEvent`: Final outcome of a generation session

Telemetry is **optional** — pipeline works if writer is `None`. Do not make telemetry
writes block the main pipeline path.

---

## Changelog & Releases

- Changelog managed by `git-cliff` (`cliff.toml`)
- Releases tagged as `v<major>.<minor>.<patch>` trigger the `release.yml` workflow
- Workflow builds the package and publishes to PyPI via OIDC (no stored token)
- Always update `CHANGELOG.md` before tagging a release
