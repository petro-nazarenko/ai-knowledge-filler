---
title: "ADR-001: Validation Layer Architecture"
type: reference
domain: akf-core
level: advanced
status: active
version: v1.8
tags:
  - adr
  - architecture
  - validation
  - retry
  - ontology
  - telemetry
  - determinism
  - event-stream
  - pipeline-api
  - rest-api
related:
  - "ARCHITECTURE.md"
  - "docs/cli-reference.md"
created: 2026-02-21
updated: 2026-03-12
---


## Pipeline Architecture

### VAL-1 (Shipped)
```
LLM → Structured Output → Validation Filter
```

### VAL-2.1 — Controlled Repair Loop (Shipped)
```
LLM → Validation Engine → Error Normalizer → Retry Controller → Validation Engine → Commit Gate
```

### VAL-2.2 — Model C: Taxonomy Enforcement (Shipped)

Hard enum enforcement via `akf.yaml` taxonomy. Retry pressure becomes ontology signal (see Accountability Shift section).

### VAL-2.3 — Telemetry & Ontology Stabilization (Shipped)

Append-only event log, E-code indexing, aggregation tooling. See Phase 2.3 section below.

### Stage 2 — Programmatic API (Shipped 2026-02-26)
```python
from akf import Pipeline

pipeline = Pipeline(output="./vault/")
result = pipeline.generate("Create a guide on Docker networking")
# result.success, result.file_path, result.content, result.attempts
```

The `Pipeline` class wraps the full repair loop with zero logic duplication. Same `run_retry_loop`, `akf_commit`, `validate` stack — exposed as a Python API.

### Stage 3 — REST API (Shipped 2026-02-26)
```
POST /v1/generate  →  Pipeline.generate()     →  GenerateResult
POST /v1/validate  →  akf.validator            →  ValidateResult
POST /v1/batch     →  Pipeline.batch_generate()
GET  /v1/models    →  list_providers()
GET  /health       →  {"status": "ok"}
```

Started with: `akf serve --host 0.0.0.0 --port 8000`

---

## Core Decisions

### Decision 1: Determinism Boundary

**Rule:** LLM is the ONLY non-deterministic component in the pipeline.

All other components are pure functions with idempotent, reproducible outputs.

| Component | Deterministic? | Role |
|-----------|---------------|------|
| LLM | ❌ No | Content generation only |
| Validation Engine | ✅ Yes | Binary judgment |
| Error Normalizer | ✅ Yes | Semantic translation |
| Retry Controller | ✅ Yes (logic) | Convergence protection |
| Commit Gate | ✅ Yes | Atomic write safety lock |

**Why:** Once determinism boundary is documented, every architectural debate resolves automatically. "Does this belong inside or outside the LLM?" is the only question.

---

### Decision 2: Validation Engine — Binary Judgment

**Rule:** Validation Engine produces only `VALID` or `INVALID`. No intermediate states.

```python
class ValidationResult:
    is_valid: bool
    errors: list[ValidationError]  # empty if valid
```

**Why:** Binary judgment forces explicit design of the Error Normalizer. Ambiguous states ("partially valid") would corrupt the retry loop.

---

### Decision 3: ValidationError Contract

```python
@dataclass
class ValidationError:
    code: str         # E001_INVALID_ENUM
    field: str        # "domain"
    expected: Any     # ["api-design", "security", ...]
    received: Any     # "backend"
    severity: str     # "error" | "warning"
```

### Standard Error Codes

| Code | Meaning |
|------|---------|
| E001_INVALID_ENUM | Field value not in allowed set |
| E002_MISSING_FIELD | Required field absent |
| E003_INVALID_DATE_FORMAT | Date not ISO 8601 |
| E004_TYPE_MISMATCH | Wrong YAML type |
| E005_SCHEMA_VIOLATION | General schema breach |
| E006_TAXONOMY_VIOLATION | Domain not in taxonomy |

---

### Decision 4: Severity Policy

