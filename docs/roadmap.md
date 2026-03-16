---
title: "AKF Development Roadmap"
type: roadmap
domain: akf-ops
level: intermediate
status: active
version: v1.0.1
tags: [roadmap, planning, milestones, features, releases]
related:
  - "docs/repo-audit.md|references"
  - "ARCHITECTURE.md"
  - "CHANGELOG.md"
created: 2026-03-16
updated: 2026-03-16
---

## Purpose

Forward-looking development plan for `ai-knowledge-filler` based on the v1.0.1 repository audit. Organized by release milestones with clear scope, rationale, and acceptance criteria for each item.

Roadmap is derived from open issues in `ARCHITECTURE.md`, gaps identified in `docs/repo-audit.md`, and feature backlog in the codebase.

---

## Guiding Principles

1. **Stability first** — no breaking changes to public API (CLI, Python SDK, REST) without a MAJOR version increment.
2. **Coverage gate is a floor, not a ceiling** — keep coverage above 90% in actively developed modules.
3. **All public interfaces must be documented** — no experimental surface area in production-facing code without a spec.
4. **Determinism boundary is inviolable** — the validation/retry/commit pipeline must remain pure and fully testable.

---

## v1.2.0 — Coverage and Stability (Short-term)

**Theme:** Close open quality gaps from the v1.0.1 audit. No new features.

### COV-1: Batch Error Path Coverage in `pipeline.py`

- **Issue:** `pipeline.py` is at 86% coverage; batch error paths (partial failures, mixed success/failure in `batch_generate`) are not covered.
- **Action:** Add unit tests covering:
  - `batch_generate()` where one prompt succeeds and one fails.
  - `batch_generate()` where all prompts fail validation after max retries.
  - `batch_generate()` with empty prompt list.
- **Target:** `pipeline.py` coverage ≥ 90%.
- **Acceptance criteria:** `pytest --cov=akf/pipeline.py --cov-fail-under=90` passes.

### COV-2: Remove Legacy `taxonomy_path` Branch in `validator.py`

- **Issue:** `validator.py` contains a legacy `taxonomy_path` code path that is no longer reachable via any public interface. This is dead code that inflates the uncovered-branch metric.
- **Action:** Audit the branch. If unreachable, remove it and the associated test scaffolding. If reachable via an undocumented path, document it.
- **Target:** Remove dead code; validator coverage ≥ 95%.
- **Acceptance criteria:** No skipped or no-op test branches related to `taxonomy_path` remain.

### BUG-1 Regression Test

- **Issue:** BUG-1 (sys.path shadowing) was fixed in v1.0.0 but no regression test was added.
- **Action:** Add an integration test that verifies `akf generate` works correctly when invoked from the repo root directory (simulating the original bug condition).
- **Acceptance criteria:** Test is in `tests/integration/` and passes on all CI Python versions.

---

## v1.3.0 — MCP Server Completion (Medium-term)

**Theme:** Bring the MCP server from "in progress" to a stable, tested, documented interface.

### MCP Server Integration

- **Current state:** `akf/mcp_server.py` scaffolding exists; not fully integrated or tested.
- **Actions:**
  - Complete tool implementations: `akf_generate`, `akf_validate`, `akf_enrich`, `akf_batch`.
  - Add end-to-end integration tests using `mcp` test client or mock transport.
  - Verify `stdio` transport (local clients: Claude Desktop, Cursor, Zed).
  - Verify `streamable-http` transport (remote deployments).
  - Add error handling for tool invocation failures (invalid prompt, LLM unavailable, validation timeout).
- **Acceptance criteria:**
  - All four MCP tools covered by integration tests.
  - `akf serve --mcp` starts without error in CI.
  - `wiki/MCP-Server.md` updated to reflect stable status.
  - README MCP section no longer marked "in progress".

### MCP Server Documentation

- Add spec document `docs/mcp-server-spec.md` (type: reference, domain: akf-core) covering:
  - Transport options (`stdio` vs `streamable-http`).
  - Tool contracts (input/output schemas).
  - Error codes returned by MCP tools.
  - Client configuration examples for Claude Desktop, Cursor, Zed.
- Update `ARCHITECTURE.md` — add MCP to the public API declaration (Interface 4).

---

## v1.4.0 — Canvas Generator Decision (Medium-term)

**Theme:** Resolve the undocumented canvas generator surface area.

### Decision Gate: Stabilize or Remove `canvas_generator.py`

Two options:

