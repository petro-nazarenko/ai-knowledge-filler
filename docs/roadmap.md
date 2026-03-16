---
title: "AKF Product Roadmap"
type: roadmap
domain: akf-core
level: intermediate
status: active
version: v1.0
tags: [roadmap, planning, features, releases, mcp, rag, telemetry, coverage]
related:
  - "docs/audit.md"
  - "ARCHITECTURE.md"
  - "CHANGELOG.md"
created: 2026-03-16
updated: 2026-03-16
---

# AKF Product Roadmap

**Baseline:** v1.0.1 — stable pipeline, CLI, Python SDK, REST API, RAG Copilot (Phases 1–3), MCP server (in progress).

This roadmap is derived from the repository audit, open issues, and architectural evolution planned in ADR-001 and ADR-004.

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ Shipped | Already in the codebase |
| 🔨 In progress | Partially implemented |
| 📋 Planned | Scoped, not yet started |
| 💡 Exploratory | Under consideration, not scoped |

---

## v1.1.x — Quality & Stability

**Theme:** Close all known gaps identified in the post-v1.0 audit. No breaking changes.

### Coverage Gaps (COV-1, COV-2)

- 📋 Add tests for `pipeline.py` batch error paths (COV-1) — exercise partial failures in `batch_generate()` to raise coverage above 90% for this file
- 📋 Remove or cover the legacy `taxonomy_path` branch in `validator.py` (COV-2)

### Documentation Gaps (DOC-1, DOC-2)

- 📋 Declare MCP server interface stable in `ARCHITECTURE.md` — add `Interface 4 — MCP` section with tool signatures and breaking-change policy
- 📋 Document telemetry JSONL event schema — define stable `schema_version: "2.0.0"` spec for `GenerationAttemptEvent`, `GenerationSummaryEvent`, `EnrichEvent`, `MarketAnalysisEvent`, `AskQueryEvent`

### Security Hardening (SEC-1, SEC-2)

- 📋 Add max-length validation for `akf ask` question parameter (CLI and `/v1/ask` endpoint)
- 📋 Document RAG corpus content trust boundary — clarify what corpus sanitization guarantees are made before content is injected into LLM context

### MCP Interface Stabilization

- 🔨 Complete MCP server implementation (`akf serve --mcp`)
- 📋 Add MCP integration tests — mirror REST API test coverage for `akf_generate`, `akf_validate`, `akf_enrich`, `akf_batch`
- 📋 Publish MCP server docs in `docs/mcp-reference.md`

---

## v1.2.x — RAG & Search Enhancements

**Theme:** Promote RAG Copilot from internal tooling to a first-class interface. No breaking changes.

### RAG CLI Integration

- 📋 Promote `akf ask` and `akf index` to stable CLI commands — add to ARCHITECTURE.md as part of Interface 1
- 📋 Add `--corpus` flag to `akf generate` to make RAG context injection explicit and configurable
- 📋 Add `akf search "<query>"` as an alias for pure retrieval (no synthesis) — wraps `rag/retriever.py`

### RAG REST API

- 📋 Document `/v1/ask` as a stable REST endpoint in ARCHITECTURE.md (currently implemented but not in the public API declaration)
- 📋 Add tenant-level ask rate limiting enforcement (currently tracked but not enforced at middleware level)

### Corpus Management

- 📋 Add `akf corpus add <path>` — incremental indexing without full re-index
- 📋 Add `akf corpus status` — show collection stats (file count, chunk count, last indexed)
- 💡 Support remote corpus sources (S3, GitHub, Confluence) via pluggable corpus adapters

### Embedding Model Flexibility

- 📋 Make embedding model configurable in `akf.yaml` (currently hardcoded to `sentence-transformers/all-MiniLM-L6-v2`)
- 💡 Support OpenAI embeddings as an alternative backend for teams already using GPT-4

---

## v1.3.x — Telemetry & Observability

**Theme:** Surface ontology friction and pipeline health in a usable format. No breaking changes.

### Telemetry Schema Stabilization

- 📋 Declare telemetry JSONL `schema_version: "2.0.0"` stable — freeze event shapes for `GenerationAttemptEvent`, `GenerationSummaryEvent`, `EnrichEvent`
- 📋 Add schema migration utility for consumers upgrading from pre-2.0.0 logs

### Analytics Commands

- 📋 Add `akf telemetry summary` CLI command — wraps `Scripts/analyze_telemetry.py` as a first-class subcommand
- 📋 Add `akf telemetry friction` — show top-N enum values causing the most retries (ontology friction report)
- 💡 Add `akf telemetry export --format csv|json` for integration with external dashboards

### Observability Integration

- 💡 OpenTelemetry span export from `pipeline.py` — plug into Grafana / Datadog / Jaeger
- 💡 Prometheus metrics endpoint at `/metrics` (auth-gated) — expose retry rate, success rate, latency histograms

---

## v2.0.0 — Multi-Schema & Breaking Change Window

**Theme:** Architectural evolution that could not be done without breaking changes. Requires MAJOR version bump.

### Schema Evolution

- 💡 Support multiple schema versions in parallel — allow `schema_version: "1.0.0"` and `"2.0.0"` configs to coexist in the same vault
- 💡 Add `akf migrate --schema 2.0.0` command to upgrade existing `.md` files when the config schema advances

### Multi-Vault Support

- 💡 Support multiple vault paths in `akf.yaml` (e.g., `vault_paths: [./docs, ./wiki]`) — currently only one `vault_path` is supported
- 💡 Per-vault taxonomy overrides — allow different enum sets per vault

### Plugin System

- 💡 `ValidationError` plugin interface — allow custom E-codes from external packages without forking the validator
- 💡 LLM provider plugin interface — register custom providers without modifying `llm_providers.py`

### Breaking Changes Planned

If any of the following issues require breaking changes, they are deferred to v2.0.0:

- Rename or restructure `ValidationError` fields for improved ergonomics
- Change `akf.yaml` top-level key structure (e.g., flatten `taxonomy.domains` → `domains`)
- Change HTTP response field names in REST API for consistency

---

## Backlog (Unscheduled)

These items have been raised but are not yet scheduled for a specific release.

| Item | Category | Notes |
|------|----------|-------|
| `akf generate --dry-run` | CLI | Preview prompt + estimated output without LLM call |
| `akf validate --fix` | CLI | Auto-fix E001/E003/E004 errors in place (safe subset only) |
| Streaming response for `/v1/generate` | REST API | Return chunks as they are validated |
| Web UI (read-only vault browser) | UX | Serve vault contents as a browsable site |
| GitHub Action — `akf-validate` | CI/CD | Official action for validating docs in any GitHub repo |
| PyPI extras audit | Packaging | Review `[mcp]`, `[rag]`, `[all]` extras for dependency bloat |
| Windows path handling audit | Platform | Verify `sanitize_filename` on Windows reserved names edge cases |
| Grok provider parity | LLM | Ensure Grok/xAI provider has same retry and telemetry coverage as Claude/Gemini |

---

## Constraints

- **No breaking changes before v2.0.0** — all v1.x releases must be backward compatible with CLI, Python SDK, REST API, and `ValidationError` contract.
- **Test coverage gate stays at ≥88%** (CI enforced) — new features must ship with tests.
- **Locked dependencies** — `requirements.lock` must be updated on every dependency addition.
- **MCP not declared stable** until Interface 4 documentation is merged into `ARCHITECTURE.md`.
