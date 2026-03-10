---
title: "Prompt Engineering Techniques for Structured Output Generation"
type: guide
domain: ai-system
level: intermediate
status: active
version: v1.0
tags: [prompt-engineering, structured-output, llm, ai-system, techniques]
related:
  - "[[Schema_as_Contract_Pattern]]"
  - "[[LLM_Context_Window_Management]]"
  - "[[Chain_of_Thought_Reasoning]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to prompt engineering techniques that maximize structured output reliability from LLMs — covering schema embedding, few-shot examples, constraint specification, and output repair patterns.

## Prerequisites

- Basic LLM API usage (OpenAI, Claude, Gemini)
- Understanding of YAML/JSON schema
- Familiarity with prompt/completion paradigm

## Technique 1: Schema in System Prompt

Embed the output schema directly in the system prompt as a contract:

```markdown
## OUTPUT SCHEMA (MANDATORY)

Your response MUST be a Markdown file with this exact YAML frontmatter:

---
title: "<string>"
type: "<concept|guide|reference|checklist>"
domain: "<ai-system|api-design|devops|security|system-design>"
level: "<beginner|intermediate|advanced>"
status: "<draft|active|completed|archived>"
tags: [tag1, tag2, tag3]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

Rules:
- type must be EXACTLY one of the listed values
- domain must be EXACTLY one of the listed values
- tags must be a YAML list with 3+ items
```

## Technique 2: Few-Shot Examples

Provide 1–2 complete valid examples before the task:

```markdown
## EXAMPLE OUTPUT

---
title: "REST API Design Principles"
type: reference
domain: api-design
level: intermediate
status: active
tags: [api, rest, design, backend]
created: 2026-03-10
updated: 2026-03-10
---

## Purpose
...

## NOW GENERATE:
Create a reference on GraphQL query optimization.
```

## Technique 3: Constraint Specification

Make constraints explicit with ✅/❌ format:

```markdown
## CONSTRAINTS

✅ Output ONLY the Markdown file — nothing else
✅ YAML frontmatter must be the first element
✅ tags must be a YAML list (not a string)
✅ dates must use ISO 8601 format (YYYY-MM-DD)

❌ No explanation text before or after the file
❌ No code fences around the entire output
❌ No "Here is the file:" preamble
```

## Technique 4: Chain-of-Schema Prompting

Break complex outputs into explicit construction steps:

```markdown
Before generating, complete these steps mentally:
1. Choose the correct type (concept/guide/reference/checklist)
2. Choose the correct domain from: [list]
3. Draft 4–6 relevant tags
4. Confirm: are all required fields present?
5. Now generate the complete file.
```

## Technique 5: Error-Driven Repair

When validation fails, construct a targeted repair prompt:

```python
def build_repair_prompt(document: str, errors: list[str]) -> str:
    error_lines = "\n".join(f"- {e}" for e in errors)
    return f"""Fix ONLY the following validation errors in the document below.
Do not change anything else.

ERRORS TO FIX:
{error_lines}

DOCUMENT:
{document}"""
```

## Output Parsing Techniques

### Robust Frontmatter Extraction

```python
import re
import yaml

def parse_frontmatter(content: str) -> dict:
    # Handle code fences around the file (common LLM artifact)
    content = re.sub(r"^```(?:markdown|yaml)?\n", "", content.strip())
    content = re.sub(r"\n```$", "", content.strip())

    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}
```

## Temperature Recommendations

| Task | Temperature | Rationale |
|------|-------------|-----------|
| Initial generation | 0.3–0.7 | Some creativity for content |
| Schema repair | 0 | Deterministic correction |
| Enum selection | 0 | Fixed vocabulary |
| Content elaboration | 0.5–0.9 | Creative diversity |

## Conclusion

Structured output reliability depends on three factors: explicit schema in system prompt, few-shot examples that match the schema, and temperature=0 for repair passes. Combine these with a validation-retry loop to achieve high schema conformance.
