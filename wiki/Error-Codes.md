# Error Codes

AKF validation produces typed error codes (E001–E008) instead of free-form messages. Each code maps to a specific schema violation and a deterministic repair instruction sent to the LLM on retry.

---

## Error Code Reference

| Code | Field | Severity | Meaning |
|------|-------|----------|---------|
| [E001](#e001) | `type` / `level` / `status` | error | Value not in allowed enum set |
| [E002](#e002) | any | error | Required field missing |
| [E003](#e003) | `created` / `updated` | error | Date not in ISO 8601 format |
| [E004](#e004) | `title` / `tags` | error | Type mismatch |
| [E005](#e005) | frontmatter | error | General schema violation |
| [E006](#e006) | `domain` | error | Value not in configured taxonomy |
| [E007](#e007) | `created` / `updated` | error | `created` date is later than `updated` date |
| [E008](#e008) | `related` | error | Typed relationship label not in `relationship_types` |

---

## E001 — Invalid Enum Value {#e001}

**Field:** `type`, `level`, or `status`

**Trigger:** The value is not in the allowed set defined in `akf.yaml`.

**Example:**
```yaml
type: tutorial   # not in ["concept", "guide", "reference", "checklist", ...]
```

**Repair instruction sent to LLM:**
```
The 'type' field must be one of: [concept, guide, reference, checklist, project, roadmap, template, audit].
You used 'tutorial' which is not in the allowed set. Choose the closest match.
```

**Fix:** Use a value from your `enums.type` (or `enums.level` / `enums.status`) list in `akf.yaml`.

---

## E002 — Required Field Missing {#e002}

**Field:** Any required field

**Trigger:** A required frontmatter field is absent or `null`.

**Required fields:**
- `title`
- `type`
- `domain`
- `level`
- `status`
- `tags`
- `created`
- `updated`

**Example:**
```yaml
---
title: "My Guide"
type: guide
# domain is missing
level: intermediate
status: active
tags: [api, guide]
created: 2026-01-01
updated: 2026-01-01
---
```

**Repair instruction sent to LLM:**
```
The 'domain' field is required but was not found in the frontmatter. Add it.
```

**Fix:** Ensure all required fields are present in the YAML frontmatter.

---

## E003 — Invalid Date Format {#e003}

**Field:** `created` or `updated`

**Trigger:** The date value is not in ISO 8601 format (`YYYY-MM-DD`).

**Examples of invalid dates:**
```yaml
created: "March 6, 2026"    # not ISO 8601
updated: "06/03/2026"       # not ISO 8601
created: 2026-3-6           # missing zero-padding
```

**Valid format:**
```yaml
created: 2026-03-06
updated: 2026-03-11
```

**Repair instruction sent to LLM:**
```
The 'created' field must be a valid ISO 8601 date (YYYY-MM-DD).
You used 'March 6, 2026' which is not valid. Use '2026-03-06'.
```

---

## E004 — Type Mismatch {#e004}

**Field:** `title` or `tags`

**Trigger:** The value has the wrong type.

**Common cases:**

| Field | Expected | Received | Example |
|-------|----------|---------|---------|
| `tags` | `list` | `string` | `tags: "security"` instead of `tags: [security]` |
| `tags` | `list` with ≥ 3 items | list with < 3 items | `tags: [api]` |
| `title` | `string` | `list` | `title: [My, Guide]` |

**Example:**
```yaml
tags: "api, security, guide"  # string instead of list
```

**Repair instruction sent to LLM:**
```
The 'tags' field must be a YAML list with at least 3 items.
You used a string 'api, security, guide'. Use: tags: [api, security, guide]
```

---

## E005 — General Schema Violation {#e005}

**Field:** Frontmatter block

**Trigger:** The frontmatter block has a structural issue that does not match a more specific error code — for example, invalid YAML syntax, missing frontmatter delimiters, or an unexpected structure.

**Example:**
```markdown
title: My Guide
type: concept
```
*(Missing `---` frontmatter delimiters)*

**Fix:** Ensure the file starts with `---`, contains valid YAML, and ends the frontmatter block with `---`.

---

## E006 — Taxonomy Violation {#e006}

**Field:** `domain`

**Trigger:** The `domain` value is not in the `taxonomy.domain` list in `akf.yaml`.

**Example:**
```yaml
domain: backend   # not in your akf.yaml taxonomy
```

**Repair instruction sent to LLM:**
```
The 'domain' field must be one of: [api-design, backend-engineering, devops, security, system-design].
You used 'backend' which is not in the taxonomy. Choose the closest match.
```

**Fix options:**
1. Change the `domain` value to one from your configured taxonomy.
2. Add `backend` to `taxonomy.domain` in `akf.yaml` if it belongs in your ontology.

**Telemetry signal:** Elevated E006 retries on a specific domain value indicates a taxonomy **boundary problem** — the LLM's natural category doesn't map cleanly to your configured domains. Use `Scripts/analyze_telemetry.py` to surface these patterns and refine your taxonomy.

---

## E007 — Date Ordering Violation {#e007}

**Field:** `created` and `updated`

**Trigger:** The `created` date is later than the `updated` date, which is logically impossible.

**Example:**
```yaml
created: 2026-03-11
updated: 2026-03-06   # earlier than created
```

**Repair instruction sent to LLM:**
```
The 'created' date (2026-03-11) must not be later than 'updated' (2026-03-06).
Either set 'updated' to today's date or set 'created' to the same as 'updated'.
```

**Fix:** Ensure `created ≤ updated`.

---

## E008 — Invalid Relationship Type {#e008}

**Field:** `related`

**Trigger:** A typed relationship label in `[[Note|label]]` syntax is not in the `relationship_types` list in `akf.yaml`.

**Example:**
```yaml
related:
  - "[[API Design Principles|depends-on]]"  # "depends-on" not in relationship_types
```

**Valid relationship types** (default):
- `implements`
- `requires`
- `extends`
- `references`
- `supersedes`
- `part-of`

**Repair instruction sent to LLM:**
```
The typed relationship label 'depends-on' in 'related' is not in relationship_types:
[implements, requires, extends, references, supersedes, part-of].
Use the closest valid label or use an untyped reference [[Note]].
```

**Fix:** Use a label from your `relationship_types` list in `akf.yaml`, or add `depends-on` to the list.

---

## Error Severity

All errors listed above have severity `"error"`, which blocks the file from being written to disk.

In `--strict` mode (`akf validate --strict`), warnings are also promoted to errors.

---

## Using Error Codes in Code

```python
from akf import Pipeline

pipeline = Pipeline(output="./vault/")
result = pipeline.validate("./vault/my-note.md")

for err in result.errors:
    if err.code == "E006":
        print(f"Domain '{err.received}' not in taxonomy")
    elif err.code == "E002":
        print(f"Missing required field: {err.field}")
```

---

## Retry as Signal

When validation fails, AKF converts the error code into a deterministic repair instruction and retries the LLM (up to 3 attempts). If the **same error fires twice on the same field**, the pipeline aborts — this pattern indicates a schema boundary problem, not a model failure.

The append-only telemetry log (`telemetry/events.jsonl`) records every attempt. Use `Scripts/analyze_telemetry.py` to identify which error codes and field values cause the most friction, and refine your `akf.yaml` taxonomy accordingly.

---

## Related Pages

- [Configuration](Configuration) — customize enums and taxonomy
- [CLI Reference](CLI-Reference) — `akf validate` command
- [Python API](Python-API) — `ValidationError` dataclass
- [Architecture](Architecture) — how the Error Normalizer works
