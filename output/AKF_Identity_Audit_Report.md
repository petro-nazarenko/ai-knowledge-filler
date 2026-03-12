---
title: "AKF Identity Audit Report"
type: audit
domain: ai-system
level: advanced
status: active
tags: [audit, identity, cli, rag, telemetry, positioning]
created: 2026-03-12
updated: 2026-03-12
---

# AKF Identity Audit — AI-Powered Knowledge Production System

**Package:** `ai-knowledge-filler` v1.0.0
**Branch:** `claude/audit-akf-identity-QdjxR`
**Date:** 2026-03-12

---

### Task 1 — CLI completeness

**Status:** ⚠️ partial
**Finding:** All 9 declared subcommands are fully wired; the `rag/indexer` has no CLI subcommand, making `akf index` impossible from the shell.

**Subcommands present:**

| Command | Handler | Module wired |
|---|---|---|
| `init` | `cmd_init` | `akf.defaults/akf.yaml` ✅ |
| `generate` | `cmd_generate` (+ `--batch`) | `akf.pipeline.Pipeline` ✅ |
| `validate` | `cmd_validate` | `akf.validator` ✅ |
| `enrich` | `cmd_enrich` | `akf.pipeline.Pipeline.enrich` ✅ |
| `models` | `cmd_models` | `llm_providers` ✅ |
| `ask` | `cmd_ask` | `rag.copilot`, `rag.retriever` ✅ |
| `canvas` | `cmd_canvas` | `akf.canvas_generator` ✅ |
| `market-analysis` | `cmd_market_analysis` | `akf.market_pipeline` ✅ |
| `serve` | `cmd_serve` | `akf.server` (REST) / `akf.mcp_server` (MCP) ✅ |

**Missing:** No `akf index` subcommand. `rag/indexer.py` exposes `index_corpus()` and a `__main__` entry point but is never wired into `cli.py`. Users must run `python rag/indexer.py` directly.

```python
# cli.py — there is no branch for "index"
elif args.command == "ask":
    cmd_ask(args)
elif args.command == "canvas":
    cmd_canvas(args)
# ← "index" is missing
```

---

### Task 2 — RAG integration

**Status:** ❌ broken
**Finding:** `akf/pipeline.py`'s `generate()` method never calls `rag/retriever.py`; corpus context is not injected before the LLM call.

**Relevant code path (`akf/pipeline.py` lines 107–121):**

```python
system_prompt = self._load_system_prompt()
# ← No retrieve() call here
if hints:
    context_lines = []
    if hints.get("domain"):
        context_lines.append(f"domain: {hints['domain']}")
    ...
content = provider.generate(prompt, system_prompt)
```

The only context injected is `domain`/`type` hints from a batch plan dict. There is no call to `rag.retriever.retrieve()`, no `RetrievalResult`, and no corpus chunks appended to the prompt or system prompt. `rag/copilot.py` implements RAG-augmented synthesis, but it is only reachable via `akf ask`, not `akf generate`.

---

### Task 3 — `akf ask` end-to-end

**Status:** ✅ aligned
**Finding:** `akf ask` is fully implemented end-to-end: CLI → retriever → LLM → formatted output.

**Full code path:**

```
cli.py:cmd_ask()
  └─ rag.copilot.answer_question(query, top_k, model)   [copilot.py:78]
       ├─ rag.retriever.retrieve(query, top_k)           [retriever.py:52]
       │    └─ chromadb PersistentClient.query()
       ├─ _filter_hits_by_distance(hits, max_distance)
       ├─ llm_providers.get_provider(model)
       └─ provider.generate(user_prompt, _SYSTEM_PROMPT) → CopilotAnswer
  └─ print result.answer + result.sources
```

`--no-llm` flag triggers retrieval-only mode (skips synthesis). Both paths are implemented and tested (`tests/test_cli_ask.py`, `tests/unit/test_rag_copilot.py`).

---

### Task 4 — market_pipeline validation

**Status:** ❌ broken
**Finding:** `MarketAnalysisPipeline` never calls `akf/validator.py`; all three stage outputs are written to disk without schema validation.

**Evidence (`akf/market_pipeline.py` lines 275–295):**

```python
def analyze_market(self, request: str) -> StageResult:
    prompt = _MARKET_ANALYSIS_PROMPT.format(request=request)
    content = self._call_llm(prompt)
    fp = self._write(content, self._safe_filename("analysis", request))   # ← direct write
    return StageResult(success=True, content=content, file_path=fp, ...)
```

No `validate()` call appears anywhere in `market_pipeline.py`. The market pipeline has its own hardcoded `_SYSTEM_PROMPT` that includes a YAML frontmatter template, but whether the LLM output passes the E001–E007 contract is never checked. Files land on disk regardless of schema validity.

