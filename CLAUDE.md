# CLAUDE.md — AI Assistant Guide for ai-knowledge-filler

This file provides guidance for AI assistants (Claude and others) working in this repository.

---

## Project Overview

**AI Knowledge Filler** transforms any LLM into a deterministic knowledge base generator. It produces structured Markdown files with YAML frontmatter for knowledge bases like Obsidian.

**Core philosophy:** Not a chatbot enhancement — a knowledge engineering architecture. Same input → same structure, every time.

**Current version:** 2.2.0
**Python requirement:** 3.8+

---

## Repository Structure

```
ai-knowledge-filler/
├── 00-Core_System/          # Master system prompts, metadata standards, protocols
│   ├── System_Prompt_AI_Knowledge_Filler.md  # LLM role definition & output rules
│   ├── Custom_Instructions.md                # AI working profile & quality standards
│   ├── Metadata_Template_Standard.md         # Authoritative YAML schema (v1.1)
│   ├── File_Update_Protocol.md               # Rules for merging/updating files
│   ├── Domain_Taxonomy.md                    # All valid domain values
│   └── Prompt_Engineering_Workflow.md        # 8-stage methodology
├── 01-Documentation/        # Deployment guides, use cases, dashboards
├── 02-Examples/             # Reference Markdown files showing correct structure
├── 03-Scripts/              # validate_yaml.py (validator), fix-related-yaml.js (Obsidian macro)
├── 04-GitHub/               # GitHub-specific configs
├── 05-Reports/              # Analysis reports
├── 06-Archive/              # Archived files
├── .github/workflows/       # CI/CD: validate-metadata.yml
├── validate_yaml.py         # SINGLE SOURCE OF TRUTH for validation logic
├── requirements.txt         # pyyaml>=6.0.0
├── README.md                # Project overview
└── CONTRIBUTING.md          # Contribution guidelines
```

---

## Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Validate all knowledge files (run from repo root)
python validate_yaml.py

# Expected output on success:
# ✅ All files valid!
# Exit code: 0

# On failure:
# ❌ Validation failed: N file(s) with errors
# Exit code: 1
```

---

## YAML Metadata Standard

Every knowledge `.md` file (except excluded files) **must** start with a YAML frontmatter block.

### Required Template

```yaml
---
title: "<Brief precise title>"
type: "<concept|guide|reference|checklist|project|roadmap|template|audit>"
domain: "<from Domain_Taxonomy>"
level: "<beginner|intermediate|advanced>"
status: "<draft|active|completed|archived>"
version: "v1.0"           # optional
tags: [tag1, tag2, tag3]  # array, 3-10 items, lowercase-hyphenated
related:
  - "[[Related Note 1]]"  # MUST be quoted — bare [[]] causes YAML parse errors
  - "[[Related Note 2]]"
created: YYYY-MM-DD       # ISO 8601, never changes after creation
updated: YYYY-MM-DD       # ISO 8601, update on every change
---
```

### Field Rules

| Field | Required | Valid Values |
|-------|----------|-------------|
| `title` | Yes | String, 3-60 chars, unique within domain |
| `type` | Yes | `concept`, `guide`, `reference`, `checklist`, `project`, `roadmap`, `template`, `audit` |
| `domain` | Yes | See `00-Core_System/Domain_Taxonomy.md` (lowercase-hyphenated) |
| `level` | Yes | `beginner`, `intermediate`, `advanced` |
| `status` | Yes | `draft`, `active`, `completed`, `archived` |
| `version` | No | `v1.0`, `v2.1`, etc. |
| `tags` | Yes | Array of strings, min 3, max 10, lowercase-hyphenated |
| `related` | No* | Array of **quoted** WikiLinks: `"[[Page Name]]"` |
| `created` | Yes | `YYYY-MM-DD` (set once, never changed) |
| `updated` | Yes | `YYYY-MM-DD` (updated on every modification) |

*`related` is recommended for knowledge graph connectivity — absence triggers a warning.

### Critical YAML Rules

- **Related links MUST be quoted:** `"[[Link]]"` not `[[Link]]` — bare square brackets break YAML parsers
- **Tags must be an array:** `[tag1, tag2]` not a plain string
- **Dates must be ISO 8601:** `YYYY-MM-DD` only
- **Domain must match taxonomy:** non-matching domains produce a warning in CI

### Excluded Files (no frontmatter required)

The validator skips these files (defined in `validate_yaml.py:EXCLUDED_FILES`):
- `README.md`
- `CONTRIBUTING.md`
- `DEPLOYMENT_READY.md`
- `LICENSE.md`
- `CHANGELOG.md`
- `CLAUDE.md`

And these directories (defined in `validate_yaml.py:EXCLUDED_DIRS`):
- `.github`, `.git`, `node_modules`, `__pycache__`, `venv`, `.venv`

---

## Valid Domain Values

Defined in `validate_yaml.py:VALID_DOMAINS` and `00-Core_System/Domain_Taxonomy.md`:

`ai-system`, `system-design`, `api-design`, `data-engineering`, `security`, `devops`, `product-management`, `consulting`, `workflow-automation`, `prompt-engineering`, `business-strategy`, `project-management`, `knowledge-management`, `documentation`, `learning-systems`, `frontend-engineering`, `backend-engineering`, `infrastructure`, `machine-learning`, `data-science`, `operations`, `finance`, `marketing`, `sales`, `healthcare`, `finance-tech`, `education-tech`, `e-commerce`

To add a new domain: update both `Domain_Taxonomy.md` and the `VALID_DOMAINS` list in `validate_yaml.py`.

---

## File Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Python scripts | `snake_case.py` | `validate_yaml.py` |
| JavaScript macros | `kebab-case.js` | `fix-related-yaml.js` |
| GitHub Actions | `kebab-case.yml` | `validate-metadata.yml` |
| Markdown knowledge files | `Title_Case_With_Underscores.md` | `System_Prompt_AI_Knowledge_Filler.md` |
| Infrastructure docs | `UPPERCASE.md` | `README.md`, `CONTRIBUTING.md` |

---

## Code Conventions

### Python (`validate_yaml.py`)

- **Functions:** `snake_case` — `validate_file()`, `validate_date_format()`, `should_validate_file()`
- **Constants:** `UPPERCASE` — `VALID_TYPES`, `EXCLUDED_FILES`, `VALID_DOMAINS`
- **Error handling:** Functions return `(errors: list[str], warnings: list[str])` tuples; exceptions caught and appended as error strings
- **Single source of truth:** All enum values and exclusion rules defined once at module top
- **Exit codes:** `sys.exit(0)` on success, `sys.exit(1)` on validation failures

### JavaScript (Obsidian QuickAdd macros)

- **Entry point:** `module.exports = async (params) => { ... }`
- **Variables:** `camelCase` — `filesProcessed`, `metadataCache`
- **Error handling:** `try/catch` blocks, errors collected in array, reported in Notice at end

### Markdown content structure (for guides)

```
## Purpose / Overview
## Prerequisites
## Implementation
### Step 1: ...
### Step 2: ...
## Best Practices
## Troubleshooting
## Conclusion
```

---

## Git Workflow

### Branch naming

```
feature/<description>       # new feature or content
fix/<description>           # bug fix or correction
docs/<description>          # documentation only
```

### Commit message format (Conventional Commits)

```
<type>: <description>