**Error** → Contract violation → blocks commit → triggers retry  
**Warning** → Quality degradation → logged only → commit proceeds

**Rule:** Warnings NEVER trigger retries.

**Why:** Warnings triggering retries inflates cost and increases variance without improving correctness. Start strict — easier to downgrade Error→Warning later than upgrade Warning→Error after corpus grows.

---

### Decision 5: Error Normalizer — Separate Module

**Rule:** Error Normalizer is a separate deterministic module. Never merged with Commit Gate.

**Function:** Translates `ValidationError` objects into human-readable repair instructions for the LLM prompt.

```
E006_TAXONOMY_VIOLATION on field "domain" (received: "backend")
→ "The 'domain' field must be one of: [api-design, backend-engineering, devops, ...]. 
   You used 'backend' which is not in the taxonomy. Choose the closest match."
```

**Why:** Merging with Commit Gate would couple two distinct concerns — semantic translation (probabilistic quality) and atomic write (deterministic safety).

---

### Decision 6: Retry Controller — Convergence Protection

```python
class RetryController:
    max_attempts: int = 3
    
    def should_retry(self, error: ValidationError, attempt_history: list) -> bool:
        # Abort if same E-code fires on same field twice
        if self._is_identical_error(error, attempt_history):
            return False
        return self.attempt_count < self.max_attempts
    
    def _is_identical_error(self, error, history) -> bool:
        # Hash comparison: code + field + received value
        return any(
            (e.code, e.field, str(e.received)) == (error.code, error.field, str(error.received))
            for e in history
        )
```

**Abort condition:** Same `(E-code, field, received_value)` hash appears twice → ontology misfit, not model error. Retry won't converge.

---

### Decision 7: Schema Versioning ~~(Superseded by PATCH-1)~~

> **PATCH-1:** `schema_version` is removed from documents. It belongs to `akf.yaml` only.
> Documents do not carry schema version. The schema version is a configuration concern, not a document concern.
> `generation_id` is the sole optional linking field permitted in documents (see Decision 9).

~~**Rule:** Add `schema_version` field immediately, even if unused.~~

~~```yaml
schema_version: "1.0.0"
```~~

~~**Properties:**~~
~~- Required at commit~~
~~- Immutable during retry~~
~~- Version-aware validation (documents valid under 1.0.0 remain valid under 1.0.0 forever)~~
~~- Prevents retroactive invalidation after schema upgrades~~

---

### Decision 8: Temperature Configuration

**Rule:** Set `temperature=0, top_p=1` explicitly in CLI.

**Why:** Semantic content may vary; structure must not. Explicit setting documents intent, prevents drift from library defaults.

---

## Accountability Shift: Retry Rate as Ontology Signal

**Source:** Engineering review, Feb 21 2026.

Once Model C (hard enum enforcement) is active, retry pressure becomes a measurement of **ontology friction**, not model incompetence.

The LLM operates under a clearly defined contract. If retries spike, one of three things is happening:

1. **Ontology boundary is ambiguous** — category is semantically overloaded
2. **Ontology granularity is wrong** — too broad or too narrow
3. **Ontology vocabulary doesn't match natural language** — LLM proposes near-synonyms

### Failure Mode Signals

**Case A — One domain triggers disproportionate retries:**
```
domain=consulting → 38% retry rate
domain=devops     →  3% retry rate
```
Signal: `consulting` boundary underspecified. Overlaps with `business-strategy` and `project-management`.

**Case B — Model proposes near-synonyms:**
```
"api" attempted when only "api-design" exists
"data-layer" attempted when only "data-engineering" exists
```
Signal: Vocabulary doesn't match natural chunking. Ontology drift.

**Case C — Same E-code fires twice on same field:**
Signal: Correction instruction is clear, but concept→enum mapping is unstable. Ontology misfit, not prompt problem.

---

## Decision 9: Telemetry Architecture — Append-Only Separate Log

