---
title: "Obsidian Vault Structure for AI-Augmented Workflows"
type: guide
domain: ai-system
level: intermediate
status: active
version: v1.0
tags: [obsidian, vault, knowledge-management, ai-workflow, pkm]
related:
  - "[[Knowledge_Management_Architecture]]"
  - "[[Personal_Knowledge_Management_System_Design]]"
  - "[[Ontology_Governance_for_AI_Generated_Knowledge_Bases]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to structuring an Obsidian vault for AI-augmented knowledge workflows — optimizing for AI generation, validation, and retrieval pipelines.

## Prerequisites

- Obsidian installed
- Basic familiarity with Markdown
- Understanding of YAML frontmatter

## Vault Structure

```
vault/
├── 00-META/              # Vault configuration and meta-docs
│   ├── Domain_Taxonomy.md
│   ├── File_Update_Protocol.md
│   └── System_Prompt.md
├── 01-AI-SYSTEM/         # AI engineering knowledge
├── 02-API-DESIGN/        # API design patterns
├── 03-BACKEND/           # Backend engineering
├── 04-DEVOPS/            # DevOps and infrastructure
├── 05-SECURITY/          # Security concepts and guides
├── 06-DATA/              # Data engineering
├── 07-MACHINE-LEARNING/  # ML and AI/ML
├── 08-TEMPLATES/         # Obsidian Templater templates (excluded from generation)
├── 09-INBOX/             # Unprocessed notes (daily capture)
└── 10-OVERHEAD/          # Meta, logs, telemetry
```

## Folder Numbering Convention

Prefix folders with numbers (01-, 02-) to:
- Control sidebar ordering
- Distinguish navigation folders from content
- Enable quick keyboard navigation

## YAML Frontmatter Standard

Every AI-generated file must include:

```yaml
---
title: "Precise File Title"
type: concept          # concept|guide|reference|checklist
domain: api-design     # must match Domain_Taxonomy.md
level: intermediate    # beginner|intermediate|advanced
status: active         # draft|active|completed|archived
version: v1.0
tags: [tag1, tag2, tag3]
related:
  - "[[Related_Note_1]]"
  - "[[Related_Note_2]]"
created: 2026-03-10
updated: 2026-03-10
---
```

## Template Setup (Obsidian Templater)

```markdown
<%*
  const domain = await tp.system.prompt("Domain?")
  const type = await tp.system.prompt("Type?")
  const title = await tp.system.prompt("Title?")
-%>
---
title: "<% title %>"
type: <% type %>
domain: <% domain %>
level: intermediate
status: draft
tags: []
related: []
created: <% tp.date.now("YYYY-MM-DD") %>
updated: <% tp.date.now("YYYY-MM-DD") %>
---
```

## AI Generation Integration

Configure `akf.yaml` at vault root:

```yaml
vault_path: "./vault"
taxonomy:
  domains:
    - ai-system
    - api-design
    - backend-engineering
    # ...
```

Run generation directly into vault folders:
```bash
akf generate --batch plan.json --model claude --output vault/01-AI-SYSTEM
```

## Graph View Optimization

For useful knowledge graph navigation:
- Every file must have `related` links to 2–5 related notes
- Use consistent WikiLink casing (`[[API_Design]]`, not `[[API Design]]`)
- Avoid orphan notes — every new note links to at least one existing note

## Search Configuration

Enable dataview plugin for querying frontmatter:

```dataview
TABLE type, domain, status
FROM ""
WHERE domain = "api-design"
SORT created DESC
```

## Maintenance Workflow

```
Daily: Capture to 09-INBOX/
Weekly: Process inbox → move to domain folder with proper frontmatter
Monthly: Review domain for stale docs (status: active, updated < 90 days)
Quarterly: Ontology review — add/deprecate domains
```

## Conclusion

A numbered folder structure with strict YAML frontmatter and a Domain Taxonomy file creates the foundation for AI-augmented knowledge management. The vault becomes both human-readable and machine-processable — enabling automated generation, validation, and graph-based navigation.
