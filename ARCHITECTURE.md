---
title: "AKF Architecture"
type: reference
domain: akf-core
level: advanced
status: active
version: v1.0.0
tags: [architecture, pipeline, api, public-api, semver, modules]
related:
  - "docs/cli-reference.md"
  - "docs/user-guide.md"
  - "CONTRIBUTING.md"
created: 2026-02-06
updated: 2026-03-10
---

# AKF Architecture

**ai-knowledge-filler** · v1.0.0 · [CHANGELOG](CHANGELOG.md) · [CONTRIBUTING](CONTRIBUTING.md)

---

## Public API Declaration

This document constitutes the public API declaration required by Semantic Versioning 2.0.0.

The public API of `ai-knowledge-filler` consists of three stable interfaces and two contracts. Breaking changes to any element below require a MAJOR version increment. Additions require a MINOR increment. Bug fixes require a PATCH increment.

---

### Interface 1 — CLI

```
akf generate "<prompt>"           Generate a validated .md file
akf generate "<prompt>" --output  Write to specified path
akf enrich <path>                 Add YAML frontmatter to existing .md files
akf enrich <path> --dry-run       Preview only, no writes
akf enrich <path> --force         Overwrite valid frontmatter
akf validate <file>               Validate a single file
akf validate --path <dir>         Validate all .md files in directory
akf validate <dir> --strict       Validate all .md files; warnings as errors
akf serve --port <n>              Start REST API server
akf init                          Scaffold akf.yaml in working directory
akf models                        List available LLM providers and key status
```

**Breaking changes (require MAJOR):** removing a command, renaming a command, changing the meaning of an existing flag, changing exit codes.

**Non-breaking additions (MINOR):** new commands, new optional flags.

---

### Interface 2 — Python SDK

```python
from akf import Pipeline

# Constructor
pipeline = Pipeline(
    output: str | Path,                   # vault path
    model: str = "auto",                  # LLM provider/model key
    telemetry_path: str | Path | None,    # JSONL event log path
    writer: TelemetryWriter | None = None, # pre-configured telemetry writer
    config: AKFConfig | None = None,      # pre-loaded config (skips get_config())
)

# Methods
pipeline.generate(prompt: str) -> GenerationResult
pipeline.enrich(path: str | Path, force: bool = False) -> EnrichResult
pipeline.enrich_dir(path: str | Path, force: bool = False) -> list[EnrichResult]
pipeline.validate(path: str | Path) -> ValidationResult
pipeline.batch_generate(prompts: list[str]) -> list[GenerationResult]
```

**`GenerationResult`**
```python
@dataclass
class GenerationResult:
    success: bool
    file_path: Path | None
    content: str | None
    errors: list[ValidationError]
    attempts: int
    generation_id: str
```

**`EnrichResult`**
```python
@dataclass
class EnrichResult:
    status: str          # "enriched" | "skipped" | "failed" | "warning"
    file_path: Path
    errors: list[ValidationError]
    attempts: int
    generation_id: str | None
```

**`ValidationResult`**
```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[ValidationError]
```

**Breaking changes (require MAJOR):** removing a method, renaming a method, changing parameter types, removing fields from result dataclasses, changing field semantics.

---

### Interface 3 — REST API

**Base URL:** `http://host:port`

```
GET  /health
     → 200 {"status": "ok"}

POST /v1/generate
     Body: {"prompt": str}
     → 200 {"success": bool, "content": str, "errors": [...], "generation_id": str}
     → 422 validation error
     → 429 rate limit exceeded

POST /v1/enrich
     Body: {"content": str, "force": bool}
     → 200 {"status": str, "content": str, "errors": [...]}

POST /v1/validate
     Body: {"content": str} | {"file_path": str}
     → 200 {"is_valid": bool, "errors": [...]}

POST /v1/batch
     Body: {"prompts": [str, ...]}
     → 200 {"results": [...]}

GET  /v1/models
     → 200 {"providers": [{"name": str, "available": bool}, ...]}

GET  /docs
     → Swagger UI
```

**Auth:** `Authorization: Bearer <AKF_API_KEY>` — required in `AKF_ENV=prod` (startup fails without key). In `AKF_ENV=dev`, auth is optional unless key is set.

**Rate limits:** `POST /v1/generate` 10/min · `POST /v1/validate` 30/min · `POST /v1/batch` 3/min.

