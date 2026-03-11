# Python API

The `akf` Python package exposes a `Pipeline` class as its primary interface. This page documents all public methods, constructor parameters, and result types.

---

## Installation

```bash
pip install ai-knowledge-filler
```

---

## Quick Start

```python
from akf import Pipeline

pipeline = Pipeline(output="./vault/")

# Generate a new validated file
result = pipeline.generate("Create a guide on API rate limiting")
print(result.success, result.file_path)

# Validate an existing file
result = pipeline.validate("./vault/API_Rate_Limiting_Strategy.md")
print(result.is_valid, result.errors)

# Enrich an existing file
result = pipeline.enrich("./existing-notes/old-note.md")
print(result.status)
```

---

## `Pipeline` Class

### Constructor

```python
from akf import Pipeline

pipeline = Pipeline(
    output: str | Path,          # vault directory path — required
    config: dict | None = None,  # override akf.yaml settings — optional
)
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `output` | `str \| Path` | Yes | Directory where generated files are written |
| `config` | `dict \| None` | No | Config dict to override `akf.yaml` settings |

**Config override example:**
```python
pipeline = Pipeline(
    output="./vault/",
    config={
        "taxonomy": {"domain": ["api-design", "devops", "security"]},
        "enums": {
            "type": ["concept", "guide", "reference"],
            "status": ["draft", "active", "archived"],
        }
    }
)
```

---

## Methods

### `pipeline.generate()`

Generate a single validated Markdown knowledge file from a prompt.

```python
result: GenerationResult = pipeline.generate(prompt: str) -> GenerationResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | `str` | Natural language prompt describing the file to generate |

