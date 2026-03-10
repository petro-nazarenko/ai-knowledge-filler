---
title: "Writing Technical Product Requirements Documents"
type: guide
domain: product-management
level: intermediate
status: active
version: v1.0
tags: [product-management, requirements, prd, documentation, planning]
related:
  - "[[Product_Roadmap_Prioritization_Frameworks]]"
  - "[[Agile_Project_Management_Solo_Developers]]"
  - "[[Technical_Documentation_Standards]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to writing technical product requirements documents (PRDs) that bridge product vision and engineering execution — covering structure, acceptance criteria, and decision recording.

## Prerequisites

- Problem statement and target user defined
- Stakeholder alignment on scope
- Engineering lead identified

## PRD Structure

### 1. Document Header

```markdown
**Product:** Feature/Project Name
**Author:** Name
**Status:** Draft / Review / Approved
**Version:** 1.0
**Created:** 2026-03-10
**Last Updated:** 2026-03-10
**Stakeholders:** PM, Engineering Lead, Design Lead
```

### 2. Problem Statement

Answer three questions:
- What user problem are we solving?
- What evidence shows this is a real problem?
- What is the cost of not solving it?

```markdown
## Problem Statement

Users who generate files in batch mode have no visibility into progress
or failures until the entire batch completes. This results in wasted
time when a single failure at item 3 prevents the user from discovering
the other 47 items would have succeeded.

**Evidence:** Support ticket #234, user interviews (5/10 users affected)
**Business impact:** 23% of batch users report this as their top friction
```

### 3. Goals and Non-Goals

```markdown
## Goals
- Show real-time progress for each batch item
- Report individual failures without stopping the batch
- Allow retry of failed items only

## Non-Goals (this release)
- GUI progress bar
- Email notifications on completion
- Pause/resume functionality
```

### 4. User Stories

```markdown
## User Stories

**As a** developer running a 50-item batch,
**I want** to see each item's status as it processes,
**So that** I can identify failures early and take action.

**Acceptance Criteria:**
- [ ] Each item shows status: pending/processing/done/failed
- [ ] Failed items include error message and error code
- [ ] Exit code 1 if any items fail, 0 if all succeed
- [ ] Total summary shown on completion: "OK: 45 | Failed: 5"
```

### 5. Technical Specification

High-level design decisions for engineering:

```markdown
## Technical Approach

**API contract:** No changes to batch API signature
**Output format:** JSON Lines to stdout (structured for CI/CD parsing)
**Error format:** {"item": N, "status": "failed", "error": "E002 missing field"}

## Open Questions
- [ ] Should failed items be retried automatically? (decision needed by 2026-03-15)
- [ ] Max concurrent workers: 1 (sequential) or N? (PM to decide)
```

### 6. Success Metrics

```markdown
## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Batch user satisfaction | 3.2/5 | 4.0/5 | In-app survey |
| Support tickets (batch) | 12/month | <5/month | Zendesk |
| Batch completion rate | 78% | 90% | Telemetry |
```

### 7. Timeline and Dependencies

```markdown
## Timeline

| Milestone | Date | Owner |
|-----------|------|-------|
| PRD approved | 2026-03-15 | PM |
| Technical design | 2026-03-22 | Eng lead |
| Implementation | 2026-04-05 | Engineering |
| QA | 2026-04-12 | QA |
| Release | 2026-04-19 | PM |

## Dependencies
- CLI refactor (PR #45) must be merged first
```

## Writing Tips

- **One decision per PRD** — don't bundle unrelated features
- **Acceptance criteria are tests** — an engineer can implement exactly what's specified
- **Separate "what" from "how"** — PRD defines what; design doc defines how
- **Record decisions with rationale** — "we chose X because Y, not Z because W"

## Conclusion

A good PRD is the minimum necessary to align stakeholders and unblock engineering. Focus on problem clarity, user stories with testable acceptance criteria, and explicit non-goals. Update it as decisions are made — a PRD that reflects reality is more valuable than a perfect document that was abandoned.
