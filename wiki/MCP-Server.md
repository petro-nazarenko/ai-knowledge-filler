# MCP Server

AI Knowledge Filler includes a Model Context Protocol (MCP) server that exposes the AKF pipeline as tools for MCP-compatible clients such as Claude Desktop, Cursor, and Zed.

---

## What is MCP?

[Model Context Protocol](https://modelcontextprotocol.io) is an open standard for connecting AI assistants to external tools and data sources. AKF's MCP server lets you invoke `akf generate`, `akf validate`, `akf enrich`, and `akf batch` directly from your AI assistant conversation.

---

## Installation

MCP support requires the optional `mcp` dependency:

```bash
pip install "ai-knowledge-filler[mcp]"
```

---

## Starting the MCP Server

### Local (stdio) — for Claude Desktop, Cursor, Zed

```bash
akf serve --mcp
```

This starts the server using the `stdio` transport, which is required for local MCP clients.

### Remote (streamable-http)

```bash
akf serve --mcp --transport streamable-http
```

This starts an HTTP server suitable for remote deployments and multi-user environments.

---

## Available Tools

| Tool | Description |
|------|-------------|
| `akf_generate` | Generate a validated Markdown knowledge file from a prompt |
| `akf_validate` | Validate YAML frontmatter in a file or directory |
| `akf_enrich` | Add or update YAML frontmatter on existing Markdown files |
| `akf_batch` | Generate multiple files from a list of prompts |

---

## Tool Reference

### `akf_generate`

Generate a single validated Markdown knowledge file.

**Input:**
```json
{
  "prompt": "Create a guide on JWT authentication"
}
```

**Output:**
```json
{
  "success": true,
  "file_path": "./vault/JWT_Authentication_Guide.md",
  "attempts": 1,
  "errors": []
}
```

---

### `akf_validate`

Validate YAML frontmatter in a file or all files in a directory.

**Input:**
```json
{
  "path": "./vault/",
  "strict": false
}
```

**Output:**
```json
{
  "total": 5,
  "valid": 4,
  "invalid": 1,
  "errors": [
    {
      "file": "./vault/old-note.md",
      "code": "E006",
      "field": "domain",
      "received": "backend"
    }
  ]
}
```

---

### `akf_enrich`

Add or update YAML frontmatter on existing Markdown files.

**Input:**
```json
{
  "path": "./notes/",
  "force": false
}
```

**Output:**
```json
{
  "enriched": 3,
  "skipped": 2,
  "failed": 0,
  "results": [...]
}
```

---

### `akf_batch`

Generate multiple validated files from a list of prompts.

**Input:**
```json
{
  "prompts": [
    "Guide on API rate limiting",
    "Concept: database indexing",
    "Docker security checklist"
  ]
}
```

**Output:**
```json
{
  "results": [
    {"success": true,  "file_path": "./vault/API_Rate_Limiting.md"},
    {"success": true,  "file_path": "./vault/Database_Indexing.md"},
    {"success": false, "file_path": null, "errors": [...]}
  ]
}
```

---

## Client Configuration

### Claude Desktop

Add the following to `claude_desktop_config.json` (usually at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

If using a virtual environment, specify the full path to `akf`:

```json
{
  "mcpServers": {
    "akf": {
      "command": "/home/user/.venv/bin/akf",
      "args": ["serve", "--mcp"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "GROQ_API_KEY": "gsk_..."
      }
    }
  }
}
```

---

### Cursor

In Cursor settings, add MCP server:

```json
{
  "mcp": {
    "servers": {
      "akf": {
        "command": "akf",
        "args": ["serve", "--mcp"]
      }
    }
  }
}
```

---

### Zed

In `~/.config/zed/settings.json`:

```json
{
  "assistant": {
    "mcp_servers": {
      "akf": {
        "command": "akf",
        "args": ["serve", "--mcp"]
      }
    }
  }
}
```

---

## Using AKF Tools in Claude

Once configured, you can invoke AKF tools directly in Claude:

> **You:** Generate a knowledge file about Docker multi-stage builds
>
> **Claude:** *(calls `akf_generate` with prompt: "Docker multi-stage builds guide")*
>
> **Claude:** Created `./vault/Docker_Multi_Stage_Builds.md` successfully (1 attempt).

> **You:** Validate all files in my vault
>
> **Claude:** *(calls `akf_validate` with path: "./vault/")*
>
> **Claude:** Found 12 files. 11 valid, 1 error: `old-note.md` has E006 on `domain` (received: "backend").

---

## Environment Variables

When starting the MCP server, ensure the relevant API keys are available in the environment:

```bash
export GROQ_API_KEY="gsk_..."
export ANTHROPIC_API_KEY="sk-ant-..."
akf serve --mcp
```

Or pass them in the client config's `env` block (see Claude Desktop example above).

---

## Troubleshooting

**MCP server not found by client**
- Ensure `akf` is in your `PATH` (or specify the full path in the client config)
- Restart the client application after updating the config
- Check that `ai-knowledge-filler[mcp]` is installed in the same Python environment

**No API key error**
- Set at least one LLM provider API key in the environment
- Check `akf models` to verify provider availability

**Connection refused (streamable-http)**
- Ensure the server is running: `akf serve --mcp --transport streamable-http`
- Check the port is not blocked by a firewall

---

## Related Pages

- [CLI Reference](CLI-Reference) — `akf serve --mcp` command
- [REST API](REST-API) — HTTP API alternative
- [Installation](Installation) — installing with MCP support