**Decision:** Option A. Telemetry lives in a separate append-only operational log. Never in committed documents.

**Principle:** Documents = state. Telemetry = events. State must be clean and canonical. Events must be append-only and analytical. Mixing them makes governance impossible.

### Two Distinct Domains

| Knowledge Domain (Documents) | System Behavior Domain (Telemetry) |
|------------------------------|-------------------------------------|
| Canonical | Ephemeral |
| Deterministic | Analytical |
| Versioned | Diagnostic |
| Contract-bound | Evolutionary |
| Long-lived | Operational |

### Why Retry Metadata Must NOT Live in Documents

Embedding `retry_count`, `rejected_candidates`, etc. creates:
1. Document identity tied to model behavior
2. Regeneration changes metadata → version churn
3. Canonical knowledge contaminated with operational noise
4. Telemetry artifacts frozen into long-lived content

### Telemetry Event Schema

Design as if it could feed a time-series DB. Start with JSONL; schema stays stable.

```json
{
  "generation_id": "uuid-v4",
  "document_id": "abc123",
  "schema_version": "1.0.0",
  "attempt": 1,
  "max_attempts": 3,
  "errors": [
    {
      "code": "E006_INVALID_ENUM",
      "field": "domain",
      "expected": ["business-strategy", "project-management"],
      "received": "consulting"
    }
  ],
  "converged": false,
  "timestamp": "2026-02-21T14:22:01Z",
  "model": "groq-xyz",
  "temperature": 0
}
```

Each retry = new event. No mutation. No rewriting history.

**Why `model` + `temperature`:**  
Ontology friction vs model behavior is a confounding variable. If retry rate spikes after switching models, that's model drift — not ontology drift. Without these fields the signal is uninterpretable.

### The One Exception: generation_id

Documents may optionally carry a single linking field:

```yaml
generation_id: "uuid-v4"
```

This allows joining document to its telemetry trace without embedding telemetry itself. Preserves document purity and observability linkage simultaneously.

### What Telemetry Enables

- Ontology friction history
- Prompt drift detection
- Model regression detection
- Schema change impact visibility
- Per-version retry rate comparison

Without append-only event log, every taxonomy change is anecdotal. With it, ontology stabilization becomes scientific.

---

## VAL-2.3: Telemetry & Ontology Stabilization (Shipped)

**Principle:** Observability before abstraction.

Once Model C ships, E-codes become the telemetry substrate for ontology health measurement.

### Critical Guardrail: Telemetry Must Observe, Never Influence

Retry logic **consumes** validation errors.  
Telemetry **records** retry outcomes.

If telemetry feeds back into generation heuristics at runtime → determinism boundary collapses.

**Telemetry is a read-only instrument. No runtime feedback loop.**

### Three Analyses Enabled by Event Stream

**A. Ontology Friction Map**  
Retry rate per enum value, invalid candidate distribution, repeated E-code clusters.  
→ Directly informs Domain_Taxonomy refinement.

**B. Prompt Drift Detection**  
If retry rate increases globally without schema change → prompt regression, model version change, or decoding config issue.  
→ Telemetry becomes regression testing for the generation pipeline.

**C. Schema Change Impact Analysis**  
After tightening taxonomy: compare retry distribution pre vs post change. Measure convergence delta. Detect new high-friction nodes.  
→ Makes Phase 2.4 governance decisions defensible rather than architectural intuition.

### Storage Design Principle

Start with append-only JSONL. Design schema as if it could feed a time-series DB later. This affects: schema field naming, timestamp precision, indexing strategy, aggregation shape.

### Three Ontology Defect Types

Under deterministic generation (temperature=0, stable prompt, fixed model, fixed schema), elevated retries on a specific enum isolate to one of:

| Defect | Description | Example |
|--------|-------------|---------|
| **Boundary ambiguity** | Domain overlaps semantically with adjacent enums | `consulting` spanning `business-strategy` and `project-management` |
| **Lexical misalignment** | Enforced label doesn't match natural semantic compression | `api-design` vs `api` |
| **Missing category** (ontological incompleteness) | Repeated E006 on edge-case documents that legitimately belong somewhere the taxonomy doesn't represent | No enum exists for the concept |

