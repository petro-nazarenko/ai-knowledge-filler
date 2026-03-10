---
title: "Schema-as-Contract Pattern for Structured AI Output"
type: guide
domain: ai-system
level: intermediate
status: active
version: v1.0
tags: [schema, contract, structured-output, llm, validation]
related:
  - "[[LLM_Output_Validation_Pipeline_Architecture|implements]]"
  - "[[Prompt_Engineering_Techniques|requires]]"
  - "[[Deterministic_Retry_Logic]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to implementing the schema-as-contract pattern for structured AI output — defining output schemas upfront as binding contracts between system prompts and validation layers.

## Prerequisites

- Basic understanding of YAML/JSON schema
- Familiarity with LLM prompting
- Python or similar language for validation implementation

## What Is Schema-as-Contract?

Schema-as-contract means the output schema is defined before writing prompts, and all generated content must conform to it. The schema is the source of truth — not the LLM's interpretation.

## Step 1: Define the Output Schema

```yaml
# output_schema.yaml
fields:
  required:
    - title    # string, 3-60 chars
    - type     # enum: concept|guide|reference|checklist
    - domain   # enum from taxonomy
    - level    # enum: beginner|intermediate|advanced
    - status   # enum: draft|active|completed|archived
    - tags     # list, min 3 items
    - created  # ISO 8601 date
    - updated  # ISO 8601 date
  optional:
    - version  # string: v1.0
    - related  # list of WikiLinks
```

## Step 2: Embed Schema in System Prompt

```markdown
## OUTPUT CONTRACT

You MUST output valid YAML frontmatter with these exact fields:
- title: string
- type: one of [concept, guide, reference, checklist]
- domain: one of [ai-system, api-design, devops, security]
- level: one of [beginner, intermediate, advanced]
- status: one of [draft, active, completed, archived]
- tags: list of 3+ lowercase strings
- created: YYYY-MM-DD
- updated: YYYY-MM-DD

Violation of this contract will cause generation failure.
```

## Step 3: Implement Validation

```python
from dataclasses import dataclass
from typing import List
import yaml

VALID_TYPES = {"concept", "guide", "reference", "checklist"}
VALID_LEVELS = {"beginner", "intermediate", "advanced"}

def validate(document: str) -> list[str]:
    errors = []
    fm = parse_frontmatter(document)

    for field in ["title", "type", "domain", "level", "status", "tags", "created", "updated"]:
        if field not in fm:
            errors.append(f"E002: Missing required field: {field}")

    if fm.get("type") not in VALID_TYPES:
        errors.append(f"E001: Invalid type: {fm.get('type')}")

    return errors
```

## Step 4: Wire Validation to Generation

```python
def generate_with_contract(prompt: str, schema: dict) -> str:
    content = llm.generate(prompt, build_system_prompt(schema))
    errors = validate(content, schema)

    if errors:
        retry_prompt = build_retry_prompt(content, errors)
        content = llm.generate(retry_prompt, build_system_prompt(schema))

    return content
```

## Contract Versioning

Version your schemas alongside your code:

```
schemas/
  v1.0/output_schema.yaml
  v1.1/output_schema.yaml
changelog:
  v1.1: added `version` field to required
  v1.0: initial schema
```

## Anti-Patterns to Avoid

- **Post-hoc schema** — defining schema after seeing LLM output
- **Loose enums** — accepting any string for type/level fields
- **Silent coercion** — converting invalid values instead of rejecting them
- **Schema in comments** — embedding schema only in human-readable prose

## Conclusion

Schema-as-contract shifts validation left: the schema is defined before prompts are written, making validation deterministic and LLM behavior auditable. Treat the schema as a first-class artifact in your AI system design.
