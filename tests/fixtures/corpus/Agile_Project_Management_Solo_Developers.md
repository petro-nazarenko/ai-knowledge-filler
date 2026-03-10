---
title: "Agile Project Management for Solo Developers"
type: guide
domain: project-management
level: beginner
status: active
version: v1.0
tags: [agile, project-management, solo-developer, productivity, planning]
related:
  - "[[Risk_Management_Software_Projects]]"
  - "[[Product_Roadmap_Prioritization_Frameworks]]"
  - "[[Technical_Product_Requirements_Documents]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to applying Agile project management principles as a solo developer — adapting team-oriented frameworks (Scrum, Kanban) for individual productivity and sustainable delivery.

## Prerequisites

- Active software project (personal or freelance)
- Basic understanding of Agile concepts
- Any task management tool (GitHub Projects, Notion, Linear, or even paper)

## Why Agile for Solo Developers?

Traditional Agile was designed for teams but its core principles apply individually:
- Iterative delivery (no big-bang releases)
- Prioritization discipline (work on highest value first)
- Regular reflection (catch problems early)
- Sustainable pace (avoid burnout)

## Personal Kanban

The simplest Agile framework for solo work:

```
BACKLOG | TODO (this week) | IN PROGRESS | DONE
   Many |           3–5   |      1      | Always
```

**Rules:**
- Never have more than 1 item in progress
- Limit TODO to what you can realistically complete this week
- Review weekly: promote from backlog to TODO

**Tools:** GitHub Projects, Trello, Notion, or a physical whiteboard

## Personal Scrum (1-Week Sprints)

```
Monday    Sprint Planning (30 min): Pick this week's tasks
Daily     Check-in (5 min): What did I do? What will I do? Blockers?
Friday    Sprint Review (15 min): What was delivered?
Friday    Retrospective (15 min): What to improve next week?
```

### Sprint Planning Template

```markdown
## Sprint 2026-03-10 — 2026-03-14

Goal: Ship batch generation feature with error handling

Tasks:
- [ ] Implement retry loop with error context (3h)
- [ ] Add telemetry events for batch mode (2h)
- [ ] Write unit tests for batch_generate() (2h)
- [ ] Update CLI help text (30min)
- [ ] Release v0.5.3 to PyPI (1h)

Capacity: ~20h (exclude meetings, admin)
```

### Retrospective Template

```markdown
## Retrospective 2026-03-14

What went well:
- Finished batch feature 1 day early
- Tests caught 2 regressions before release

What didn't:
- Underestimated CLI changes (took 3h, not 30min)
- Context switching between docs and code

Improvements:
- Time-box doc writing to 1h blocks
- Add "spikes" for unknown complexity tasks
```

## Story Points for Solo

Use simple T-shirt sizing:
- **S (1h):** Clear task, no unknowns
- **M (2–4h):** Some complexity, mostly known
- **L (1 day):** Significant complexity
- **XL (2+ days):** Break down first

**Track velocity:** How many hours of S+M+L you typically deliver per week. Use this for realistic sprint planning.

## GitHub Issues as Backlog

```markdown
# Issue Template

## Description
What needs to be built and why.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Size
S / M / L / XL

## Labels
feature, bug, docs, refactor
```

## Definition of Done

Personal DoD prevents scope creep:
- [ ] Code written and passing tests
- [ ] Tests written (≥ unit tests for new functions)
- [ ] CHANGELOG updated
- [ ] Docs updated if behavior changes
- [ ] Deployed/released if applicable

## Avoiding Burnout

- Never commit to more than 80% of capacity in a sprint
- "Slack" tasks (20%): refactoring, exploration, learning
- No sprint carries over more than 2 uncompleted items
- Take a full week "off" the project quarterly

## Conclusion

Agile for solo developers means Kanban for continuous flow or 1-week sprints for project-oriented work. The key disciplines: weekly prioritization, single in-progress item, and honest retrospection. Adapt the framework to your energy and workflow — consistency matters more than ceremony.