**Breaking changes (require MAJOR):** removing an endpoint, renaming a field in request/response, changing HTTP method, changing response status codes for existing conditions, changing auth model from optional to required unconditionally.

---

### Interface 4 — MCP Server (⚠️ Not yet stable)

Started via `akf serve --mcp`. Transport: `stdio` (default) or `streamable-http`.

```python
# Tool signatures (FastMCP)

akf_generate(
    prompt: str,
    output: str = "./vault",
    domain: str | None = None,
    type: str | None = None,
    model: str = "auto",
) -> dict
# Returns: {"success": bool, "file_path": str | None, "attempts": int,
#            "generation_id": str, "errors": [str, ...]}

akf_validate(
    path: str,
    strict: bool = False,
) -> dict
# Single file: {"is_valid": bool, "errors": [str, ...]}
# Directory:   {"total": int, "ok": int, "failed": int, "results": [...]}
# Not found:   {"error": str}

akf_enrich(
    path: str,
    force: bool = False,
    dry_run: bool = False,
    model: str = "auto",
) -> dict
# Returns: {"total": int, "enriched": int, "skipped": int, "failed": int,
#            "results": [{"file": str, "status": str}, ...]}
# Not found: {"error": str}

akf_batch(
    plan: list,
    output: str = "./vault",
    model: str = "auto",
) -> dict
# Returns: {"total": int, "ok": int, "failed": int,
#            "results": [{"prompt": str, "success": bool,
#                         "file_path": str | None, "attempts": int}, ...]}
```

**Status:** In progress — tool signatures may change before declaration as stable. Not subject to semver breaking-change policy until declared stable.

**Install:** `pip install ai-knowledge-filler[mcp]`

---

### Contract 1 — ValidationError

```python
@dataclass
class ValidationError:
    code: str        # E001–E008
    field: str       # YAML field name
    expected: Any    # allowed values or type
    received: Any    # what was found
    severity: str    # "error" | "warning"
```

**Error codes:**

| Code | Field | Meaning |
|------|-------|---------|
| E001 | type / level / status | Invalid enum value |
| E002 | any | Required field missing |
| E003 | created / updated | Date not ISO 8601 |
| E004 | title / tags | Type mismatch |
| E005 | frontmatter | General schema violation |
| E006 | domain | Not in configured taxonomy |
| E007 | created / updated | `created > updated` |
| E008 | related | Typed relationship label not in `relationship_types` |

**Breaking changes (require MAJOR):** removing an E-code, renaming fields in `ValidationError`, changing severity of an existing code (e.g. warning → error for existing users).

**Non-breaking additions (MINOR):** new E-codes, new `severity` value that does not affect existing behavior.

---

### Contract 2 — akf.yaml Configuration Schema

```yaml
schema_version: "1.0.0"        # required
vault_path: "./vault"           # required

taxonomy:
  domain:                       # domain taxonomy
    - ai-system
    - api-design
    # ...

enums:
  type: [concept, guide, ...]   # file type enum
  level: [beginner, ...]        # level enum
  status: [draft, active, ...]  # status enum

relationship_types:             # valid labels for [[Note|type]] syntax
  - implements
  - requires
  - extends
  - references
  - supersedes
  - part-of
```

`schema_version: "1.0.0"` — frozen at this value until a breaking change to the config schema occurs, at which point it increments to `"2.0.0"`.

**Breaking changes (require MAJOR):** renaming a top-level key, removing a key, changing the type of a key, tightening enum sets in a way that invalidates existing configs.

**Non-breaking additions (MINOR):** new optional top-level keys, new enum values.

---

### Contract 3 — Telemetry JSONL Schema (⚠️ Not yet stable)

All events are written to `telemetry/events.jsonl` as newline-delimited JSON. Each line is one event object. The `event_type` field identifies the schema.

**Common fields (all events):**

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | string | Event discriminator (see types below) |
| `event_id` | string (UUID v4) | Unique event identifier |
| `timestamp` | string (ISO 8601 UTC) | Event emission time, e.g. `"2026-03-01T12:00:00.000Z"` |
| `generation_id` | string (UUID v4) | Links events from the same pipeline run |

**`generation_attempt`** — emitted by RetryController after each attempt:

