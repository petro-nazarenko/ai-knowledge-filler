---
title: "AKF Repository Audit"
type: audit
domain: akf-core
level: intermediate
status: active
version: v1.0
tags: [audit, architecture, coverage, security, ci-cd, documentation, open-issues]
related:
  - "ARCHITECTURE.md"
  - "docs/roadmap.md"
  - "CHANGELOG.md"
  - "CONTRIBUTING.md"
created: 2026-03-16
updated: 2026-03-16
---

# AKF Repository Audit

**Scope:** `ai-knowledge-filler` · v1.0.1 · Full-repo audit covering architecture, code quality, test coverage, security, documentation, and CI/CD.

---

## Executive Summary

The project is in a stable, production-ready state. The core pipeline is fully implemented and well-tested. Three public interfaces are declared and versioned (CLI, Python SDK, REST API). Security posture is sound. Documentation is comprehensive. Two low-severity coverage gaps remain open. The MCP server interface is partially implemented and not yet declared stable.

---

## Architecture Assessment

### Implemented Modules

| Module | Purpose | Status |
|--------|---------|--------|
| `akf/pipeline.py` | Orchestrates generate / enrich / validate / batch | ✅ Stable |
| `akf/validator.py` | Binary VALID/INVALID + E001–E008 typed errors | ✅ Stable |
| `akf/validation_error.py` | `ValidationError` dataclass + error constructors | ✅ Stable |
| `akf/error_normalizer.py` | `ValidationError[]` → deterministic LLM repair instructions | ✅ Stable |
| `akf/retry_controller.py` | `run_retry_loop()` — convergence protection, max 3 attempts | ✅ Stable |
| `akf/commit_gate.py` | Atomic write — only VALID output reaches disk | ✅ Stable |
| `akf/telemetry.py` | Append-only JSONL event stream (GenerationEvent, EnrichEvent, AskQueryEvent, MarketAnalysisEvent) | ✅ Stable |
| `akf/config.py` | `get_config()` — loads `akf.yaml` or bundled defaults | ✅ Stable |
| `akf/enricher.py` | Reads existing Markdown, builds merge prompt, drives enrich pipeline | ✅ Stable |
| `akf/server.py` | FastAPI REST API — `/v1/generate`, `/v1/validate`, `/v1/batch`, `/v1/enrich`, `/v1/ask` | ✅ Stable |
| `akf/mcp_server.py` | MCP server (FastMCP) — `akf_generate`, `akf_validate`, `akf_enrich`, `akf_batch` | ⚠️ In progress |
| `akf/market_pipeline.py` | Three-stage market analysis pipeline (market → competitors → positioning) | ✅ Stable |
| `akf/canvas_generator.py` | Obsidian Canvas file generation | ✅ Stable |
| `rag/indexer.py` | Phase 1 — Chroma corpus indexer | ✅ Stable |
| `rag/retriever.py` | Phase 2 — Semantic query layer over Chroma index | ✅ Stable |
| `rag/copilot.py` | Phase 3 — Retrieval + synthesis, grounded answers from corpus | ✅ Stable |
| `cli.py` | Entry point — command routing and argument parsing | ✅ Stable |
| `llm_providers.py` | Provider router — Claude / Gemini / GPT-4 / Groq / Grok / Ollama | ✅ Stable |
| `exceptions.py` | Typed exception hierarchy | ✅ Stable |
| `logger.py` | Logging factory (human + JSON modes) | ✅ Stable |

### Determinism Boundary

| Component | Deterministic | Note |
|-----------|--------------|------|
| LLM | ❌ | Sole non-deterministic element by design |
| Validation Engine | ✅ | Pure function |
| Error Normalizer | ✅ | Fixed templates per E-code |
| Retry Controller | ✅ | Convergence via error-hash comparison |
| Commit Gate | ✅ | Atomic write via temp-file rename |
| Telemetry Writer | ✅ | Append-only, no feedback loop |

The determinism boundary is correctly enforced: all non-LLM components are pure functions and independently testable.

### Dependency Injection

All feature modules (`Pipeline`, `MarketAnalysisPipeline`) follow a consistent optional-injection pattern for `TelemetryWriter` and `AKFConfig`. This enables test isolation without mocking singletons. The pattern is correctly documented in `ARCHITECTURE.md`.

---

## Public Interfaces

Three interfaces are declared stable and covered by the semver breaking-change policy documented in `ARCHITECTURE.md`.

| Interface | Status | Breaking-change guard |
|-----------|--------|-----------------------|
| CLI (`akf <command>`) | ✅ Stable | MAJOR required to remove/rename commands |
| Python SDK (`from akf import Pipeline`) | ✅ Stable | MAJOR required to remove/rename methods or fields |
| REST API (`/v1/*`) | ✅ Stable | MAJOR required to remove/rename endpoints or response fields |
| MCP (`akf serve --mcp`) | ⚠️ In progress | Not yet declared stable |

### Contracts

| Contract | Status |
|----------|--------|
| `ValidationError` (E001–E008) | ✅ Stable |
| `akf.yaml` config schema (`schema_version: "1.0.0"`) | ✅ Stable |
| Telemetry JSONL schema | ⚠️ Not yet stable (noted in ARCHITECTURE.md) |

---

## Code Coverage

**Overall:** 91% (560+ tests) — CI enforced.

| Module | Coverage | Open Gap |
|--------|----------|----------|
| `pipeline.py` | 86% | COV-1: batch error paths not covered |
| `validator.py` | 92% | COV-2: legacy `taxonomy_path` branch not covered |
| All other modules | ≥92% | No open gaps |

**COV-1** (Medium): The `batch_generate()` error-handling paths inside `pipeline.py` are not exercised by tests. A partial LLM failure during batch processing may mask silent data loss.

