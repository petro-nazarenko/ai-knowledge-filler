# Architecture

This page describes the internal architecture of AI Knowledge Filler: the pipeline flow, module map, determinism boundary, and design decisions.

---

## Pipeline Flow

```
Prompt ──► LLM ──► Validation Engine ──► Error Normalizer ──► Retry Controller ──► Commit Gate ──► File
                          │                      ▲                    │
                        VALID ───────────────────┼────────────────────┘
                        INVALID ─────────────────┘         (max 3 attempts;
                                                            abort on identical
                                                            error hash)
```

The LLM is the only non-deterministic component. Everything else is a pure function.

If output fails schema checks, it **never touches disk** — the Error Normalizer converts typed error codes into correction instructions and sends them back to the LLM for retry.

If the same error fires twice on the same field, the pipeline **aborts instead of looping** — this pattern indicates a schema boundary problem, not a model failure.

---

## Determinism Boundary

| Component | Deterministic | Role |
|-----------|--------------|------|
| LLM | ❌ | Content generation — only non-deterministic component |
| Validation Engine | ✅ | Binary `VALID` / `INVALID` + typed E001–E008 errors |
| Error Normalizer | ✅ | `ValidationError[]` → deterministic LLM repair instructions |
| Retry Controller | ✅ | Convergence protection — abort on identical error hash |
| Commit Gate | ✅ | Atomic write — only `VALID` output reaches disk |
| Telemetry Writer | ✅ | Append-only JSONL — observe only, no feedback loop |

---

## Module Map

```
akf/
  pipeline.py          Pipeline class — generate(), enrich(), enrich_dir(), validate(), batch_generate()
  enricher.py          File reader, YAML extractor, merge logic, prompt builder (enrich pipeline)
  validator.py         Validation Engine — binary VALID/INVALID + E001–E008
  validation_error.py  ValidationError dataclass + error constructors
  error_normalizer.py  Error → deterministic LLM repair instructions
  retry_controller.py  run_retry_loop() — convergence protection
  commit_gate.py       Atomic write — only VALID files reach disk
  telemetry.py         TelemetryWriter — append-only JSONL (GenerationEvent + EnrichEvent)
  config.py            get_config() — loads akf.yaml or bundled defaults
  server.py            FastAPI REST API — /v1/generate, /v1/validate, /v1/batch, /v1/enrich
  mcp_server.py        MCP server (FastMCP) — akf_generate, akf_validate, akf_enrich, akf_batch
  market_pipeline.py   Three-stage market analysis pipeline
  canvas_generator.py  Obsidian Canvas file generation
  defaults/akf.yaml    Default taxonomy + enums (package fallback)

cli.py                 Entry point — command routing and argument parsing
llm_providers.py       Provider router — Claude / Gemini / GPT-4 / Groq / Grok / Ollama
exceptions.py          Typed exception hierarchy
logger.py              Logging factory (human + JSON)

Scripts/
  validate_yaml.py     Standalone YAML frontmatter validator
  analyze_telemetry.py Telemetry aggregation — retry rate, ontology friction

tests/                 560+ tests, 91% coverage
.github/workflows/     ci.yml · tests.yml · lint.yml · validate.yml · changelog.yml · release.yml
```

---

## Core Components

### Pipeline (`akf/pipeline.py`)

The main public interface. Orchestrates the full generate/enrich/validate flow by composing the other components. Exposes `generate()`, `enrich()`, `enrich_dir()`, `validate()`, and `batch_generate()`.

### Validation Engine (`akf/validator.py`)

Takes raw Markdown content and returns a binary `VALID` / `INVALID` decision plus a list of typed `ValidationError` objects. Checks:
- Required fields (E002)
- Enum values: `type`, `level`, `status` (E001)
- Domain taxonomy (E006)
- Date format (E003)
- Date ordering: `created ≤ updated` (E007)
- Type constraints: `tags` as list, `title` as string (E004)
- Frontmatter syntax (E005)
- Relationship types (E008)

### Error Normalizer (`akf/error_normalizer.py`)

