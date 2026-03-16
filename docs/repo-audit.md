---
title: "AKF Repository Audit"
type: audit
domain: akf-ops
level: advanced
status: active
version: v1.0.1
tags: [audit, quality, coverage, security, ci-cd, documentation, roadmap]
related:
  - "ARCHITECTURE.md"
  - "docs/roadmap.md|references"
created: 2026-03-16
updated: 2026-03-16
---

## Purpose

Comprehensive audit of the `ai-knowledge-filler` repository at v1.0.1. Documents what is working well, open issues, and gaps that inform the project roadmap.

Scope: code quality, test coverage, documentation completeness, CI/CD health, dependency hygiene, security posture.

---

## Repository at a Glance

| Dimension | Status | Notes |
|-----------|--------|-------|
| Version | v1.0.1 | Stable, published on PyPI |
| Python support | 3.10 / 3.11 / 3.12 | Tested in CI matrix |
| Test coverage | 91% | Gate threshold: 85% |
| Test count | 560+ tests | Unit + integration |
| CI workflows | 7 | lint, test, validate, release, changelog, codeql, secret-scan |
| LLM providers | 5 | Claude, Gemini, GPT-4, Groq, Ollama |
| Public interfaces | 3 | CLI, Python SDK, REST API |
| Documentation | Comprehensive | README, ARCHITECTURE, CONTRIBUTING, 5 docs pages, wiki |
| Security baseline | Strong | Pre-commit hooks, SAST, secret scanning |

---

## What Is Working Well

### Core Pipeline

- Deterministic validation gate — only VALID files reach disk.
- Typed error codes E001–E008 with structured `ValidationError` dataclass.
- Convergence protection in `retry_controller.py` — aborts on identical error hash to prevent infinite loops.
- Atomic write via `commit_gate.py` — no partial writes.
- Append-only telemetry JSONL — all pipeline events are observable.

### Test Infrastructure

- 560+ tests across `tests/unit/` and `tests/integration/`.
- 91% coverage; gate at 85% (blocking in CI).
- Fixtures: 47 realistic Markdown documents in `tests/fixtures/corpus/`.
- Coverage artifacts uploaded to Codecov (non-blocking, main branch only).
- Tests run against Python 3.10, 3.11, 3.12 in CI matrix.

### CI/CD

- **ci.yml** — ruff lint + coverage gate, every push/PR to `main`.
- **tests.yml** — multi-version test matrix.
- **validate.yml** — `akf validate --path docs/` on every PR; ensures internal docs comply with schema.
- **release.yml** — automated PyPI publish on git tag.
- **changelog.yml** — git-cliff CHANGELOG generation.
- **codeql.yml** — GitHub CodeQL SAST.
- **secret-scan.yml** — detect-secrets + GitHub secret scanning.

### Documentation

- `README.md` (429 lines) — problem statement, quick start, all interfaces.
- `ARCHITECTURE.md` (360 lines) — public API declaration, pipeline architecture, module map, known issues.
- `CONTRIBUTING.md` (322 lines) — dev setup, quality gates, PR conventions.
- `docs/cli-reference.md` — all commands, flags, exit codes.
- `docs/user-guide.md` — installation, configuration, troubleshooting, MCP quickstart.
- `wiki/` — 12 pages covering installation, REST API, Python API, MCP, FAQ.
- `docs/adr/` — ADR-001 (validation layer), ADR-002 (taxonomy), ADR-004 (identity).

### Security

- `SECURITY.md` defines vulnerability reporting procedure.
- `.pre-commit-config.yaml` includes detect-secrets and format checks.
- SEC-M2 (path traversal in `--output`) fixed in v0.6.2.
- SEC-L2 (`akf init --force` no backup) fixed in v0.6.2.
- SEC-L3 (Windows reserved filenames) fixed in v1.0.0.
- REST API requires `Authorization: Bearer` in `AKF_ENV=prod`.
- Rate limits enforced on all write endpoints.

---

## Open Issues

### Coverage Gaps

| ID | Location | Coverage | Description |
|----|----------|----------|-------------|
| COV-1 | `akf/pipeline.py` | 86% | Batch error paths not covered |
| COV-2 | `akf/validator.py` | 92% | Legacy `taxonomy_path` branch — dead code, not removed |

Both are low severity (gate is 85%) but COV-2 is technical debt.