[optional body]
[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

**Examples:**
```bash
git commit -m "feat: add OAuth 2.0 implementation guide"
git commit -m "fix: correct YAML frontmatter in API design guide"
git commit -m "docs: expand deployment troubleshooting section"
```

### Before committing

Always run validation:
```bash
python validate_yaml.py
```

CI will block the merge if this fails.

### PR checklist

- [ ] All `.md` files in `00-Core_System/`, `01-Documentation/`, `02-Examples/` have valid YAML frontmatter
- [ ] `python validate_yaml.py` passes with exit code 0
- [ ] Related links use quoted WikiLink syntax: `"[[Page Name]]"`
- [ ] `updated` date reflects today in all modified files
- [ ] Internal links use `[[WikiLink]]` format, not plain Markdown links
- [ ] Commit messages follow Conventional Commits format

---

## CI/CD Pipeline

**File:** `.github/workflows/validate-metadata.yml`

**Triggers:** Push or PR to `main` or `develop` branches

**Steps:**
1. Checkout repository
2. Set up Python 3.11
3. `pip install -r requirements.txt`
4. `python validate_yaml.py` (from repo root)

**Failure:** Any `.md` file with missing required fields, invalid enum values, or malformed YAML will cause CI to exit with code 1, blocking the merge.

---

## Adding New Content

### New knowledge file

1. Create `.md` file in the appropriate directory
2. Add complete YAML frontmatter following the template above
3. Use heading hierarchy `##`, `###`, `####`
4. Add `[[WikiLinks]]` to related files in the `related` field (quoted)
5. Run `python validate_yaml.py` — must pass before committing

### New domain

1. Add to `00-Core_System/Domain_Taxonomy.md` with description and examples
2. Add the domain string to `VALID_DOMAINS` list in `validate_yaml.py`
3. Both changes must be in the same commit

### New script

- Place in `03-Scripts/`
- Python scripts: follow existing patterns in `validate_yaml.py`
- JavaScript (Obsidian macros): use `module.exports = async (params) => {...}` pattern

---

## Architecture

```
User Request
    → System Prompt (00-Core_System/System_Prompt_AI_Knowledge_Filler.md)
    → Execution Protocol
    → Metadata Standards (Metadata_Template_Standard.md + Domain_Taxonomy.md)
    → Structured Markdown Output
    → Validation (validate_yaml.py)
    → CI/CD Gate (GitHub Actions)
    → Knowledge Base (Obsidian vault)
```

**Result:** Deterministic, validated, graph-connected knowledge files on every generation.

---

## Common Pitfalls

| Mistake | Effect | Fix |
|---------|--------|-----|
| Unquoted `[[related]]` links | YAML parse error, CI fails | Quote them: `"[[Link]]"` |
| `tags: "single string"` | CI error: tags must be array | Use `tags: [tag1, tag2, tag3]` |
| Wrong date format `DD-MM-YYYY` | CI error | Use `YYYY-MM-DD` |
| Invalid `type` value | CI error | Use one of the 8 valid types |
| Invalid `level` value | CI error | Use `beginner`, `intermediate`, or `advanced` |
| Forgetting to update `updated` field | Stale metadata | Always update to today's date when modifying |
| New domain not in `validate_yaml.py` | CI warning | Add to both `Domain_Taxonomy.md` and `VALID_DOMAINS` |
| Adding YAML frontmatter to excluded files | Unexpected behavior | Leave `README.md`, `CONTRIBUTING.md`, etc. without frontmatter |