Converts `ValidationError` objects into deterministic, human-readable repair instructions for the LLM. Each error code maps to a fixed template that tells the model exactly what went wrong and what to do instead.

### Retry Controller (`akf/retry_controller.py`)

Implements `run_retry_loop()` with convergence protection:
- Maximum 3 LLM attempts
- Computes a hash of each error set
- Aborts immediately if the same hash appears twice — identical errors on retry mean the LLM cannot self-correct, indicating a schema problem

### Commit Gate (`akf/commit_gate.py`)

Atomic write: only writes a file to disk after validation passes. Uses a write-to-temp-then-rename pattern to prevent partial writes.

### Telemetry (`akf/telemetry.py`)

Append-only JSONL event stream. Records `GenerationEvent` and `EnrichEvent` for every pipeline run. Events include `generation_id`, `attempts`, `success`, `errors`, and `provider`. Used for observing retry patterns and ontology friction. Not a feedback loop — read-only from the pipeline's perspective.

### Config (`akf/config.py`)

`get_config()` loads `akf.yaml` from `AKF_CONFIG_PATH`, the current working directory, or the bundled `akf/defaults/akf.yaml`. Returns a dict used by the Validator and Pipeline.

### Enricher (`akf/enricher.py`)

Reads existing Markdown files, extracts any existing YAML frontmatter, builds a merge prompt, and passes it to the LLM. Handles the "partial frontmatter" case by asking the LLM to fill in missing fields only (unless `--force`).

---

## Public API Declaration

### Interface 1 — CLI

```
akf generate "<prompt>"           Generate a validated .md file
akf generate "<prompt>" --output  Write to specified path
akf enrich <path>                 Add YAML frontmatter to existing .md files
akf enrich <path> --dry-run       Preview only, no writes
akf enrich <path> --force         Overwrite valid frontmatter
akf validate <file>               Validate a single file
akf validate --path <dir>         Validate all .md files in directory
akf validate <dir> --strict       Validate; treat warnings as errors
akf serve --port <n>              Start REST API server
akf init                          Scaffold akf.yaml in working directory
akf models                        List available LLM providers and key status
```

### Interface 2 — Python SDK

```python
from akf import Pipeline

pipeline = Pipeline(output: str | Path, config: dict | None = None)

pipeline.generate(prompt: str) -> GenerationResult
pipeline.enrich(path: str | Path, force: bool = False) -> EnrichResult
pipeline.enrich_dir(path: str | Path, force: bool = False) -> list[EnrichResult]
pipeline.validate(path: str | Path) -> ValidationResult
pipeline.batch_generate(prompts: list[str]) -> list[GenerationResult]
```

### Interface 3 — REST API

```
GET  /health
POST /v1/generate    → validated file
POST /v1/enrich      → enriched content
POST /v1/validate    → schema check result
POST /v1/batch       → multiple files
GET  /v1/models      → available providers
```

### Contract — akf.yaml Configuration

The config schema is versioned at `schema_version: "1.0.0"`. See [Configuration](Configuration).

---

## Breaking Change Policy

Breaking changes to any public interface require a MAJOR version increment. See [Contributing](Contributing) for the full versioning policy.

**Breaking (requires MAJOR):**
- Removing or renaming a CLI command
- Changing parameter types or removing fields from result dataclasses
- Removing a REST endpoint or renaming a response field
- Removing an E-code or changing its severity
- Renaming a top-level key in `akf.yaml`

**Non-breaking (MINOR):**
- New CLI commands or optional flags
- New Python SDK methods
- New REST endpoints
- New E-codes
- New optional `akf.yaml` keys

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
| COV-1 | `pipeline.py` 86% — batch error paths uncovered | Low | Open |
| COV-2 | `validator.py` 92% — legacy `taxonomy_path` branch | Low | Open |

---

## Related Pages

- [Error Codes](Error-Codes) — E001–E008 descriptions
- [Configuration](Configuration) — akf.yaml schema
- [Contributing](Contributing) — dev setup, adding providers
