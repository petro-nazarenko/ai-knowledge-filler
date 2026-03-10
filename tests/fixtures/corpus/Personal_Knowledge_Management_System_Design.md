---
title: "Personal Knowledge Management System Design"
type: reference
domain: system-design
level: intermediate
status: active
version: v1.0
tags: [pkm, knowledge-management, productivity, system-design, obsidian]
related:
  - "[[Obsidian_Vault_Structure_for_AI_Workflows]]"
  - "[[Knowledge_Management_Architecture]]"
  - "[[Ontology_Governance_for_AI_Generated_Knowledge_Bases]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for designing a personal knowledge management (PKM) system — covering capture workflows, organization methods, review cadences, and tool selection.

## Core PKM Methods

### Zettelkasten (Card Index System)

Originally by Niklas Luhmann. Key principles:
- Each note contains **one idea** (atomic)
- Notes are linked to related notes (not folders)
- New ideas emerge from connections between notes

**Best for:** Research, long-form writing, original thinking

### PARA Method (Tiago Forte)

Four categories:
- **Projects** — active goals with deadlines
- **Areas** — ongoing responsibilities without end dates
- **Resources** — reference material for future use
- **Archives** — inactive items from above

**Best for:** Actionability, task management integration

### Johnny Decimal

Numbered categories (10-19 Finance, 20-29 Operations):
- Maximum 10 categories, 10 subcategories each
- Every item has a unique ID
- No searching — navigating

**Best for:** Teams, shared drives, document naming

## System Design Principles

### 1. Capture Ubiquity
Capture ideas immediately — never rely on memory. Mobile apps, voice memos, quick-entry shortcuts.

### 2. Single Inbox
All input goes to one place first (inbox folder). Process periodically — don't organize at capture time.

### 3. Atomic Notes
One concept per note. Long documents that cover multiple concepts should be split.

### 4. Bi-Directional Linking
Every note should be reachable from at least one other note. Orphan notes are invisible notes.

### 5. Progressive Elaboration
Notes start as rough captures and are refined over time. Don't wait for a note to be perfect before saving.

## Tool Selection

| Tool | Paradigm | Best For |
|------|----------|----------|
| Obsidian | Local Markdown + graph | Privacy, offline, extensibility |
| Notion | Database-first | Teams, structured data |
| Roam Research | Graph-first | Dense interlinking, daily notes |
| Logseq | Outline + graph | Open-source Roam alternative |
| Bear | Simple Markdown | Apple ecosystem, simplicity |

## Review Cadences

| Cadence | Action |
|---------|--------|
| Daily | Process inbox, check active projects |
| Weekly | Review project status, clear inbox |
| Monthly | Review areas, update resources |
| Quarterly | Prune archives, review system design |
| Yearly | Full system audit and restructure |

## Capture Sources

- **Reading:** Kindle highlights → Readwise → PKM
- **Web:** Browser extension → PKM
- **Meetings:** Live notes during → process after
- **Ideas:** Mobile quick-capture → inbox
- **Code:** Annotated snippets → reference notes

## Anti-Patterns

- **Collector's fallacy** — capturing without processing
- **Perfect system paralysis** — redesigning instead of using
- **Tool switching** — the tool is not the problem
- **Folder over links** — folders are one-dimensional; links are multi-dimensional

## Conclusion

A PKM system's value is determined by how much you retrieve from it, not how much you put in. Design for retrieval first: atomic notes, consistent linking, and regular review cadences. The best system is the one you actually use.