**Returns:** [`GenerationResult`](#generationresult)

**Example:**
```python
result = pipeline.generate("Create a reference guide for JWT authentication")

if result.success:
    print(f"Written to: {result.file_path}")
    print(f"Attempts: {result.attempts}")
else:
    for error in result.errors:
        print(f"  {error.code} on {error.field}: got {error.received!r}")
```

---

### `pipeline.batch_generate()`

Generate multiple validated files from a list of prompts.

```python
results: list[GenerationResult] = pipeline.batch_generate(prompts: list[str])
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompts` | `list[str]` | List of natural language prompts |

**Returns:** `list[GenerationResult]` — one result per prompt, in order.

**Example:**
```python
results = pipeline.batch_generate([
    "Guide on API rate limiting",
    "Concept: database indexing",
    "Security checklist for Docker"
])

for result in results:
    status = "✅" if result.success else "❌"
    print(f"{status} {result.file_path or 'FAILED'}")
```

---

### `pipeline.validate()`

Validate the YAML frontmatter of a Markdown file against the configured schema.

```python
result: ValidationResult = pipeline.validate(path: str | Path) -> ValidationResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str \| Path` | Path to the Markdown file to validate |

**Returns:** [`ValidationResult`](#validationresult)

**Example:**
```python
result = pipeline.validate("./vault/jwt-auth.md")

if result.is_valid:
    print("File is valid")
else:
    for err in result.errors:
        print(f"  [{err.severity.upper()}] {err.code} on '{err.field}'")
        print(f"    Expected: {err.expected}")
        print(f"    Got:      {err.received}")
```

---

### `pipeline.enrich()`

Add or update YAML frontmatter on a single existing Markdown file.

```python
result: EnrichResult = pipeline.enrich(
    path: str | Path,
    force: bool = False,
) -> EnrichResult
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str \| Path` | — | Path to the Markdown file to enrich |
| `force` | `bool` | `False` | If `True`, regenerate frontmatter even if it is already valid |

**Returns:** [`EnrichResult`](#enrichresult)

**Example:**
```python
result = pipeline.enrich("./notes/old-note.md")
print(result.status)   # "enriched", "skipped", "failed", or "warning"
```

---

### `pipeline.enrich_dir()`

Add or update YAML frontmatter on all `.md` files in a directory.

```python
results: list[EnrichResult] = pipeline.enrich_dir(
    path: str | Path,
    force: bool = False,
) -> list[EnrichResult]
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str \| Path` | — | Directory to process recursively |
| `force` | `bool` | `False` | If `True`, regenerate valid frontmatter too |

**Returns:** `list[EnrichResult]`

**Example:**
```python
results = pipeline.enrich_dir("./notes/")

enriched = [r for r in results if r.status == "enriched"]
skipped  = [r for r in results if r.status == "skipped"]
failed   = [r for r in results if r.status == "failed"]

print(f"Enriched: {len(enriched)}, Skipped: {len(skipped)}, Failed: {len(failed)}")
```

---

## Result Types

### `GenerationResult`

```python
@dataclass
class GenerationResult:
    success: bool                    # True if a valid file was written to disk
    file_path: Path | None           # Path of the written file; None on failure
    content: str | None              # Raw Markdown content; None on failure
    errors: list[ValidationError]    # Validation errors from the last attempt
    attempts: int                    # Number of LLM attempts made (1–3)
    generation_id: str               # UUID for correlating telemetry events
```

---

### `EnrichResult`

```python
@dataclass
class EnrichResult:
    status: str                      # "enriched" | "skipped" | "failed" | "warning"
    file_path: Path                  # Path of the processed file
    errors: list[ValidationError]    # Validation errors from the last attempt
    attempts: int                    # Number of LLM attempts made
    generation_id: str | None        # UUID for telemetry; None if skipped
```

**Status values:**

| Status | Meaning |
|--------|---------|
| `"enriched"` | Frontmatter generated and written successfully |
| `"skipped"` | File already had valid frontmatter (and `--force` was not set) |
| `"failed"` | Validation failed after max retries; file not modified |
| `"warning"` | File was empty or could not be processed |

---

### `ValidationResult`

```python
@dataclass
class ValidationResult:
    is_valid: bool                   # True if no errors (warnings may still be present)
    errors: list[ValidationError]    # All validation errors and warnings
```

---

### `ValidationError`

```python
@dataclass
class ValidationError:
    code: str        # E001–E008 — see Error Codes wiki page
    field: str       # YAML frontmatter field name (e.g. "domain", "type")
    expected: Any    # Allowed values or expected type
    received: Any    # What was found in the file
    severity: str    # "error" | "warning"
```

**Example:**
```python
ValidationError(
    code="E006",
    field="domain",
    expected=["api-design", "devops", "security"],
    received="backend",
    severity="error",
)
```

See [Error Codes](Error-Codes) for the full list.

---

## Exception Hierarchy

```python
from exceptions import (
    AKFError,               # Base exception
    ValidationError,        # Schema validation failure
    RetryExhaustedError,    # Max retries reached without convergence
    ConfigError,            # akf.yaml missing or invalid
    ProviderError,          # LLM provider unavailable or API error
)
```

**Example:**
```python
from akf import Pipeline
from exceptions import RetryExhaustedError, ProviderError

pipeline = Pipeline(output="./vault/")

try:
    result = pipeline.generate("Create a guide on X")
except RetryExhaustedError as e:
    print(f"Could not converge after 3 attempts: {e}")
except ProviderError as e:
    print(f"LLM provider error: {e}")
```

---

## Working with Telemetry

AKF writes an append-only JSONL event stream for observability. Events are written to `AKF_TELEMETRY_PATH` (default: `telemetry/events.jsonl`).

```python
import json

with open("telemetry/events.jsonl") as f:
    for line in f:
        event = json.loads(line)
        print(event["generation_id"], event["attempts"], event["success"])
```

Use `Scripts/analyze_telemetry.py` to aggregate retry rates and identify ontology friction:

```bash
python Scripts/analyze_telemetry.py telemetry/events.jsonl
```

---

## Complete Example

```python
from pathlib import Path
from akf import Pipeline

pipeline = Pipeline(output=Path("./vault"))

# Batch generate a knowledge base
topics = [
    "Concept: API gateway patterns",
    "Guide: Docker multi-stage builds",
    "Reference: JWT claims and validation",
    "Checklist: production security review",
]

results = pipeline.batch_generate(topics)

for result in results:
    if result.success:
        print(f"✅ {result.file_path.name} ({result.attempts} attempt(s))")
    else:
        print(f"❌ FAILED after {result.attempts} attempt(s)")
        for err in result.errors:
            print(f"   {err.code} {err.field}: {err.received!r}")

# Validate everything that was written
print("\n--- Validation pass ---")
for result in results:
    if result.file_path:
        vr = pipeline.validate(result.file_path)
        status = "✅" if vr.is_valid else "❌"
        print(f"{status} {result.file_path.name}")
```

---

## Related Pages

- [CLI Reference](CLI-Reference) — command-line interface
- [REST API](REST-API) — HTTP interface
- [Error Codes](Error-Codes) — E001–E008 descriptions
- [Configuration](Configuration) — `akf.yaml` schema
