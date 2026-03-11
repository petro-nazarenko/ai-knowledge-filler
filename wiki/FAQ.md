# FAQ

Frequently asked questions about AI Knowledge Filler.

---

## General

### What problem does AKF solve?

LLMs generate inconsistent structured output. When building knowledge bases with YAML frontmatter, models frequently drift: wrong enum values, missing fields, dates in the wrong format, tags as strings instead of arrays. AKF enforces a schema contract before any file touches disk — no silent failures, no manual cleanup.

---

### What does "knowledge file" mean?

A Markdown file with YAML frontmatter that describes the content's metadata. Example:

```yaml
---
title: "API Rate Limiting Strategy"
type: guide
domain: api-design
level: intermediate
status: active
tags: [api, rate-limiting, performance]
created: 2026-03-06
updated: 2026-03-06
---

## Purpose
...
```

This format is used by tools like Obsidian, Logseq, and static site generators. AKF ensures every generated file has complete, valid metadata.

---

### Is AKF a note-taking app?

No. AKF is a **validation pipeline** — it sits between your LLM and the filesystem. It does not have a UI, a sync service, or a storage backend. It just ensures that files meet a schema contract before they are written to disk.

---

### What LLM providers are supported?

| Provider | Environment Variable | Notes |
|----------|---------------------|-------|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | Best for complex content |
| Gemini (Google) | `GOOGLE_API_KEY` | Fast, cost-effective |
| GPT-4 (OpenAI) | `OPENAI_API_KEY` | General purpose |
| Groq | `GROQ_API_KEY` | Free tier, fastest |
| Grok (xAI) | `XAI_API_KEY` | xAI models |
| Ollama | — | Local, offline, private |

Run `akf models` to see which providers are currently available in your environment.

---

### Does AKF work offline?

Yes, with [Ollama](https://ollama.ai). Install Ollama, pull a model (`ollama pull llama3`), and run:

```bash
akf generate "Create a guide on X" --model ollama
```

No internet connection or API key required.

---

## Installation & Setup

### How do I install AKF?

```bash
pip install ai-knowledge-filler
```

See [Installation](Installation) for full instructions, including virtual environment setup and optional dependencies.

---

### Why is `akf` not found after installing?

The Python `bin` (or `Scripts` on Windows) directory is not in your `PATH`. Solutions:

- If using a virtual environment: activate it first (`source .venv/bin/activate`)
- Or install with `pip install --user` and add `~/.local/bin` to your `PATH`
- Or use `python -m cli` as a fallback

---

### How do I update AKF?

```bash
pip install --upgrade ai-knowledge-filler
```

Check the [CHANGELOG](https://github.com/petro-nazarenko/ai-knowledge-filler/blob/main/CHANGELOG.md) before upgrading across MAJOR versions.

---

## Configuration

### Do I need an `akf.yaml` file?

No, but it is strongly recommended. Without it, AKF uses its bundled default taxonomy. The defaults may not match your domain.

Run `akf init` to generate a customizable `akf.yaml` in the current directory.

---

### Can I use multiple taxonomies for different vaults?

Yes. Use `AKF_CONFIG_PATH` to point to a specific config file:

```bash
AKF_CONFIG_PATH=./personal-vault/akf.yaml akf generate "Create a note on X"
AKF_CONFIG_PATH=./work-vault/akf.yaml akf generate "Create a work guide on Y"
```

---

### How do I add a new domain?

Add it to the `taxonomy.domain` list in `akf.yaml`:

```yaml
taxonomy:
  domain:
    - existing-domain
    - my-new-domain
```

No code changes or restarts required. Validate existing files afterward:

```bash
akf validate --path ./vault/
```

---

### What is `schema_version: "1.0.0"` in `akf.yaml`?

It identifies the version of the `akf.yaml` config schema. This value is frozen until a breaking change occurs in the config format, at which point it will increment to `"2.0.0"`. You should not change this value.

---

## Validation & Error Codes

### Why did my file fail with E006?

The `domain` value in the generated file is not in your `taxonomy.domain` list in `akf.yaml`. Either:

1. Add the domain to your taxonomy
2. Or change the `domain` to one that is already in your list

Run `akf init` to see the default domain list if you are not sure what to use.

---

### What happens when validation fails?

AKF converts the error code into a repair instruction and sends it back to the LLM for a retry. This happens automatically, up to 3 times. If the same error fires twice on the same field, the pipeline aborts — repeated identical errors indicate that the schema boundary is the problem, not the model.

---

### Why does AKF abort instead of retrying indefinitely?

Infinite retry loops create cost without convergence. If the same validation error fires twice in a row, the LLM has already seen the repair instruction and failed to apply it — which means the schema has a boundary problem. The right fix is to refine your `akf.yaml` taxonomy, not to keep retrying.

---

### How do I see which errors cause the most retries?

```bash
python Scripts/analyze_telemetry.py telemetry/events.jsonl
```

This aggregates retry rates and shows which domain values and error codes cause the most friction. Use the output to refine your taxonomy.

---

### What is the difference between `akf validate` and the validation in `akf generate`?

`akf validate` is a read-only check on files already on disk. The validation in `akf generate` / `akf enrich` runs as part of the pipeline and gates whether the LLM output is written to disk. Both use the same Validation Engine and error codes.

---

## Batch Generation

### How do I generate multiple files at once?

Use `--batch` with a JSON plan:

```bash
akf generate --batch plan.json
```

`plan.json`:
```json
[
  {"prompt": "Guide on JWT auth", "domain": "security", "type": "guide"},
  {"prompt": "Docker networking concept", "domain": "devops", "type": "concept"}
]
```

Or use the Python API:

```python
results = pipeline.batch_generate([
    "Guide on JWT auth",
    "Docker networking concept",
])
```

---

## MCP & REST API

### How do I use AKF with Claude Desktop?

1. Install MCP support: `pip install "ai-knowledge-filler[mcp]"`
2. Add the server to `claude_desktop_config.json`
3. Restart Claude Desktop

See [MCP Server](MCP-Server) for full configuration instructions.

---

### What is the difference between REST API and MCP?

| | REST API | MCP Server |
|-|---------|-----------|
| Protocol | HTTP | Model Context Protocol |
| Best for | Programmatic integrations, web apps | AI assistants (Claude Desktop, Cursor, Zed) |
| Start command | `akf serve` | `akf serve --mcp` |
| Transport | HTTP | stdio or streamable-http |

---

## Development & Contributing

### How do I run the tests?

```bash
pytest --tb=short
```

With coverage:
```bash
pytest --cov=akf --cov-report=term-missing --cov-fail-under=91
```

---

### Can I add a new LLM provider?

Yes. See [Contributing](Contributing) for step-by-step instructions on adding a new provider, including subclassing `LLMProvider`, registering the provider, updating the CLI, and writing tests.

---

### Where do I report bugs?

Open a GitHub Issue at https://github.com/petro-nazarenko/ai-knowledge-filler/issues.

---

## Related Pages

- [Installation](Installation) — setup guide
- [Configuration](Configuration) — `akf.yaml` reference
- [Error Codes](Error-Codes) — E001–E008 descriptions
- [Contributing](Contributing) — developer guide
