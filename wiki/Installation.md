# Installation

This page covers how to install AI Knowledge Filler, configure your environment, and verify the setup.

---

## Requirements

- **Python 3.10 or higher**
- At least one LLM API key (or a running [Ollama](https://ollama.ai) instance for offline use)

---

## Install from PyPI

```bash
pip install ai-knowledge-filler
```

### Optional Feature Groups

| Command | Includes |
|---------|---------|
| `pip install ai-knowledge-filler` | Core CLI + all LLM providers |
| `pip install "ai-knowledge-filler[mcp]"` | + MCP server support |
| `pip install "ai-knowledge-filler[server]"` | + FastAPI REST API server |
| `pip install "ai-knowledge-filler[all]"` | All optional dependencies |

---

## Install from Source

```bash
git clone https://github.com/petro-nazarenko/ai-knowledge-filler.git
cd ai-knowledge-filler
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

For development (includes test tools):
```bash
pip install -e ".[dev]"
```

---

## Set Up API Keys

Set the environment variable for your preferred LLM provider:

```bash
# Groq — free tier, fastest to start
export GROQ_API_KEY="gsk_..."

# Claude (Anthropic) — recommended for complex content
export ANTHROPIC_API_KEY="sk-ant-..."

# Gemini (Google) — fast and cost-effective
export GOOGLE_API_KEY="..."

# GPT-4 (OpenAI)
export OPENAI_API_KEY="sk-..."

# Grok (xAI)
export XAI_API_KEY="..."

# Ollama — no key needed, requires local Ollama service
# Install from https://ollama.ai and run: ollama pull llama3
```

To make keys persistent, add them to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.).

---

## Verify Installation

```bash
# Check the CLI is available
akf --help

# List providers and their availability
akf models
```

Example output:
```
✅ groq       Groq (Llama 3.3)
   Model: llama-3.3-70b-versatile

✅ claude     Claude (Anthropic)
   Model: claude-sonnet-4-20250514

❌ gemini     Gemini (Google)
   Set GOOGLE_API_KEY
```

---

## Initialize a Project

```bash
mkdir my-vault && cd my-vault
akf init
```

This creates an `akf.yaml` configuration file in the current directory. Edit it to define your taxonomy:

```yaml
schema_version: "1.0.0"
vault_path: "./vault"

taxonomy:
  domain:
    - api-design
    - devops
    - security

enums:
  type: [concept, guide, reference, checklist]
  level: [beginner, intermediate, advanced]
  status: [draft, active, completed, archived]
```

See [Configuration](Configuration) for the full schema reference.

---

## Generate Your First File

```bash
akf generate "Create a guide on JWT authentication"
```

AKF runs the full pipeline and writes a validated Markdown file to `./vault/`:

```yaml
---
title: "JWT Authentication Guide"
type: guide
domain: security
level: intermediate
status: active
version: v1.0
tags: [jwt, authentication, security, api]
related:
  - "[[API Security Patterns]]"
created: 2026-03-11
updated: 2026-03-11
---

## Purpose
...
```

---

## Windows

On Windows, use the `install.cmd` helper or run:

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install ai-knowledge-filler
```

Set environment variables in PowerShell:
```powershell
$env:GROQ_API_KEY = "gsk_..."
```

Or persistently via System Properties → Environment Variables.

---

## Upgrading

```bash
pip install --upgrade ai-knowledge-filler
```

Check the [CHANGELOG](https://github.com/petro-nazarenko/ai-knowledge-filler/blob/main/CHANGELOG.md) for breaking changes before upgrading across MAJOR versions.

---

## Troubleshooting

**`akf: command not found`**
Ensure the Python `bin` / `Scripts` directory is in your `PATH`. If using a virtual environment, activate it first.

**`No providers available`**
Set at least one API key (see above) or install and start Ollama.

**`ValidationError: E006 on domain`**
Your `akf.yaml` taxonomy does not include the domain the LLM chose. Run `akf init` to regenerate the config, or add the domain manually. See [Error Codes](Error-Codes).

---

## Next Steps

- [Configuration](Configuration) — customize `akf.yaml`
- [CLI Reference](CLI-Reference) — all available commands
- [Python API](Python-API) — use AKF programmatically