**COV-2** (Low): A legacy `taxonomy_path` branch in `validator.py` is unreachable via the current public API but remains in the codebase.

---

## Security Assessment

### Resolved Issues

| ID | Description | Severity | Fixed In |
|----|-------------|----------|----------|
| BUG-1 | `akf generate` from repo directory used local `akf/` instead of installed package | Medium | v1.0.0 |
| SEC-M2 | `--output` path traversal not sanitized in `sanitize_filename` | Medium | v0.6.2 |
| SEC-L2 | `akf init --force` performed no backup before overwrite | Low | v0.6.2 |
| SEC-L3 | Windows reserved filename check missing in commit gate | Low | v1.0.0 |

### Current Posture

| Control | Status |
|---------|--------|
| Auth (`AKF_API_KEY`) required in `AKF_ENV=prod` | ✅ Enforced (startup fails without key) |
| Rate limits on POST endpoints | ✅ 10/min generate · 30/min validate · 3/min batch |
| Path traversal protection | ✅ Fixed (v0.6.2) |
| `/v1/metrics` requires auth | ✅ Enforced (v1.0.1) |
| Prompt injection via `--output` | ✅ Sanitized |
| Secret scanning in CI | ✅ `secret-scan.yml` workflow active |
| Dependency pinning | ✅ `requirements.lock` + `uv.lock` |
| Supply chain: GitHub Actions pinned to SHA | ✅ Enforced in `ci.yml` |
| RAG corpus input sanitization | ⚠️ No explicit guardrails on corpus content used in LLM context |
| `akf ask` input length not bounded | ⚠️ No max-length check on question parameter |

---

## Documentation Coverage

| Document | Location | Status |
|----------|----------|--------|
| README | `README.md` | ✅ Comprehensive |
| Architecture | `ARCHITECTURE.md` | ✅ Comprehensive — public API, module map, DI convention |
| CLI Reference | `docs/cli-reference.md` | ✅ All commands, flags, exit codes |
| User Guide | `docs/user-guide.md` | ✅ Install, config, troubleshooting |
| REST API Threat Model | `docs/rest-api-threat-model.md` | ✅ Auth, rate limits, logging/PII |
| Contributing | `CONTRIBUTING.md` | ✅ Dev setup, quality gates, provider guide |
| CHANGELOG | `CHANGELOG.md` | ✅ Machine-generated via git-cliff |
| ADR-001 | `docs/adr/ADR-001_Validation_Layer_Architecture.md` | ✅ Active |
| ADR-002 | `docs/adr/ADR-002_Vault_Taxonomy_vs_Repo_Taxonomy.md` | ✅ Active |
| ADR-004 | `docs/adr/ADR-004_Identity_Content_Production_System.md` | ✅ Active |
| Wiki | `wiki/` (16 pages) | ✅ Mirrors key docs |
| RAG Copilot phases | `README.md` §RAG | ✅ Phases 1–3 documented |
| Market analysis pipeline | `docs/market-analysis.md` | ✅ Present |
| Roadmap | `docs/roadmap.md` | ✅ See linked document |
| MCP server public API | Not declared | ⚠️ Missing — MCP interface not yet in ARCHITECTURE.md as stable |
| Telemetry JSONL schema | Not documented | ⚠️ Missing — referenced as "not yet stable" but no schema spec exists |

---

## CI/CD Assessment

| Workflow | File | Purpose | Status |
|----------|------|---------|--------|
| CI | `.github/workflows/ci.yml` | Lint (ruff, black, mypy) on PR for changed Python files | ✅ Active |
| Tests | `.github/workflows/tests.yml` | pytest 3.10/3.11/3.12, coverage gate ≥88% | ✅ Active |
| Validate | `.github/workflows/validate.yml` | `akf validate --path docs/` on docs changes | ✅ Active |
| Changelog | `.github/workflows/changelog.yml` | git-cliff on push to main | ✅ Active |
| Release | `.github/workflows/release.yml` | PyPI publish on tag push | ✅ Active |
| Secret Scan | `.github/workflows/secret-scan.yml` | Credential leak detection | ✅ Active |

**CI is green on Python 3.10 / 3.11 / 3.12.** All workflows are using pinned action SHAs. Locked dependency constraints enforced via `pip install -c requirements.lock`.

---

## Open Issues

| ID | Description | Severity | Status |
|----|-------------|----------|--------|
| COV-1 | `pipeline.py` 86% — batch error paths uncovered | Low | Open |
| COV-2 | `validator.py` 92% — legacy `taxonomy_path` branch | Low | Open |
| DOC-1 | MCP server interface not declared in public API docs | Low | Open |
| DOC-2 | Telemetry JSONL schema not documented | Low | Open |
| SEC-1 | RAG corpus content used in LLM context without explicit sanitization guardrails | Low | Open |
| SEC-2 | `akf ask` question parameter has no max-length enforcement | Low | Open |

---

## Findings Summary

| Area | Rating | Notes |
|------|--------|-------|
| Architecture | ✅ Excellent | Clean determinism boundary, consistent DI, atomic writes |
| Code coverage | ✅ Good | 91% overall; two low-severity gaps open (COV-1, COV-2) |
| Security | ✅ Good | All medium/high issues resolved; two low-severity items open |
| Documentation | ✅ Good | Comprehensive across all public interfaces; MCP and telemetry schema gaps |
| CI/CD | ✅ Excellent | Multi-version matrix, locked deps, secret scanning, changelog automation |
| Public API | ✅ Stable | Three interfaces + two contracts declared with semver policy |
| MCP interface | ⚠️ Partial | Implemented but not declared stable; not in versioned API docs |
| Telemetry | ⚠️ Partial | Functional; schema not yet declared stable or documented |
