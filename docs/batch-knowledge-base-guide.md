---
title: "Batch Knowledge Base Guide"
type: guide
domain: akf-docs
level: intermediate
status: active
tags: [batch, plan.json, knowledge-base, workflow, taxonomy]
related:
  - "[[docs/cli-reference.md|references]]"
  - "[[docs/user-guide.md|requires]]"
created: 2026-03-18
updated: 2026-03-18
---

## Concept

`plan.json` is a flat JSON array of generation prompts. Each object maps to one
Markdown file. Running `akf generate --batch plan.json` submits all prompts
sequentially through the full pipeline — LLM → validation → retry → commit —
and writes only files that pass validation.

Batch generation means consistency (every file shares the same taxonomy), speed
(50 files in minutes), and reproducibility (the plan file is version-controllable).

---

## Taxonomy First

Design your `akf.yaml` before writing any prompts. The taxonomy defines what is
valid — domain values, type values, level values. Files generated outside those
boundaries fail E001/E006 and trigger retries.

Define `domains` (your knowledge areas, 3–10 is practical), `vault_path`
(output directory), and `relationship_types` (labels allowed in `[[Note|type]]`
links). Keep domain names kebab-case. A prompt resolves `domain: devops` only
if `devops` is in your taxonomy — mismatches waste LLM retries.

---

## Plan Design Principles

**Order matters.** Generate foundational files first so related links resolve
to real files:

1. **Concepts** — mental models, definitions (no dependencies)
2. **References** — specifications, schemas, command references
3. **Guides** — how-to tutorials (reference concepts and references)
4. **Checklists** — review gates (reference guides)

**Naming prompts.** Be explicit about type and audience:

```
✅ "Create a concept on CAP theorem for backend engineers"
✅ "Create a reference on Kubernetes resource limits"
❌ "Kubernetes stuff"
```

**Related links strategy.** Use consistent terminology across prompts (always
"JWT authentication", never "token auth") — AKF infers `related:` links from
topic proximity, so terminology drift produces weaker cross-links.

---

## Example: Generic Technical Knowledge Base

### akf.yaml

```yaml
schema_version: "1.0.0"
vault_path: "./docs"

taxonomy:
  domains:
    - backend-engineering
    - api-design
    - devops
    - security

enums:
  type:
    - concept
    - guide
    - reference
    - checklist

  level:
    - beginner
    - intermediate
    - advanced

  status:
    - draft
    - active
    - archived

relationship_types:
  - implements
  - requires
  - extends
  - references
  - supersedes
  - part-of
```

### plan.json

```json
[
  {"prompt": "Create a concept on microservices architecture for backend engineers"},
  {"prompt": "Create a concept on CAP theorem and distributed consistency trade-offs"},
  {"prompt": "Create a concept on JWT authentication and stateless session design"},

  {"prompt": "Create a reference on REST API versioning strategies"},
  {"prompt": "Create a reference on HTTP status codes for API design"},
  {"prompt": "Create a reference on Docker CLI commands for container management"},
  {"prompt": "Create a reference on environment variable management for backend services"},

  {"prompt": "Create a guide on building a REST API with FastAPI and JWT authentication"},
  {"prompt": "Create a guide on CI/CD pipeline setup with GitHub Actions for a Python service"},
  {"prompt": "Create a guide on container security hardening for Docker images"},
  {"prompt": "Create a guide on API rate limiting strategies for high-traffic services"},

  {"prompt": "Create a checklist for REST API security review before production deployment"},
  {"prompt": "Create a checklist for Docker deployment readiness review"}
]
```

### Step-by-Step Commands

**1. Scaffold config:**

```bash
akf init
```

**2. Replace the generated `akf.yaml` with the config above, then set an API key:**

```bash
export GROQ_API_KEY="gsk_..."      # free tier, fastest
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

**3. Run the batch:**

```bash
akf generate --batch plan.json
```

```
✅ Microservices_Architecture_for_Backend_Engineers.md
✅ CAP_Theorem_and_Distributed_Consistency_Trade_offs.md
...
✅ Docker_Deployment_Readiness_Review.md
→ Generated: 13 | Failed: 0
```

---

## Validation

After the batch completes, validate the whole vault:

```bash
akf validate --path docs/
```

**Common failures and fixes:**

| Error | Cause | Fix |
|-------|-------|-----|
| E006 | Domain not in `akf.yaml` taxonomy | Add domain, re-run the affected prompt |
| E001 | Invalid enum value (e.g. `type: document`) | Tighten the prompt; file auto-retries up to 3× |
| E002 | Missing required field | Retry the prompt — usually a transient LLM failure |
| E008 | Unknown relationship type in `related:` | Add the type to `relationship_types` in `akf.yaml` |

Re-run a single failed prompt without touching the rest:

```bash
akf generate "Create a checklist for Docker deployment readiness review"
```

Add `--strict` to promote warnings (e.g. empty `related:`) to errors.

---

## Result

After a successful batch + validate run you have:

- **Validated Markdown files** — every file passed E001–E008 checks
- **Consistent taxonomy** — all `domain`, `type`, `level`, `status` values from your controlled vocabulary
- **Interlinked notes** — `related:` fields form a navigable graph
- **CI-ready** — `akf validate --path docs/` exits 0; drop into GitHub Actions as a gate

The output is plain Markdown with YAML frontmatter. Drop it into Obsidian,
MkDocs, Docusaurus, or any static site generator without modification.
