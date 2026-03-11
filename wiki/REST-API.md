# REST API

AKF includes a FastAPI-based REST server that exposes the full pipeline over HTTP. This page documents all endpoints, request/response schemas, authentication, and rate limits.

---

## Starting the Server

```bash
# Start with default settings (0.0.0.0:8000)
akf serve

# Custom host and port
akf serve --host 127.0.0.1 --port 9000
```

**Requires:** `pip install "ai-knowledge-filler[server]"` (or `[all]`)

Interactive API documentation is available at `http://localhost:8000/docs` (Swagger UI).

---

## Authentication

Authentication depends on `AKF_ENV`:

- `AKF_ENV=prod`: `AKF_API_KEY` is mandatory; server fails to start without it.
- `AKF_ENV=dev`: auth is optional unless `AKF_API_KEY` is set.

When auth is enabled, all requests must include a bearer token:

```bash
export AKF_API_KEY="your-secret-key"
```

```http
Authorization: Bearer your-secret-key
```

If `AKF_ENV=dev` and `AKF_API_KEY` is not set, requests pass without auth.

For tenant-level usage analytics (and future billing), send optional header:

```http
X-AKF-Tenant-ID: team-alpha
```

If omitted, server uses `AKF_DEFAULT_TENANT` or falls back to `default`.

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `POST /v1/generate` | `AKF_RATE_LIMIT_GENERATE` (default `10/minute`) |
| `POST /v1/ask` | `AKF_RATE_LIMIT_ASK` (default `10/minute`) |
| `POST /v1/validate` | `AKF_RATE_LIMIT_VALIDATE` (default `30/minute`) |
| `POST /v1/batch` | `AKF_RATE_LIMIT_BATCH` (default `3/minute`) |

Exceeding limits returns **HTTP 429** with a `Retry-After` header.

---

## CORS

CORS is configured via `AKF_CORS_ORIGINS` (default: `http://localhost:3000`).
In production, wildcard `*` is rejected at startup.

```bash
export AKF_CORS_ORIGINS="https://myapp.example.com,https://dashboard.example.com"
```

---

## Endpoints

### `GET /health`

Health check endpoint.

