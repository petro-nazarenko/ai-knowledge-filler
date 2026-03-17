---
title: "New Project Checklist — AI Solutions Architect"
type: checklist
domain: project-management
level: intermediate
status: active
version: v1.0
tags: [checklist, project-kickoff, agile, ai-pipeline, template]
related:
  - "[[Agile_Project_Management_Solo_Developers|extends]]"
  - "[[AI_Pipeline_Reliability_Audit_Checklist|extends]]"
  - "[[Risk_Management_Software_Projects|references]]"
  - "[[Product_Roadmap_Prioritization_Frameworks|requires]]"
created: 2026-03-17
updated: 2026-03-17
---

## Purpose

Reusable project kickoff checklist synthesized from Agile solo practices and AI pipeline reliability standards. Copy this template at the start of every new build or consulting engagement and check off items as you complete them.

**How to use:** Duplicate this file, rename it `[ProjectName]_Project_Checklist.md`, set `status: draft`, and work through each section in order.

---

## Sprint Zero Setup

*Establish the foundation before writing a single line of code.*

### Project Identity
- [ ] Project name and purpose statement written (1–2 sentences)
- [ ] North star metric defined (what does success look like in 90 days?)
- [ ] Target user / customer segment identified
- [ ] Stakeholders mapped (decision-makers, reviewers, end-users)

### Repository & Tooling
- [ ] Git repository initialized with `.gitignore` and `README.md`
- [ ] Branch strategy documented (`main`, `develop`, feature branches)
- [ ] Task management tool set up (GitHub Projects, Linear, or Notion)
- [ ] Personal Kanban board created: `BACKLOG | TODO | IN PROGRESS | DONE`
- [ ] `.env.example` committed (never `.env`)

### Sprint Rhythm
- [ ] Sprint cadence chosen (1-week recommended for solo)
- [ ] Weekly planning slot blocked (Monday, 30 min)
- [ ] Weekly review slot blocked (Friday, 15 min)
- [ ] Retrospective template saved (see Agile guide)

---

## Backlog & Prioritization

*Capture and rank work before the first sprint begins.*

### Backlog Seed
- [ ] All known features/tasks written as GitHub Issues or cards
- [ ] Each item has: Description, Acceptance Criteria, Size (S/M/L/XL)
- [ ] Issues labeled: `feature`, `bug`, `docs`, `refactor`, `spike`

### Prioritization
- [ ] RICE score applied to top 10 backlog items
  - Reach × Impact × Confidence / Effort
- [ ] MoSCoW applied to first release scope:
  - **Must Have** (60%) — release blockers
  - **Should Have** (20%) — high value
  - **Could Have** (15%) — nice to have
  - **Won't Have** (5%) — explicitly deferred
- [ ] Roadmap horizons defined: Now (0–3 mo) / Next (3–6 mo) / Later (6–12 mo)

### Capacity Check
- [ ] Sprint capacity estimated (hours available)
- [ ] Sprint committed to ≤ 80% of capacity (20% slack)
- [ ] No more than 5 items in the "TODO this week" column

---

## Architecture Decision Points

*Resolve key design questions before building.*

### Service Design
- [ ] System boundaries drawn (what is in scope vs out of scope)
- [ ] API-first vs UI-first decision made
- [ ] Sync vs async communication pattern chosen
- [ ] Data store chosen (PostgreSQL / Redis / vector DB / etc.)
- [ ] Authentication strategy selected (OAuth 2.0, API key, JWT)

### AI/LLM Decisions (if applicable)
- [ ] LLM provider chosen and API key confirmed
- [ ] Output schema (YAML/JSON structure) defined before first prompt
- [ ] Domain taxonomy / enum constraints documented
- [ ] Fallback provider configured

### Documentation
- [ ] ADR (Architecture Decision Record) created for each major decision
- [ ] OpenAPI spec skeleton created
- [ ] README updated with project purpose and quick start

---

## AI Pipeline Gates

*Required checks before any LLM pipeline goes to staging.*

### Schema & Validation
- [ ] Output schema defined and versioned (not hardcoded)
- [ ] All required fields enumerated with types and enum constraints
- [ ] Validation is idempotent (same input → same result every time)
- [ ] Blocking vs non-blocking errors classified
- [ ] Schema version tracked in telemetry

### Retry Logic
- [ ] Max retry attempts configured (recommend: 3)
- [ ] Retry prompt includes original errors as explicit context
- [ ] Exponential backoff strategy implemented
- [ ] Convergence check prevents infinite retry on identical errors

### Error Handling
- [ ] LLM timeout errors handled separately from logic errors
- [ ] Empty response detection implemented
- [ ] Auth / rate-limit errors distinguished from transient errors
- [ ] Pipeline never silently swallows validation failures

### Observability
- [ ] Telemetry events emitted at each pipeline stage
- [ ] Generation ID assigned per request for traceability
- [ ] Duration metrics captured (ms)
- [ ] Failed generations recorded (not only successes)

### Storage
- [ ] Files written atomically (commit gate pattern)
- [ ] Path traversal prevention implemented
- [ ] Output directory created if missing

---

## Definition of Done

*A task is only complete when ALL of the following are true.*

### Code Quality
- [ ] Code written and all existing tests pass
- [ ] Unit tests written for new functions (≥ 1 happy path + 1 edge case)
- [ ] No hardcoded secrets or environment values

### Documentation
- [ ] `CHANGELOG.md` entry added for user-visible changes
- [ ] Inline comments added for non-obvious logic
- [ ] OpenAPI spec updated if API surface changed

### Delivery
- [ ] Feature branch merged via PR (or direct commit on solo projects)
- [ ] Deployed to staging and smoke-tested
- [ ] Released / tagged if applicable

---

## Risk Register Seed

*Document known risks at project start. Review weekly.*

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|-----------|
| 1 | LLM provider outage | Medium | High | Configure fallback provider |
| 2 | Schema drift between prompt and validator | High | High | Schema-first design; lock before prompting |
| 3 | Scope creep eating sprint capacity | High | Medium | Strict MoSCoW; defer to backlog |
| 4 | API rate limits in production | Medium | Medium | Implement rate limiting + exponential backoff |
| 5 | [Add project-specific risk] | | | |
| 6 | [Add project-specific risk] | | | |

---

## Sign-Off

**Project Name:** ___________________________
**Start Date:** ___________________________
**Owner:** ___________________________
**Sprint Zero Complete:** [ ] Yes — ready to begin Sprint 1
