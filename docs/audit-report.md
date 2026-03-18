# Full Repository Audit Report

**Date:** 2026-03-18
**Scope:** `akf/`, `rag/`, `tests/`, `docs/`, `.github/`, CLI entry points, configs, `README.md`, `CHANGELOG.md`
**Auditor:** Automated static analysis

### Constraints (not flagged, all intentional)

- `schema_version` absent from documents / commit_gate — ADR-001 v1.8 PATCH-1
- `rag/` at repo root, not `akf/rag/` — ADR-002
- `server.py` slowapi coverage — known pre-existing gap
- REST API auth optional — by design

---

## HIGH

| Location | Category | Description |
|---|---|---|
| `CHANGELOG.md:8` | DOCS | All ~150 commit URLs reference `petrnzrnk-creator/ai-knowledge-filler`; `pyproject.toml:50` and README use `petro-nazarenko/ai-knowledge-filler` — every link is dead |
| `rag/vector_store.py:111` | ERROR HANDLING | `d["metadata"]` accessed with bare key lookup inside delete loop; any document missing the `"metadata"` key raises `KeyError` and corrupts the delete operation |
| `rag/vector_store.py:118` | ERROR HANDLING | `self._embeddings[keep]` uses an unvalidated index list; doc/embedding length mismatch after a partial `add()` raises `IndexError` |
| `rag/vector_store.py:129-132` | ERROR HANDLING | `documents[i]`, `metadatas[i]`, `ids[i]` indexed in a loop over `ids` with no length-equality assertion; mismatched batch inputs raise `IndexError` |
| `rag/vector_store.py:155` | ERROR HANDLING | `self._embed(query_texts[:1])[0]` indexes the result without checking the array is non-empty; empty embed result raises `IndexError` on every query |
| `rag/vector_store.py:161-164` | ERROR HANDLING | `self._docs[i]` accessed for each index in `top_indices` without bounds validation; stale indices after deletions cause `KeyError` |
| `akf/pipeline.py:23-44` | INTERFACE CONTRACTS | `GenerateResult` uses `file_path: object`; `EnrichResult` uses `path: Path` — inconsistent field name and type across the two primary result dataclasses breaks unified callers |
| `tests/test_s4_commit_gate.py` + `tests/test_commit_gate.py` | DUPLICATE TESTS | ~70% of test cases duplicated across both files; both suites cover `commit()` happy path, error accumulation, and blocking logic |

---

## MEDIUM

### Type Annotations

| Location | Category | Description |
|---|---|---|
| `akf/pipeline.py:11` | TYPE ANNOTATIONS | `file_path: object = None` and `filepath: object = None` in `GenerateResult`/`ValidateResult`; should be `Optional[Path]`. `errors: list` in multiple result dataclasses lacks generic parameter |
| `akf/pipeline.py:123` | TYPE ANNOTATIONS | `Pipeline.__init__` parameters `output`, `model`, `telemetry_path`, `verbose`, `writer`, `config` have no type annotations |
| `akf/pipeline.py:156` | TYPE ANNOTATIONS | `_extract_filename(content, prompt)` has no type annotations on either parameter |
| `rag/indexer.py:26` | TYPE ANNOTATIONS | `_load_frontmatter_module() -> Any`, `_load_markdown_splitter_class() -> Any` (line 36), `_build_collection() -> Any` (line 47) return bare `Any`; downstream callers get no type safety |
| `rag/retriever.py:15` | TYPE ANNOTATIONS | `_build_collection(config: RAGConfig) -> Any` returns bare `Any` |
| `rag/vector_store.py:85` | TYPE ANNOTATIONS | `_get_model(self) -> Any`; should be `-> SentenceTransformer` |

### Error Handling