---

### Task 5 — Module wiring

**Status:** ⚠️ partial
**Finding:** All production modules share `llm_providers.py`; RAG uses an independent config system; `canvas_generator.py` uses no LLM at all; `market_pipeline.py` has a hardcoded domain bypassing `akf/config.py`.

| Module | `llm_providers.py` | `akf/config.py` |
|---|---|---|
| `akf/pipeline.py` | ✅ `get_provider()` | ✅ `get_config()` in `enrich()` |
| `akf/enricher.py` | ✅ via `pipeline.enrich()` | ✅ `get_config()` |
| `akf/market_pipeline.py` | ✅ `get_provider()` | ❌ hardcodes `domain: business-strategy` |
| `akf/canvas_generator.py` | ❌ no LLM (static transform) | ❌ not needed (reads YAML directly) |
| `rag/copilot.py` | ✅ `get_provider()` | ❌ uses `rag/config.py` (env-vars only) |
| `rag/indexer.py` | ❌ no LLM | ❌ uses `rag/config.py` |
| `rag/retriever.py` | ❌ no LLM | ❌ uses `rag/config.py` |
| `akf/mcp_server.py` | ✅ (via Pipeline) | ✅ (via Pipeline) |

`rag/config.py` is env-var based (`RAG_CORPUS_DIR`, `RAG_CHROMA_PATH`) and completely independent of `akf/config.py`. There is no cross-link between the taxonomy/domain config and the RAG layer.

---

### Task 6 — Telemetry coverage

**Status:** ⚠️ partial
**Finding:** Four event types are defined; `generate` and `validate-retry` stages are fully covered; `enrich` telemetry has a silent bug; `market-analysis`, `canvas`, and CLI `ask` emit zero events.

| Stage | Event type | Coverage |
|---|---|---|
| Each retry attempt | `GenerationAttemptEvent` | ✅ `retry_controller.py` |
| Generation session end | `GenerationSummaryEvent` | ✅ `commit_gate.py` |
| File enrich (CLI) | `EnrichEvent` | ❌ **bug**: `Pipeline.writer` is always `None`; the `if not dry_run and self.writer is not None` guard silently drops every event |
| REST API `ask` | `AskQueryEvent` | ✅ `akf/server.py` |
| CLI `ask` | `AskQueryEvent` | ❌ `cmd_ask` never creates a `TelemetryWriter` |
| `market-analysis` (all stages) | — | ❌ no telemetry |
| `canvas` | — | ❌ no telemetry |

**Root cause of enrich telemetry bug (`akf/pipeline.py` line 54):**

```python
class Pipeline:
    def __init__(self, output=None, model="auto", telemetry_path=None, verbose=True):
        ...
        self.writer = None   # ← never assigned; telemetry_path is stored but ignored
```

`telemetry_path` is stored as `self.telemetry_path` but never used to construct a `TelemetryWriter`. Every `EnrichEvent` is silently dropped.

---

### Task 7 — Test coverage

**Status:** ✅ aligned
**Finding:** All major modules have dedicated test files; only the missing `akf index` CLI command has no test.

**Covered:**

| Module | Test file(s) |
|---|---|
| `rag/indexer.py` | `tests/unit/test_rag_indexer.py` |
| `rag/retriever.py` | `tests/unit/test_rag_retriever.py` |
| `rag/copilot.py` | `tests/unit/test_rag_copilot.py` |
| `akf/canvas_generator.py` | `tests/test_canvas_generator.py` |
| `akf/market_pipeline.py` | `tests/test_market_pipeline.py` |
| `akf/enricher.py` | `tests/unit/test_enricher.py`, `tests/unit/test_pipeline_enrich.py` |
| CLI `ask` | `tests/test_cli_ask.py` |

**Not covered:**

| Gap | Reason |
|---|---|
| `akf index` CLI | Subcommand does not exist |
| `market_pipeline` + validator integration | No test verifies that market outputs fail E001–E007 |
| `EnrichEvent` telemetry emission | Bug makes it untestable via current `Pipeline` API |

---

### Task 8 — Positioning contradiction

**Status:** ❌ broken
**Finding:** Three separate artifacts declare the product as a "validation pipeline", directly contradicting "AI-powered knowledge production system".

| File | Line | Text |
|---|---|---|
| `pyproject.toml` | 4 | `"Schema validation pipeline for LLM-generated structured Markdown. CLI · Python API · REST API."` |
| `README.md` | 3 | `"Validation pipeline that prevents AI-generated files from reaching disk unless they pass schema checks"` |
| `docs/user-guide.md` | 19 | `"AKF is a **validation pipeline** — not a note-taking app."` |