```json
{
  "event_type": "generation_attempt",
  "event_id": "<uuid>",
  "timestamp": "<iso8601>",
  "generation_id": "<uuid>",
  "document_id": "My_Document",
  "schema_version": "1.0.0",
  "attempt": 1,
  "max_attempts": 3,
  "is_final_attempt": false,
  "converged": false,
  "errors": [{"code": "E001", "field": "type", "expected": [...], "received": "...", "severity": "error"}],
  "model": "claude-3-5-sonnet",
  "temperature": 0,
  "top_p": 1,
  "duration_ms": 1200
}
```

**`generation_summary`** — emitted by CommitGate after a session completes:

```json
{
  "event_type": "generation_summary",
  "event_id": "<uuid>",
  "timestamp": "<iso8601>",
  "generation_id": "<uuid>",
  "document_id": "My_Document",
  "schema_version": "1.0.0",
  "total_attempts": 2,
  "converged": true,
  "abort_reason": null,
  "rejected_candidates": ["Technology"],
  "final_domain": "backend-engineering",
  "model": "claude-3-5-sonnet",
  "temperature": 0,
  "total_duration_ms": 3400
}
```

**`enrich`** — emitted by `Pipeline.enrich()` per enriched file:

```json
{
  "event_type": "enrich",
  "event_id": "<uuid>",
  "timestamp": "<iso8601>",
  "generation_id": "<uuid>",
  "file": "vault/My_Note.md",
  "schema_version": "1.0.0",
  "existing_fields": ["title"],
  "generated_fields": ["type", "domain", "level", "status", "tags", "created", "updated"],
  "attempts": 1,
  "converged": true,
  "skipped": false,
  "skip_reason": "",
  "model": "claude-3-5-sonnet",
  "temperature": 0.0
}
```

**`ask_query`** — emitted by `/v1/ask` endpoint:

```json
{
  "event_type": "ask_query",
  "event_id": "<uuid>",
  "timestamp": "<iso8601>",
  "generation_id": "<uuid>",
  "tenant_id": "default",
  "mode": "synthesis",
  "model": "auto",
  "top_k": 5,
  "no_llm": false,
  "max_distance": null,
  "hits_used": 3,
  "insufficient_context": false,
  "duration_ms": 820
}
```

**`market_analysis`** — emitted by `MarketAnalysisPipeline` per stage:

```json
{
  "event_type": "market_analysis",
  "event_id": "<uuid>",
  "timestamp": "<iso8601>",
  "generation_id": "<uuid>",
  "request": "AI knowledge management market...",
  "stage": "market_analysis",
  "success": true,
  "duration_ms": 2100,
  "model": "claude-3-5-sonnet",
  "error": ""
}
```

**Status:** Schema not yet declared stable. Fields may be added or reorganized before `schema_version: "2.0.0"` is declared.

---

## Pipeline Architecture

```
Prompt ──► LLM ──► Validation Engine ──► Error Normalizer ──► Retry Controller ──► Commit Gate ──► File
                          │                      ▲                    │
                        VALID ───────────────────┼────────────────────┘
                        INVALID ─────────────────┘         (max 3 attempts;
                                                            abort on identical
                                                            error hash)
```

### Determinism Boundary

| Component | Deterministic | Role |
|-----------|--------------|------|
| LLM | ❌ | Content generation — only non-deterministic component |
| Validation Engine | ✅ | Binary `VALID` / `INVALID` + typed errors |
| Error Normalizer | ✅ | `ValidationError[]` → LLM repair instructions |
| Retry Controller | ✅ | Convergence protection — abort on identical hash |
| Commit Gate | ✅ | Atomic write — only `VALID` output reaches disk |
| Telemetry Writer | ✅ | Append-only JSONL — observe only, no feedback loop |

---

## Module Map