### Incomplete Features

#### MCP Server (`akf/mcp_server.py`)

- Status: scaffolding exists, integration is incomplete.
- Commands planned: `akf_generate`, `akf_validate`, `akf_enrich`, `akf_batch`.
- Missing: end-to-end integration tests, transport options (`stdio` vs `streamable-http`).
- Documented in `wiki/MCP-Server.md` and README but marked "in progress (v0.6.x)".

#### Canvas Generator (`akf/canvas_generator.py`)

- Status: experimental, present in codebase.
- Not documented in README, ARCHITECTURE, or any public docs.
- No dedicated tests beyond smoke coverage.
- Purpose unclear from code alone — generates visual canvas output.

### Documentation Gaps

| Gap | Location | Severity |
|-----|----------|----------|
| Canvas generator entirely undocumented | `akf/canvas_generator.py` | Medium |
| RAG SPEC.md not linked from README | `rag/SPEC.md` | Low |
| Market pipeline minimal documentation | `docs/market-analysis.md` | Low |
| No REST API CORS configuration examples | `docs/rest-api-threat-model.md` | Low |
| No telemetry JSONL schema documentation | `ARCHITECTURE.md` | Low |
| Dependency lockfile strategy unclear | `requirements.txt` vs `requirements.lock` | Low |

### Dependency Management

- Dual lockfile: `requirements.lock` (pip-freeze, canonical) + `uv.lock` (uv package manager).
- CONTRIBUTING.md states CI uses `pip install -c requirements.lock -e ".[all,dev]"`.
- The role of `requirements.txt` as "thin entrypoint" is documented in README but not in CONTRIBUTING.
- Dependabot is configured but lock update policy is not documented.

### Known Issue: BUG-1

- `akf generate` from repo directory caused `akf/` package to shadow installed package via `sys.path[0]`.
- Fixed in v1.0.0 via `sys.path` guard in `cli.py`.
- No regression test added to prevent reintroduction.

---

## Dependency Audit

All core dependencies are pinned in `requirements.lock`. Key observations:

- `anthropic ≥0.50.0` — updated in v1.0.1 hotfix; recommended LLM provider.
- `pydantic ≥2.0` — modern v2 API used throughout.
- `fastapi` + `uvicorn` — production-grade ASGI stack.
- `slowapi ≥0.1.9` — rate limiting; decorators removed from POST endpoints in v1.0.1 (concurrency fix).
- `chromadb ≥0.5.0` — RAG vector store; optional dependency under `[rag]` extra.
- `sentence-transformers ≥2.7.0` — local embeddings; large install, optional.
- `mcp ≥1.3.0` — MCP server support; optional under `[mcp]` extra.

No known CVEs identified in the dependency set at audit date (2026-03-16).

---

## Quality Gate Summary

| Gate | Status | Tool |
|------|--------|------|
| Lint | ✅ Passing | ruff |
| Format | ✅ Passing | black |
| Type check | ✅ Passing | mypy (selected targets) |
| Tests | ✅ Passing | pytest (Python 3.10–3.12) |
| Coverage ≥85% | ✅ Passing | pytest-cov |
| Metadata validation | ✅ Passing | `akf validate --path docs/` |
| Secret scan | ✅ Passing | detect-secrets + GitHub |
| SAST | ✅ Passing | CodeQL |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| LLM provider API breaking change | Medium | High | Multi-provider router; pin SDK versions |
| Coverage regression below gate | Low | Medium | Blocking CI gate at 85% |
| MCP spec instability (pre-1.0) | Medium | Low | `mcp` is optional extra; version-pinned |
| COV-2 legacy branch masking bug | Low | Low | Tracked in ARCHITECTURE.md Known Issues |
| Canvas generator undocumented scope creep | Low | Medium | Needs design decision: stabilize or remove |

---

## Conclusions

The repository is in a **production-ready state** at v1.0.1 with mature CI/CD, strong test coverage, and comprehensive documentation. The two most actionable items before the next minor release are:

1. **COV-1** — add tests for batch error paths in `pipeline.py` to reach 90%+ coverage on that module.
2. **Canvas generator** — make a decision: document and integrate, or remove. The undocumented surface area creates maintenance overhead.
3. **MCP server** — complete integration and add end-to-end tests before marking stable.

See `docs/roadmap.md` for prioritized next steps.