**Request:** None

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "env": "prod"
}
```

**Status:** `200 OK`

---

### `GET /ready`

Readiness check endpoint.

Returns `200` when pipeline and runtime checks are initialized; otherwise `503`.

---

### `GET /metrics`

Built-in JSON metrics endpoint with request counters and average latency.

Includes:
- `requests_total`
- `requests_by_path`
- `status_codes`
- `latency_ms_avg`

---

### `POST /v1/generate`

Generate a single validated Markdown knowledge file.

**Request body:**
```json
{
  "prompt": "Create a guide on API rate limiting"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | `string` | Yes | Natural language prompt |

**Response (200 OK):**
```json
{
  "success": true,
  "content": "---\ntitle: \"API Rate Limiting Strategy\"\n...",
  "file_path": "./vault/API_Rate_Limiting_Strategy.md",
  "errors": [],
  "attempts": 1,
  "generation_id": "a1b2c3d4-..."
}
```

**Response (200 OK — failed after retries):**
```json
{
  "success": false,
  "content": null,
  "file_path": null,
  "errors": [
    {
      "code": "E006",
      "field": "domain",
      "expected": ["api-design", "devops"],
      "received": "backend",
      "severity": "error"
    }
  ],
  "attempts": 3,
  "generation_id": "a1b2c3d4-..."
}
```

**Error responses:**
- `422 Unprocessable Entity` — invalid request body
- `429 Too Many Requests` — rate limit exceeded

**cURL example:**
```bash
curl -X POST http://localhost:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a guide on API rate limiting"}'
```

---

### `POST /v1/ask`

Ask a question over the local RAG index.

Two modes are supported:
- `no_llm=false` (default): retrieval + LLM synthesis
- `no_llm=true`: retrieval-only (no LLM required)

**Request body:**
```json
{
  "query": "How do I implement API rate limiting in FastAPI?",
  "top_k": 5,
  "model": "auto",
  "no_llm": false,
  "max_distance": 0.5
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | `string` | Yes | — | Natural-language question |
| `top_k` | `integer` | No | `5` | Number of retrieved chunks (1..20) |
| `model` | `string` | No | `auto` | LLM provider for synthesis |
| `no_llm` | `boolean` | No | `false` | Retrieval-only mode |
| `max_distance` | `number` | No | `null` | Guardrail: keep chunks with `distance <= max_distance` |

**Response (200 OK — synthesis):**
```json
{
  "mode": "synthesis",
  "query": "How do I implement API rate limiting in FastAPI?",
  "top_k": 5,
  "answer": "Use SlowAPI middleware and return standard rate limit headers.",
  "sources": [
    "tests/fixtures/corpus/API_Rate_Limiting_with_FastAPI.md"
  ],
  "hits_used": 5,
  "hits": [],
  "model": "claude",
  "insufficient_context": false
}
```

**Response (200 OK — retrieval-only):**
```json
{
  "mode": "retrieval-only",
  "query": "How do I implement API rate limiting in FastAPI?",
  "top_k": 5,
  "answer": null,
  "sources": [],
  "hits_used": 2,
  "hits": [
    {
      "chunk_id": "...",
      "content": "## Purpose ...",
      "metadata": {
        "source": "tests/fixtures/corpus/API_Rate_Limiting_with_FastAPI.md",
        "section": "Purpose"
      },
      "distance": 0.1529
    }
  ],
  "model": "none",
  "insufficient_context": false
}
```

**Error responses:**
- `400 Bad Request` — invalid query arguments
- `422 Unprocessable Entity` — invalid payload
- `429 Too Many Requests` — rate limit exceeded
- `500 Internal Server Error` — retrieval/synthesis runtime failure

**cURL examples:**
```bash
# Synthesis mode
curl -X POST http://localhost:8000/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I implement API rate limiting in FastAPI?", "top_k": 5}'

# Retrieval-only mode
curl -X POST http://localhost:8000/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I implement API rate limiting in FastAPI?", "top_k": 5, "no_llm": true}'
```

---

### `POST /v1/enrich`

Add or update YAML frontmatter on a Markdown file provided as a string.

**Request body:**
```json
{
  "content": "# My Note\n\nSome content without frontmatter.",
  "force": false
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `content` | `string` | Yes | — | Raw Markdown content |
| `force` | `boolean` | No | `false` | Regenerate even if frontmatter is already valid |

**Response (200 OK):**
```json
{
  "status": "enriched",
  "content": "---\ntitle: \"My Note\"\ntype: concept\n...\n---\n\n# My Note\n\nSome content.",
  "errors": [],
  "attempts": 1
}
```

**Status values:**

| Status | Meaning |
|--------|---------|
| `"enriched"` | Frontmatter generated and merged |
| `"skipped"` | Already valid and `force` was `false` |
| `"failed"` | Validation failed after max retries |
| `"warning"` | File was empty or could not be processed |

**cURL example:**
```bash
curl -X POST http://localhost:8000/v1/enrich \
  -H "Content-Type: application/json" \
  -d '{"content": "# My Note\n\nContent here."}'
```

---

### `POST /v1/validate`

Validate YAML frontmatter in Markdown content or a file.

**Request body (validate content string):**
```json
{
  "content": "---\ntitle: \"Test\"\ntype: concept\n...\n---\n\n# Test"
}
```

**Request body (validate by file path):**
```json
{
  "file_path": "./vault/my-note.md"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | `string` | One of | Raw Markdown content to validate |
| `file_path` | `string` | One of | Path to a file on the server's filesystem |

**Response (200 OK — valid):**
```json
{
  "is_valid": true,
  "errors": []
}
```

**Response (200 OK — invalid):**
```json
{
  "is_valid": false,
  "errors": [
    {
      "code": "E001",
      "field": "type",
      "expected": ["concept", "guide", "reference", "checklist"],
      "received": "tutorial",
      "severity": "error"
    },
    {
      "code": "E002",
      "field": "tags",
      "expected": "list with >= 3 items",
      "received": null,
      "severity": "error"
    }
  ]
}
```

**cURL example:**
```bash
curl -X POST http://localhost:8000/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"file_path": "./vault/my-note.md"}'
```

---

### `POST /v1/batch`

Generate multiple validated files from a list of prompts.

**Request body:**
```json
{
  "prompts": [
    "Guide on API rate limiting",
    "Concept: database indexing",
    "Security checklist for Docker"
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompts` | `string[]` | Yes | List of prompts to process |

**Response (200 OK):**
```json
{
  "results": [
    {
      "success": true,
      "content": "---\n...",
      "file_path": "./vault/API_Rate_Limiting.md",
      "errors": [],
      "attempts": 1,
      "generation_id": "uuid-1"
    },
    {
      "success": true,
      "content": "---\n...",
      "file_path": "./vault/Database_Indexing.md",
      "errors": [],
      "attempts": 2,
      "generation_id": "uuid-2"
    }
  ]
}
```

**cURL example:**
```bash
curl -X POST http://localhost:8000/v1/batch \
  -H "Content-Type: application/json" \
  -d '{"prompts": ["Guide on rate limiting", "Concept: indexing"]}'
```

---

### `GET /v1/models`

List available LLM providers and their availability status.

**Request:** None

**Response (200 OK):**
```json
{
  "providers": [
    {"name": "groq",   "available": true,  "model": "llama-3.3-70b-versatile"},
    {"name": "claude", "available": true,  "model": "claude-sonnet-4-20250514"},
    {"name": "gemini", "available": false, "model": null},
    {"name": "gpt4",   "available": false, "model": null},
    {"name": "ollama", "available": false, "model": null}
  ]
}
```

---

### `GET /docs`

Interactive Swagger UI for exploring and testing the API.

Navigate to `http://localhost:8000/docs` in a browser.

---

## Error Response Format

All error responses follow this format:

```json
{
  "detail": "Error description"
}
```

| HTTP Status | Meaning |
|-------------|---------|
| `200` | Success (check `success` field in body for generation results) |
| `422` | Invalid request body |
| `429` | Rate limit exceeded |
| `500` | Internal server error |

---

## Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Generate a file
resp = requests.post(f"{BASE_URL}/v1/generate", json={
    "prompt": "Create a guide on API rate limiting"
})
result = resp.json()
print(result["success"], result["file_path"])

# Validate content
resp = requests.post(f"{BASE_URL}/v1/validate", json={
    "content": open("./vault/my-note.md").read()
})
print(resp.json()["is_valid"])

# List providers
resp = requests.get(f"{BASE_URL}/v1/models")
for provider in resp.json()["providers"]:
    status = "✅" if provider["available"] else "❌"
    print(f"{status} {provider['name']}")
```

---

## Related Pages

- [CLI Reference](CLI-Reference) — `akf serve` command
- [MCP Server](MCP-Server) — MCP protocol server
- [Python API](Python-API) — Python SDK
- [Error Codes](Error-Codes) — E001–E008 descriptions
