# CLI Reference

Complete reference for all `akf` CLI commands, flags, environment variables, and exit codes.

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

Run `akf --help` or `akf <command> --help` for usage info.

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
| `--batch` | `-b` | — | JSON file with batch plan |

**Batch plan format** (`plan.json`):
```json
[
  {"prompt": "JWT authentication guide", "domain": "security", "type": "guide"},
  {"prompt": "Docker networking concept", "domain": "devops",   "type": "concept"}
]
```

**Examples:**
```bash
akf generate "Create a concept file about API rate limiting"
akf generate -m groq "Create a guide for Docker multi-stage builds"
akf generate -m claude -o ./docs "Create a security checklist"
akf generate --batch plan.json
akf generate --batch plan.json --model groq --output ./vault
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | File generated and written successfully |
| `1` | Validation failed after max retries |
| `3` | Config error |

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
| `--dry-run` | — | `False` | Print generated YAML without writing files |
| `--force` | `-f` | `False` | Overwrite valid existing frontmatter |
| `--model` | `-m` | `auto` | LLM provider |
| `--output` | `-o` | — | Copy enriched files to this directory |

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
| `0` | All files enriched or skipped (valid) |
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
| `--path` | `-p` | Validate all `.md` files recursively in a directory |
| `--strict` | `-s` | Promote warnings to errors |

If no flags provided, validates all `**/*.md` in the current directory.

**Error codes:**

| Code | Field | Meaning |
|------|-------|---------|
| E001 | type / level / status | Invalid enum value |
| E002 | any | Required field missing |
| E003 | created / updated | Date not ISO 8601 |
| E004 | title / tags | Type mismatch |
| E005 | frontmatter | General schema violation |
| E006 | domain | Not in taxonomy |
| E007 | created / updated | `created` > `updated` |
| E008 | related | Typed relationship label not in `relationship_types` |

See [Error Codes](Error-Codes) for full descriptions and repair guidance.

**Output example:**
```
✅ docs/jwt-auth.md
✅ docs/quickstart.md
❌ docs/old-note.md
   [ERROR] E006_TAXONOMY_VIOLATION field='domain' expected=[...] received='backend'

→  Total: 3 | OK: 2 | Errors: 1
```

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
| `--path` | `-p` | Target directory (default: current working directory) |
| `--force` | `-f` | Overwrite existing `akf.yaml` |

**Examples:**
```bash
akf init
akf init --path ./my-vault
akf init --force
```

---

## `akf models`

List all LLM providers, their availability status, and active model names.

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

❌ gpt4       GPT-4 (OpenAI)
   Set OPENAI_API_KEY

❌ ollama     Ollama (local)
   Ollama not running or not installed
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

| Method | Path | Rate Limit | Description |
|--------|------|-----------|-------------|
| `GET` | `/health` | — | Health check |
| `POST` | `/v1/generate` | 10/min | Generate a validated file |
| `POST` | `/v1/enrich` | 10/min | Enrich a file |
| `POST` | `/v1/validate` | 30/min | Validate content |
| `POST` | `/v1/batch` | 3/min | Batch generate files |
| `GET` | `/v1/models` | — | List available providers |
| `GET` | `/docs` | — | Swagger UI |

**MCP tools:**

| Tool | Description |
|------|-------------|
| `akf_generate` | Generate a validated knowledge file |
| `akf_validate` | Validate file or directory frontmatter |
| `akf_enrich` | Add or update frontmatter on existing files |
| `akf_batch` | Generate multiple files from a plan |

**Examples:**
```bash
akf serve                                    # REST API on :8000
akf serve --port 9000                        # REST API on :9000
akf serve --mcp                              # MCP stdio (Claude Desktop, Cursor, Zed)
akf serve --mcp --transport streamable-http  # MCP HTTP (remote deployments)
```

**Requires for MCP:** `pip install 'ai-knowledge-filler[mcp]'`

See [REST API](REST-API) and [MCP Server](MCP-Server) for full details.

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

## Full Workflow

```bash
akf init                          # 1. Create akf.yaml
akf models                        # 2. Verify API keys
akf enrich ./existing-notes/      # 3. Enrich existing files
akf generate "Guide on X"         # 4. Generate new files
akf validate --path ./vault/      # 5. Validate all files
```

---

## CI Integration

```yaml
# .github/workflows/validate.yml
- name: Validate docs/
  run: akf validate --path docs/
```

Exit code `1` on validation errors — suitable for blocking PRs with invalid metadata.

---

## Related Pages

- [Configuration](Configuration) — `akf.yaml` reference
- [Error Codes](Error-Codes) — E001–E008 error code meanings
- [REST API](REST-API) — HTTP API reference
- [MCP Server](MCP-Server) — MCP integration guide