| Location | Category | Description |
|---|---|---|
| `akf/pipeline.py:147` | ERROR HANDLING | `_load_system_prompt()` catches `Exception` without logging or re-raising; system prompt load failures are silently dropped |
| `akf/pipeline.py:214-215` | ERROR HANDLING | `except Exception: initial_errors = []` swallows all validation failures and resets the error list to empty, hiding the original cause |
| `akf/pipeline.py:228-231` | ERROR HANDLING | `except Exception: return []` inside the `validate_fn` closure silently converts any validation crash into an empty error list |
| `akf/config.py:256-283` | ERROR HANDLING | Module-level `_config_cache` mutated with `global` keyword; no lock protects concurrent first-load — race condition under multi-threaded import |
| `rag/indexer.py:67` | ERROR HANDLING | `frontmatter_module.load(path)` called bare; parse errors, encoding errors, or permission failures on any single markdown file crash the entire indexing run |
| `rag/indexer.py:75` | ERROR HANDLING | `splitter.split_text(content)` called bare; exceptions propagate and abort the full index build |
| `rag/indexer.py:113-118` | ERROR HANDLING | `getattr(doc, "metadata", {})` used without validating that `metadata` is a dict; non-dict metadata crashes line 120 |
| `rag/retriever.py:65-68` | ERROR HANDLING | `(result.get("ids") or [[]])[0]` only guards against a missing key, not an empty-list value; `{"ids": []}` still raises `IndexError` at `[0]` |
| `rag/vector_store.py:66` | ERROR HANDLING | `json.load(f)` in `_load()` not wrapped; corrupted JSON makes the entire vector store unloadable with an unhandled `JSONDecodeError` |
| `rag/vector_store.py:68` | ERROR HANDLING | `np.load(self._emb_path)` not wrapped; corrupted `.npy` file raises unhandled exception |

### Security

| Location | Category | Description |
|---|---|---|
| `llm_providers.py:174` | SECURITY | `response.choices[0].message.content` accessed without checking `choices` is non-empty; the API can return `choices=[]` on content-filter refusals |
| `llm_providers.py:377` | SECURITY | `response.json().get("response", "")` for Ollama assumes the response body is a dict; no schema validation; malformed responses silently return empty string |

### Validation

| Location | Category | Description |
|---|---|---|
| `akf/pipeline.py:395` | VALIDATION | `e.severity.value == "error"` is a string comparison against an enum value; should be `e.severity == Severity.ERROR` |

### Interface Contracts

| Location | Category | Description |
|---|---|---|
| `akf/pipeline.py:131` | INTERFACE CONTRACTS | `config` parameter accepted in `Pipeline.__init__` but never read or stored anywhere in the class |

### Dead Code

| Location | Category | Description |
|---|---|---|
| `llm_providers.py:181` | DEAD CODE | `import anthropic  # noqa: F401` inside `ClaudeProvider.is_available()` is unused — name is immediately discarded. Same pattern at lines 252 (Gemini), 324 (OpenAI), 467 (Groq), 539 (XAI) |

### Docs

| Location | Category | Description |
|---|---|---|
| `README.md:10` | DOCS | Coverage badge shows `92%`; line 269 states "715 tests, 92% coverage"; `ci.yml:42` and `tests.yml:40` enforce `--cov-fail-under=85`; `docs/audit.md` states "560+ tests, 91% overall" — three sources disagree |
| `docs/adr/ADR-002.md:49` | DOCS | `extends:` key described as "Deferred to v0.6.x"; current version is v1.0.7 with no implementation and no follow-up ADR |
| `ARCHITECTURE.md:1` | DOCS | Documents version v1.0.0; `pyproject.toml` is at v1.0.7; six patch releases unaccounted for |

### CI

| Location | Category | Description |
|---|---|---|
| `.github/workflows/changelog.yml:29-35` | CI | `git pull --rebase origin main` followed immediately by `git push` with no `set -e` or exit-code check; a rebase conflict causes push to proceed on pre-rebase state |
| `.github/workflows/release.yml:20-21` | CI | `pytest --tb=short` in the release workflow lacks `--cov-fail-under`; a release can ship with coverage below the threshold enforced in CI |

### Config

| Location | Category | Description |
|---|---|---|
| `pyproject.toml:32` | CONFIG | `all` extras omit `python-frontmatter>=1.1.0`, `langchain-text-splitters>=0.3.0`, and `numpy>=1.26.0`; installing `[all]` does not install RAG dependencies |
| `pyproject.toml:32` | CONFIG | `google-genai==1.0.0` is pinned in `requirements.lock` and imported in `llm_providers.py` but declared in no extras group; Gemini support is an undeclared implicit dependency |

### Tests