The model is not failing. It is exposing compression tension between reality and the schema.

### Normalized Retry Rate (Required)

When aggregating retry rate per enum, compute both:

```
absolute_retry_count    # total retries on this enum value
retry_rate_normalized   # retry_count / usage_frequency
```

**Why:** An enum with 100% retry rate on 3 documents is more ontologically suspect than 15% retry rate on 200 documents. Absolute count alone produces popularity bias — high-volume enums appear problematic even when fundamentally sound.

Normalized rate is the governance signal. Absolute count is context.

### Metrics to Collect (Final)

Minimal diagnostic basis for the ontology stress-testing framework:

**Critical: Separate two distinct retry signals. Collapsing them loses diagnostic resolution.**

#### Signal A — First-Attempt Invalid Rate
```
% of documents where attempt 1 violates enum constraints
```
Measures: natural compression mismatch between model and ontology.

#### Signal B — Multi-Attempt Convergence Rate
```
% of documents requiring >1 attempt that eventually converge
```
Measures: boundary recoverability.

**Diagnostic combinations:**

| First-Attempt Invalid | Convergence | Defect |
|-----------------------|-------------|--------|
| High | High | Lexical misalignment |
| High | Low | Missing category or severe boundary ambiguity |
| Low | High (late failures) | Prompt drift or structural instability |

#### Convergence Time — Precise Definition
```
convergence_time = attempts required until valid schema output
```
- **Mean attempts** — converged documents only
- **Non-convergence rate** — hard failure rate (reported separately, never folded into mean)

Non-converged documents averaged in = misleading signal. The pair (mean attempts converged + non-convergence rate) tells you whether ontology is slightly frictional or fundamentally misrepresenting reality.

#### Missing Category Detection
```
rejected_value → count (total)
rejected_value → unique_document_count
rejected_value → convergence_outcome_distribution
```
If a rejected value (e.g., `"consulting"`) appears across many unique documents and often fails to converge cleanly → candidate enum addition.

**Threshold for governance action:** high frequency across unique documents, not just total count. Single-document outliers do not drive taxonomy decisions.

#### Full Metric Set

| Metric | Signal | Defect Detected |
|--------|--------|-----------------|
| First-attempt invalid rate (Signal A) | Compression mismatch | Lexical misalignment |
| Multi-attempt convergence rate (Signal B) | Boundary recoverability | Missing category / ambiguity |
| Mean attempts to convergence (converged only) | Friction magnitude | Any |
| Non-convergence rate | Hard failure rate | Severe defect |
| Rejected candidate frequency (absolute + unique doc count) | Latent ontology demand | Missing category |
| Convergence outcome per rejected value | Recoverability | Missing category vs ambiguity |
| Pre/post schema comparison delta | Governance legitimacy | Impact of changes |
| Global retry rate trend | Pipeline health | Prompt drift / model regression |

Without historical event logs, ontology revisions are aesthetic. With logs, they are falsifiable.

#### Pre/Post Schema Comparison — Environmental Control Required
When changing taxonomy, freeze before measuring delta:
- Model version
- Temperature
- Prompt

Otherwise delta cannot be attributed to schema change. Schema impact analysis without environmental control becomes anecdotal.

### Phase 2.3 Build Scope

- Append-only telemetry store (structured event schema)
- E-code indexing (queryable by code, field, value, timestamp)
- Aggregation tooling: retry rate per enum, rejected candidate distribution, convergence time per domain
- Per-version comparison for ontology change impact measurement
- Ontology review: identify domains with >15% retry rate → refine boundaries

---

## Priority Stack (from Engineering Review)