The PyPI package description is the most damaging: it is the first string indexed by pip and shown on pypi.org. The actual surface area of the system — RAG indexing, multi-LLM generation, market research, Obsidian canvas export, MCP server — is not reflected anywhere in the public-facing description.

---

### Task 9 — Full loop feasibility

**Status:** ⚠️ partial
**Finding:** 4 of 5 steps in the ideal loop work; `akf index` is missing from the CLI, breaking the full round-trip.

```
corpus → akf index → akf ask → akf generate → akf validate → akf canvas
```

| Step | Command | Status | Notes |
|---|---|---|---|
| `corpus` | (existing files) | ✅ | `tests/fixtures/corpus/` has 46 docs |
| `akf index` | — | ❌ | No CLI subcommand; requires `python rag/indexer.py` |
| `akf ask` | `akf ask "..."` | ✅ | Fully implemented |
| `akf generate` | `akf generate "..."` | ✅ | Works, but ignores RAG context (Task 2) |
| `akf validate` | `akf validate --path ./output` | ✅ | Full E001–E007 enforcement |
| `akf canvas` | `akf canvas -i ./output -o vault.canvas` | ✅ | Fully implemented |

The missing `akf index` subcommand means the corpus → RAG loop cannot be driven end-to-end from the CLI without dropping into `python rag/indexer.py`, breaking the "one tool" UX.

---

### Task 10 — generate bug

**Status:** ❌ broken
**Finding:** `akf generate` can return verbatim content from the `COMPLETE EXAMPLES` section of `system_prompt.md` because the examples are embedded as literal Markdown files inside the system prompt with no guard against reproduction.

**Root cause:**

`akf/system_prompt.md` contains a `## COMPLETE EXAMPLES` section (lines 246–627) with four fully-formed knowledge files (Microservices Architecture, Docker Multi-Stage Builds, API Security Checklist, Metadata Template Standard). The system prompt instructs the LLM:

```
- ❌ No text before or after Markdown
- ✅ Output only in Markdown
- ✅ One response = one or several completed files
```

For vague or topically overlapping prompts — especially with smaller or less instruction-following models (Ollama, Groq) — the LLM interprets the example files as valid output candidates and reproduces one verbatim, satisfying the "output only Markdown" rule with no validation error (the examples are already schema-valid).

**Minimal fix:**

Add one explicit negative instruction to `system_prompt.md` immediately before the examples section:

```markdown
## IMPORTANT — EXAMPLE USAGE

The files below are FORMAT REFERENCES ONLY.
**NEVER reproduce any example file in your output.**
Every response must be uniquely generated for the user's specific request.
If the user's prompt overlaps with an example topic, generate a new,
distinct file with different content.
```

This costs zero tokens of behavior change for compliant models and blocks the reproduction path for non-compliant ones without altering any code.

---

## Gaps — Ranked by Impact

1. **Missing `akf index` CLI subcommand** — breaks the only end-to-end loop (`corpus → index → ask → generate → validate → canvas`) and forces users to drop into `python rag/indexer.py`. Highest impact because it blocks the flagship "AI-powered knowledge production" flow.

2. **`akf generate` ignores RAG context** — `pipeline.py` never calls `rag/retriever.py` before LLM generation, so knowledge already in the corpus is never used to ground new output. The product claims to be a knowledge production system but generates files in a vacuum.

3. **`market_pipeline` bypasses validator** — all three stage outputs land on disk without E001–E007 validation. Any domain drift or schema error in market research outputs is invisible to the system that exists precisely to catch such errors.

4. **`system_prompt.md` generate bug** — examples in the system prompt are reproduced verbatim by weaker models, producing stale content instead of new knowledge. One-line fix, but actively corrupts user vaults if unaddressed.

5. **Positioning description contradicts actual system** — `pyproject.toml` description, README headline, and user-guide all describe a "validation pipeline". The multi-LLM generation engine, RAG layer, market research, canvas export, and MCP server are invisible to anyone reading the package description on PyPI.

6. **`EnrichEvent` telemetry is silently dropped** — `Pipeline.writer` is always `None`; every enrich event is lost. The telemetry gap means there is no observability on the most user-facing enrichment workflow.

7. **`market_pipeline` hardcodes `domain: business-strategy`** — bypasses `akf/config.py`, meaning user-defined taxonomies from `akf.yaml` are ignored for market research output. Ontology drift is undetectable.

8. **CLI `ask` emits no telemetry** — `AskQueryEvent` is only emitted via the REST server, leaving all CLI-driven RAG queries invisible in the telemetry stream.
