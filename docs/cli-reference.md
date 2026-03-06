---
title: "AKF CLI Reference"
type: reference
domain: akf-docs
level: intermediate
status: active
version: v2.1
tags: [cli, reference, commands, akf, enrich, validate, generate, mcp, serve]
related:
  - "docs/user-guide.md"
created: 2026-02-19
updated: 2026-03-06
---

## Purpose

Complete reference for all `akf` CLI commands, flags, environment variables, and exit codes.
Reflects actual behaviour as of v0.6.1.

---

## Commands Overview

```
akf <command> [options]

Commands:
  generate    Generate a structured Markdown knowledge file from a prompt
  enrich      Add YAML frontmatter to existing Markdown files
  validate    Validate YAML frontmatter in Markdown files
  init        Create akf.yaml config in target directory
  models      List available LLM providers and their status
  serve       Start REST API server or MCP server
```

---

## `akf generate`

Generate a knowledge file from a natural language prompt.

**Usage:**
```bash
akf generate PROMPT [--model MODEL] [--output PATH]
akf generate --batch PLAN_JSON [--model MODEL] [--output PATH]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--model` | `-m` | `auto` | LLM provider: `auto` `claude` `gemini` `gpt4` `groq` `grok` `ollama` |
| `--output` | `-o` | `AKF_OUTPUT_DIR` or `.` | Output directory |
| `--batch` | `-b` | — | JSON file with batch plan: `[{"prompt": str, "domain": str, "type": str}]` |

**Examples:**
```bash
akf generate "Create a concept file about API rate limiting"
akf generate -m groq "Create a guide for Docker multi-stage builds"
akf generate -m claude -o ./docs "Create a security checklist"
akf generate --batch plan.json
akf generate --batch plan.json --model groq --output ./vault
```

---

## `akf enrich`

Add YAML frontmatter to existing Markdown files that have missing or incomplete metadata.

**Usage:**
```bash
akf enrich PATH [--dry-run] [--force] [--model MODEL] [--output DIR]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `PATH` | File or directory to enrich |

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--dry-run` | — | `False` | Print generated YAML, no file writes |
| `--force` | `-f` | `False` | Overwrite valid existing frontmatter |
| `--model` | `-m` | `auto` | LLM provider |
| `--output` | `-o` | — | Copy enriched files here (no overwrite of originals) |

**Behavior by file state:**

| State | Default | `--force` |
|-------|---------|-----------|
| No frontmatter | Generate + validate + write | Same |
| Incomplete frontmatter | Generate missing fields only | Regenerate all |
| Valid frontmatter | Skip | Regenerate all |
| Empty file | Skip with warning | Skip |

**Examples:**
```bash
akf enrich docs/
akf enrich docs/ --dry-run
akf enrich docs/old-notes/ --force --model groq
akf enrich vault/ --output vault-enriched/
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | All enriched or skipped (valid) |
| `1` | One or more files failed after max retries |
| `2` | No `.md` files found |
| `3` | Config error |

---

## `akf validate`

Validate YAML frontmatter against schema and taxonomy defined in `akf.yaml`.

**Usage:**
```bash
akf validate [--file FILE] [--path PATH] [--strict]
```

**Options:**

| Flag | Short | Description |
|------|-------|-------------|
| `--file` | `-f` | Validate a single file |
| `--path` | `-p` | Validate all `.md` files recursively |
| `--strict` | `-s` | Promote warnings to errors |

If no flags provided: validates all `**/*.md` in current directory.

**Error codes:**

| Code | Field | Meaning |
|------|-------|---------|
| E001 | type/level/status | Invalid enum value |
| E002 | any | Required field missing |
| E003 | created/updated | Date not ISO 8601 |
| E004 | title/tags | Type mismatch |
| E005 | frontmatter | General schema violation |
| E006 | domain | Not in taxonomy |
| E007 | created/updated | `created` > `updated` |

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | All files valid |
| `1` | One or more errors found |

**Examples:**
```bash
akf validate -f docs/cli-reference.md
akf validate -p docs/
akf validate -p docs/ --strict
```

---

## `akf init`

Generate `akf.yaml` config file in target directory.

**Usage:**
```bash
akf init [--path DIR] [--force]
```

**Options:**

| Flag | Short | Description |
|------|-------|-------------|
| `--path` | `-p` | Target directory (default: CWD) |
| `--force` | `-f` | Overwrite existing `akf.yaml` |

**Example:**
```bash
akf init
akf init --path ./my-vault
```

---

## `akf models`

List all LLM providers, availability status, and active model names.

**Usage:**
```bash
akf models
```

**Output example:**
```
✅ groq       Groq (Llama 3.3)
   Model: llama-3.3-70b-versatile

✅ claude     Claude (Anthropic)
   Model: claude-sonnet-4-20250514

❌ gemini     Gemini (Google)
   Set GOOGLE_API_KEY
```

---

## `akf serve`

Start AKF as a REST API server or MCP server.

**Usage:**
```bash
akf serve [--host HOST] [--port PORT]
akf serve --mcp [--transport stdio|streamable-http]
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `0.0.0.0` | Bind address (REST only) |
| `--port` | `8000` | Port (REST only) |
| `--mcp` | `False` | Run as MCP server instead of REST API |
| `--transport` | `stdio` | MCP transport: `stdio` (local) or `streamable-http` (remote) |

**REST API endpoints:**

| Method | Path | Rate limit | Description |
|--------|------|-----------|-------------|
| `GET` | `/health` | — | Health check |
| `POST` | `/v1/generate` | 10/min | Generate file |
| `POST` | `/v1/enrich` | 10/min | Enrich file |
| `POST` | `/v1/validate` | 30/min | Validate content |
| `POST` | `/v1/batch` | 3/min | Batch generate |
| `GET` | `/v1/models` | — | List providers |

**MCP tools:**

| Tool | Description |
|------|-------------|
| `akf_generate` | Generate a validated knowledge file |
| `akf_validate` | Validate file or directory frontmatter |
| `akf_enrich` | Add/update frontmatter on existing files |
| `akf_batch` | Generate multiple files from a plan |

**Examples:**
```bash
akf serve                                    # REST API on :8000
akf serve --port 9000
akf serve --mcp                              # MCP stdio (Claude Desktop, Cursor, Zed)
akf serve --mcp --transport streamable-http  # MCP HTTP (remote)
```

**Requires for MCP:** `pip install 'ai-knowledge-filler[mcp]'`

---

## Environment Variables

### API Keys

| Variable | Provider |
|----------|----------|
| `ANTHROPIC_API_KEY` | Claude |
| `GOOGLE_API_KEY` | Gemini |
| `OPENAI_API_KEY` | GPT-4 / Grok |
| `GROQ_API_KEY` | Groq |
| `XAI_API_KEY` | Grok (xAI) |

### Runtime

| Variable | Default | Description |
|----------|---------|-------------|
| `AKF_OUTPUT_DIR` | `.` | Default output directory |
| `AKF_TELEMETRY_PATH` | `telemetry/events.jsonl` | Telemetry log path |
| `AKF_CONFIG_PATH` | — | Explicit path to `akf.yaml` |
| `AKF_API_KEY` | — | REST API auth key (optional) |
| `AKF_CORS_ORIGINS` | `*` | Allowed CORS origins |

### Provider Priority (auto mode)

```
groq → grok → claude → gemini → gpt4 → ollama
```

---

## Conclusion

Full pipeline: `akf init` → `akf enrich` (existing files) → `akf generate` (new files) → `akf validate` → commit.