| Phase | Objective | Why |
|-------|-----------|-----|
| VAL-1 | Structured Output + Validation Filter | ✅ Shipped |
| VAL-2.1 | Controlled Repair Loop | ✅ Shipped |
| VAL-2.2 | Model C — Taxonomy Enforcement | ✅ Shipped |
| VAL-2.3 | Telemetry & Ontology Stabilization | ✅ Shipped |
| 2.4 | Schema Evolution Tooling | ✅ Complete |
| 2.5 | Onboarding & Marine Crew Pilot | ✅ Complete |
| Stage 2 | Programmatic API — `Pipeline` class | ✅ Complete 2026-02-26 |
| Stage 3 | REST API — `akf serve`, FastAPI | ✅ Complete 2026-02-26 |
| Stage 4 | Telegram Bot / Web UI / n8n connectors | ⬜ Next |
| Later | Quality Scoring Layer | Analytics on top of mature infrastructure |

**What NOT to build prematurely:**
- ❌ Document-level quality scoring — subjective, non-contractual, second stochastic loop
- ❌ Knowledge graph extraction — depends on stable ontology first

---

## Infrastructure Layers Model

```
1. Determinism      → VAL-2.1: Repair Loop ✅
2. Contract         → VAL-2.1: ValidationError + E-codes ✅
3. Ontology         → VAL-2.2: Model C taxonomy enforcement ✅
4. Observability    → VAL-2.3: Telemetry & ontology stabilization ✅
5. Governance       → Phase 2.4: Schema evolution tooling ✅
6. Interface        → Stage 2: Pipeline API / Stage 3: REST API ✅
7. Semantics        → Phase 3.0: Graph extraction (planned)
8. Analytics        → Later: Quality scoring
```

**Current position:** Layer 5 complete. Next = Stage 4 interfaces (Telegram, Web UI, n8n).

---

## Cross-Document Invariants (Future)

Once taxonomy enforcement (layer 3) is stable, enforce:

- Domain ↔ tag compatibility rules
- Required related domains
- Taxonomy hierarchy validation
- Disallowed combinations

This is when the system becomes a knowledge system, not a formatter.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-02-21 | Initial ADR from engineering review |
| v1.1 | 2026-02-21 | Phase 2.1 implementation decisions (S1-S4 complete) |
| v1.2 | 2026-02-21 | Phase 2.3 telemetry section, priority stack, infrastructure layers model, cross-document invariants |
| v1.3 | 2026-02-21 | Decision 9: Telemetry architecture resolved — append-only log, separate from documents. generation_id as linking field. Two Domains model (Knowledge vs System Behavior) |
| v1.4 | 2026-02-21 | Strengthened event schema (model, temperature, converged, max_attempts). Telemetry guardrail: observe never influence. Three analyses: Friction Map, Prompt Drift, Schema Impact. Event stream framing. |
| v1.5 | 2026-02-21 | Three ontology defect types formalized (boundary ambiguity, lexical misalignment, missing category). Normalized retry rate added to prevent popularity bias. Minimal diagnostic basis table. Ontology stress-testing framework framing. |
| v1.6 | 2026-02-21 | Separated Signal A (first-attempt invalid) from Signal B (multi-attempt convergence). Precise convergence time definition. Missing category detection via unique document count. Environmental control requirements for pre/post comparison. |
| v1.7 | 2026-02-26 | Stage 2: Pipeline class — programmatic API, zero logic duplication. Stage 3: REST API (FastAPI), `akf serve` CLI command. 425 tests, 88% coverage, CI green 3.10/3.11/3.12. Infrastructure Layers Model updated: layer 5 = Interface. Priority Stack updated: 2.2–Stage 3 all complete. |
| v1.8 | 2026-03-12 | VAL-phase notation introduced (VAL-1, VAL-2.1, VAL-2.2, VAL-2.3). PATCH-1: schema_version removed from documents — belongs to akf.yaml only. generation_id is sole optional linking field. VAL-2.2 and VAL-2.3 marked shipped. Priority stack and infrastructure layers updated to VAL notation. |
