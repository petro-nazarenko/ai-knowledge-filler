---
title: "AKF Quickstart Guide"
type: guide
domain: akf-docs
level: beginner
status: active
version: v2.1
tags: [quickstart, installation, setup, akf, pipeline, validation, mcp]
related:
  - "docs/cli-reference.md"
created: 2026-02-19
updated: 2026-03-06
---

## Purpose

Get from zero to a validated, schema-compliant Markdown file in under 5 minutes.

AKF is a **validation pipeline** — not a note-taking app. It enforces a schema contract on every file LLMs generate. No silent failures. No partial commits.

---

## Prerequisites

- Python 3.10+
- At least one API key (or a running Ollama instance)

---

## Installation

```bash
pip install ai-knowledge-filler
```

With MCP server support:
```bash
pip install 'ai-knowledge-filler[mcp]'
```

With all LLM providers:
```bash
pip install "ai-knowledge-filler[all]"
```

---

## Step 1: Init Config

```bash
akf init
```

Creates `akf.yaml` in the current directory. Edit it to define your domains:

```yaml
vault_path: "./docs"

taxonomy:
  domains:
    - api-design
    - devops
    - security
```

---

## Step 2: Set API Key

```bash
export GROQ_API_KEY="gsk_..."   # free tier, fastest
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

Check available providers:
```bash
akf models
```

---

## Step 3: Generate a File

```bash
akf generate "Create a reference guide for JWT authentication"
```

AKF runs the full pipeline:

```
Prompt → LLM → Validation Engine → Retry Controller → Commit Gate → File
```

If the LLM returns invalid YAML, AKF retries up to 3 times with error-specific repair instructions. Only valid files reach disk.

---

## Step 4: Enrich Existing Files

Have existing Markdown files without frontmatter? Enrich them in bulk:

```bash
akf enrich docs/
```

Preview first without writing:
```bash
akf enrich docs/ --dry-run
```

Force-regenerate already-valid frontmatter:
```bash
akf enrich docs/ --force
```

---

## Step 5: Validate

```bash
akf validate --path docs/
```

Output:
```
✅ docs/jwt-auth.md
✅ docs/quickstart.md
❌ docs/old-note.md
   [ERROR] E006_TAXONOMY_VIOLATION field='domain' expected=[...] received='backend'

→  Total: 3 | OK: 2 | Errors: 1
```

Exit code `1` when errors found — suitable for CI gates.

---

## CI Integration

```yaml
# .github/workflows/validate.yml
- name: Validate docs/
  run: akf validate --path docs/
```

Every PR that introduces invalid metadata fails the check.

---

## Batch Generation

Generate multiple files from a JSON plan:

```bash
cat plan.json
```
```json
[
  { "prompt": "JWT authentication guide", "domain": "security", "type": "guide" },
  { "prompt": "Docker networking concept", "domain": "devops",   "type": "concept" }
]
```
```bash
akf generate --batch plan.json
```

---

## MCP Server

AKF exposes four tools for Claude Desktop, Cursor, Zed, and any MCP-compatible client.

```bash
# Install MCP support
pip install 'ai-knowledge-filler[mcp]'

# Start server (stdio — for local clients)
akf serve --mcp

# streamable-http — for remote deployments
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

Available MCP tools: `akf_generate` · `akf_validate` · `akf_enrich` · `akf_batch`

---

## REST API

```bash
akf serve --port 8000
```

```bash
curl -X POST http://localhost:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a guide for Docker networking"}'
```

---

## Python API

```python
from akf import Pipeline

pipeline = Pipeline(output="./docs")

# Generate new file
result = pipeline.generate("Create a guide for JWT authentication")
print(result.path)

# Enrich existing file
result = pipeline.enrich("docs/old-note.md")

# Validate
result = pipeline.validate("docs/old-note.md")
print(result.valid)
```

---

## What Every Committed File Guarantees

- Required fields present: `title`, `type`, `domain`, `level`, `status`, `tags`, `created`, `updated`
- `domain` from your `akf.yaml` taxonomy
- `type`, `level`, `status` from controlled enum sets
- ISO 8601 dates, `created ≤ updated`
- `tags` as array with ≥3 items

Violations produce typed error codes (E001–E007). No silent failures.

---

## Conclusion

Full workflow: `akf init` → set API key → `akf enrich` (existing files) → `akf generate` (new files) → `akf validate` → CI gate.

MCP workflow: `pip install 'ai-knowledge-filler[mcp]'` → `akf serve --mcp` → connect Claude Desktop.