**Option A — Stabilize:**
- Write a spec (`docs/canvas-spec.md`) describing input format, output format, and use cases.
- Add full test coverage (unit + integration).
- Expose via CLI as `akf canvas <path>` and REST API as `POST /v1/canvas`.
- Document in README and ARCHITECTURE.

**Option B — Remove:**
- Delete `akf/canvas_generator.py` and any dependent imports.
- Document removal in CHANGELOG as a MINOR deprecation notice (no public interface was declared).
- Add a brief note in ARCHITECTURE.md "Not Implemented" section.

**Acceptance criteria:** Either a documented, tested, stable `akf canvas` command — or the file is removed with a CHANGELOG entry.

---

## v1.5.0 — RAG Enhancements (Medium-term)

**Theme:** Polish and extend the RAG copilot based on real-world usage feedback.

### Auto-reindex on File Changes

- **Feature:** Detect when corpus files are added, modified, or deleted and trigger re-indexing automatically.
- **Implementation:** File system watcher (e.g., `watchdog`) as optional dependency; activated by `akf index --watch`.
- **Acceptance criteria:** Adding a new Markdown file to the corpus directory triggers incremental indexing without a full rebuild.

### RAG SPEC Integration

- **Gap:** `rag/SPEC.md` is a detailed design document but is not linked from the main README RAG section.
- **Action:** Add link from README RAG section to `rag/SPEC.md`. Update SPEC.md frontmatter to comply with AKF schema.
- **Acceptance criteria:** `akf validate rag/SPEC.md` passes.

### Query History for Learning

- **Feature:** Log RAG queries to the telemetry JSONL stream with associated top-k chunk IDs and user feedback signals.
- **Use case:** Identify which queries repeatedly return low-quality results (no useful chunks found), driving corpus improvement.
- **Implementation:** Extend `AskQueryEvent` in `akf/telemetry.py` with `retrieved_chunk_ids` and `result_quality` fields.
- **Acceptance criteria:** `akf ask` queries appear in `telemetry.jsonl` with chunk IDs and distance scores.

---

## v2.0.0 — Next Generation Features (Long-term)

**Theme:** Major capabilities that extend the product beyond its current scope.

> Items here are aspirational and subject to revision. No committed timeline.

### Multilingual Search

- Extend RAG indexer to support non-English corpora.
- Switch embedding model to multilingual variant (e.g., `paraphrase-multilingual-MiniLM-L12-v2`).
- Add language detection in `rag/indexer.py`.

### Web UI for RAG Copilot

- Lightweight web interface for querying the RAG copilot without using the CLI.
- Stack: minimal HTML/JS single-page app served by FastAPI static files.
- Out of scope: authentication, multi-user, hosted deployment.

### Telemetry Schema Stabilization

- Declare `telemetry_schema_version: "2.0.0"` in telemetry events.
- Publish telemetry JSONL schema documentation in ARCHITECTURE.md.
- Provide `Scripts/analyze_telemetry.py` as a stable, documented analysis tool.

### Plugin Architecture for Validators

- Allow custom validation rules beyond E001–E008 via a plugin interface.
- Enables teams to enforce project-specific frontmatter policies without forking.

---

## Backlog (Unscheduled)

These items are identified but not yet assigned to a milestone:

| Item | Source | Priority |
|------|--------|----------|
| REST API CORS configuration examples in docs | Audit GAP | Low |
| Clarify requirements.txt vs requirements.lock in CONTRIBUTING | Audit GAP | Low |
| Mypy coverage expanded to `rag/` module | Code quality | Medium |
| ADR for canvas generator decision | Architecture | Medium |
| Dependabot lock update policy documentation | Ops | Low |
| `akf models` command extended with health check | UX | Low |

---

## Release Cadence

| Release | Theme | Target |
|---------|-------|--------|
| v1.2.0 | Coverage and stability | ~Q2 2026 |
| v1.3.0 | MCP server stable | ~Q2 2026 |
| v1.4.0 | Canvas generator decision | ~Q3 2026 |
| v1.5.0 | RAG enhancements | ~Q3 2026 |
| v2.0.0 | Next generation | ~Q4 2026 |

Patch releases (v1.x.y) are issued as needed for bug fixes and security patches, independent of this schedule.

---

## How to Contribute to Roadmap Items

Each roadmap item maps to a GitHub issue. To work on an item:

1. Check the issue tracker for the corresponding issue.
2. Read the acceptance criteria in this document.
3. Follow the contribution workflow in `CONTRIBUTING.md`.
4. Add or update tests before opening a PR.
5. Ensure `akf validate --path docs/` passes after documentation changes.