```
akf/
  pipeline.py          Pipeline class — generate(), enrich(), enrich_dir(), validate(), batch_generate()
  enricher.py          File reader, YAML extractor, merge logic, prompt builder (enrich pipeline)
  validator.py         Validation Engine
  validation_error.py  ValidationError dataclass + E001–E007
  error_normalizer.py  Error → LLM repair instructions
  retry_controller.py  run_retry_loop() — convergence protection
  commit_gate.py       Atomic write
  telemetry.py         TelemetryWriter — append-only JSONL (GenerationAttemptEvent, GenerationSummaryEvent, EnrichEvent, MarketAnalysisEvent, AskQueryEvent)
  config.py            get_config() — loads akf.yaml or defaults
  server.py            FastAPI REST API
  mcp_server.py        MCP server (FastMCP) — akf_generate, akf_validate, akf_enrich, akf_batch
  market_pipeline.py   Three-stage market analysis pipeline (market → competitors → positioning)
  defaults/akf.yaml    Default taxonomy + enums

cli.py                 Entry point
llm_providers.py       Provider router — Claude / Gemini / GPT-4 / Groq / Grok / Ollama
exceptions.py          Typed exception hierarchy
logger.py              Logging factory (human + JSON)

Scripts/
  validate_yaml.py     Standalone YAML frontmatter validator
  analyze_telemetry.py Telemetry aggregation — retry rate, ontology friction

tests/                 799+ tests, 95.9% coverage
.github/workflows/     ci.yml · tests.yml · validate.yml · changelog.yml · release.yml · secret-scan.yml
```

---

## Dependency Injection Convention

All feature modules (`Pipeline`, `MarketAnalysisPipeline`) follow the same
optional-injection pattern for shared infrastructure.  This avoids ad-hoc
singleton access inside method bodies and makes every component independently
testable.

### Rule

Every module that needs config or telemetry **must** accept both as optional
constructor parameters:

```python
class AnyFeatureModule:
    def __init__(
        self,
        ...,
        writer: TelemetryWriter | None = None,   # inject or omit
        config: AKFConfig | None = None,          # inject or omit
    ) -> None:
        self.writer = writer
        self._config = config
```

### Resolution order

| Dependency | Injected? | Fallback |
|------------|-----------|---------|
| `TelemetryWriter` | `writer is not None` → use it | telemetry silently disabled (or `TelemetryWriter(path=self.telemetry_path)` for `Pipeline`) |
| `AKFConfig` | `config is not None` → use it | `get_config()` singleton (loads `akf.yaml` or package defaults) |

### Server wiring

The FastAPI server creates one shared `TelemetryWriter` and injects it into
every pipeline instance at startup:

```python
# akf/server.py
pipeline = Pipeline(
    output=...,
    writer=get_telemetry_writer(),   # ← shared instance
)
```

### Testing

Tests that need to assert telemetry behaviour pass a `MagicMock()` as writer:

```python
writer = MagicMock()
pipeline = Pipeline(writer=writer, verbose=False)
pipeline.enrich(some_file)
writer.write.assert_called_once()
```

Tests that need a custom config pass a pre-built `AKFConfig` directly,
bypassing all file I/O:

```python
cfg = AKFConfig(domains=["test-domain"], enums=..., relationship_types=[])
pipeline = Pipeline(config=cfg, verbose=False)
```

---

## NOT Public API

The following are internal and may change without a MAJOR increment:

- `akf/validator.py` internals — `_validate_*` private methods
- `akf/retry_controller.py` — `_is_identical_error()` hash implementation
- Telemetry JSONL schema — subject to change until `schema_version: "2.0.0"` is declared stable
- `Scripts/` — utility scripts, not part of the versioned API
- `akf/system_prompt.md` — internal LLM instruction set

---

## Known Issues

| ID | Issue | Severity | Status |
|----|-------|----------|--------|
| BUG-1 | `akf generate` from repo directory uses local `akf/` instead of installed package | Medium | Fixed v1.0.0 |
| SEC-M2 | `--output` path traversal not sanitized | Medium | Fixed v0.6.2 |
| SEC-L2 | `akf init --force` no backup before overwrite | Low | Fixed v0.6.2 |
| SEC-L3 | Windows reserved filename check missing | Low | Fixed v1.0.0 |
| COV-1 | `pipeline.py` batch error paths uncovered | Low | Fixed |
| COV-2 | `validator.py` legacy `taxonomy_path` branch | Low | Fixed |
| COV-3 | `mcp_server.py` error paths in MCP tools uncovered | Low | Fixed |
| DOC-1 | MCP server interface not declared in public API docs | Low | Fixed |
| DOC-2 | Telemetry JSONL schema not documented | Low | Fixed |
| SEC-1 | RAG corpus content used in LLM context without sanitization guardrails | Low | Fixed |