| Location | Category | Description |
|---|---|---|
| `tests/test_s2_error_normalizer.py:25-70` + `tests/test_error_normalizer.py:19-73` | DUPLICATE TESTS | Both files test `normalize_errors()` with identical happy path, empty-list, and mixed-severity cases |
| `tests/test_s3_retry_controller.py:250-318` + `tests/test_retry_controller.py:369-413` | DUPLICATE TESTS | `_check_convergence()` logic tested twice with overlapping inputs and assertions |
| `tests/test_cli_init.py:47-81` | WRONG BEHAVIOR | Patches `cli.Path` and `shutil.copy` inside a `with` block that contains only `pass`; patches are never applied, test outcome depends on real filesystem side-effects |
| `tests/test_pipeline_rag.py:63` | HARDCODED PATH | `Pipeline(output="/tmp/akf_test", ...)` uses a hard-coded `/tmp` path; fails on Windows and pollutes the filesystem if fixture teardown is skipped |
| `tests/test_canvas_generator.py:431` | HARDCODED VALUE | `assert len(canvas["nodes"]) == 49` hardcodes a fixture-derived node count; any change to the corpus silently breaks this test |
| `tests/test_commit_gate.py` | MISLEADING NAME | `test_missing_schema_version_blocks_commit` and `test_wrong_schema_version_blocks_commit` both assert `committed is True` (correct per ADR-001 PATCH-1) but names imply blocking; future maintainers will distrust or revert the assertions |

---

## LOW

### Dead Code

| Location | Category | Description |
|---|---|---|
| `akf/pipeline.py:2` | DEAD CODE | `import re` is unused in `pipeline.py` |
| `akf/pipeline.py:128` | DEAD CODE | `expanduser()` called on `output` in `__init__` and again in `generate()` at line 209; double-expansion is harmless but redundant |
| `akf/telemetry.py:321` | DEAD CODE | `TypeError` message lists four event types but the union includes five (`MarketAnalysisEvent` omitted from the string) |
| `akf/market_pipeline.py:385` | DEAD CODE | Log message reads `"Stage 1/3"` but the market pipeline has four stages |

### Error Handling

| Location | Category | Description |
|---|---|---|
| `rag/config.py:36` | ERROR HANDLING | `except ValueError` on `int(batch_size_raw)` silently defaults to 64 without logging the invalid value; users cannot diagnose why `RAG_BATCH_SIZE` is ignored |
| `rag/indexer.py:93` | ERROR HANDLING | `corpus_dir.glob(resolved.markdown_glob)` not wrapped; an invalid glob pattern from config raises `ValueError` with no user-facing message |
| `rag/retriever.py:79` | ERROR HANDLING | `dict(metadata)` assumes metadata is dict-like; custom backend metadata objects raise `TypeError` |
| `rag/vector_store.py:106` | ERROR HANDLING | `delete()` silently returns when `where` dict is missing the `"source"` key; callers passing wrong filter keys get no error or indication |
| `llm_providers.py:398` | ERROR HANDLING | `OllamaProvider.is_available()` catches bare `Exception` and returns `False`; connection refused, timeout, and actual code bugs are all treated identically |
| `akf/enricher.py:224` | ERROR HANDLING | `except Exception: pass` in `write_back()` atomic rename path suppresses real disk errors (full filesystem, permission denied) |

### Type Annotations

| Location | Category | Description |
|---|---|---|
| `rag/vector_store.py:53` | TYPE ANNOTATIONS | `self._model: Any = None` should be `Optional[SentenceTransformer]` |
| `cli.py:290` | TYPE ANNOTATIONS | `Path.is_relative_to()` used in `sanitize_filename()`; method added in Python 3.9 — no version guard, confusing error on 3.8 if backports are absent |

### Tests

| Location | Category | Description |
|---|---|---|
| `tests/test_cli_ask.py:20-44` + `tests/test_cli_ask_telemetry.py:26-48` | DUPLICATE TESTS | Both test `cmd_ask()` happy path with nearly identical mock setup; telemetry variant adds marginal coverage value |
| `tests/test_validator.py` | COVERAGE GAP | E008 relationship-type checks missing edge cases: empty note name in wikilink (`[[|implements]]`), case-insensitive relationship type matching, Unicode in relationship type |

### Docs

| Location | Category | Description |
|---|---|---|
| `docs/batch-knowledge-base-guide.md:9-10` | DOCS | Uses Obsidian WikiLink syntax (`[[docs/cli-reference.md\|references]]`) which renders as literal text in standard Markdown renderers (GitHub, mkdocs without plugin) |

### Config

| Location | Category | Description |
|---|---|---|
| `pyproject.toml:8` | CONFIG | `authors = [{ name = "Petro Nzrnk" }]` is an abbreviated name inconsistent with the GitHub handle `petro-nazarenko` used everywhere else in the project |

---

## Summary

| Severity | Count |
|---|---|
| HIGH | 8 |
| MEDIUM | 34 |
| LOW | 15 |
| **Total** | **57** |
