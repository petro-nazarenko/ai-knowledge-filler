---
title: "Consulting Deliverable Standards for Architecture Projects"
type: reference
domain: consulting
level: intermediate
status: active
version: v1.0
tags: [consulting, deliverables, architecture, standards, quality]
related:
  - "[[AI_Consulting_Engagement_Framework]]"
  - "[[Technical_Documentation_Standards]]"
  - "[[Technical_Product_Requirements_Documents]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for consulting deliverable standards in architecture and technology projects — covering document types, quality criteria, review processes, and formatting guidelines.

## Core Deliverable Types

### 1. Assessment Report

**Purpose:** Document current state findings.

Structure:
```
Executive Summary (1 page)
Methodology
Findings
  - Category 1: [findings + evidence]
  - Category 2: [findings + evidence]
Prioritized Recommendations
Appendix: Data and Analysis
```

Quality criteria:
- Findings backed by evidence (interviews, data, observation)
- Recommendations are actionable (not generic)
- Risk level assigned to each finding (High/Medium/Low)

### 2. Architecture Design Document

**Purpose:** Define target state architecture.

Structure:
```
Problem Statement
Architecture Goals and Constraints
Current State Architecture (as-is)
Target State Architecture (to-be)
  - Component Diagram
  - Data Flow
  - Integration Points
  - Security Model
Architecture Decisions (ADRs)
Migration Plan
Risk Register
```

Quality criteria:
- C4 model diagrams at Context, Container, Component levels
- Each ADR follows: Status, Context, Decision, Consequences
- Migration plan has discrete phases with rollback strategy

### 3. Implementation Roadmap

**Purpose:** Define the path from current to target state.

Structure:
```
Vision and Goals
Success Metrics
Phased Delivery Plan
  - Phase N: Scope, Duration, Dependencies, Risks
Resource Plan
Governance Model
```

Quality criteria:
- Phases are independently deliverable (not one big bang)
- Dependencies explicitly mapped
- Each phase has measurable outcomes

### 4. Technical Review Report

**Purpose:** Evaluate existing system or vendor product.

Structure:
```
Review Scope and Criteria
Evaluation Methodology
Findings by Dimension
  - Architecture
  - Security
  - Scalability
  - Operational Maturity
Overall Assessment
Recommendations
```

## Document Quality Standards

### Executive Summary Rule
Every deliverable must start with a 1-page executive summary:
- Context: What we were asked to do
- Finding: What we found
- Recommendation: What we recommend
- Impact: Why it matters

### Evidence Standards

| Claim Type | Required Evidence |
|-----------|------------------|
| Factual | Data, logs, documentation |
| Expert opinion | Named source, interview notes |
| Benchmark | Published source, date, methodology |
| Risk assessment | Risk scoring criteria documented |

### Visual Standards

- Diagrams: Use consistent notation (C4, BPMN, UML as appropriate)
- Tables: All tables have headers and align data types per column
- Code blocks: Syntax-highlighted, complete and runnable

## Review Process

```
Author draft → Internal peer review (24h) → Client review (48h)
→ Revision round → Final sign-off → Delivery
```

### Internal Review Checklist
- [ ] Executive summary stands alone
- [ ] All findings have evidence citations
- [ ] No confidential client info in internal review copy
- [ ] Diagrams are legible at 100% zoom
- [ ] Spell-check and grammar review complete

## Conclusion

Consulting deliverables are the tangible representation of engagement value. High-quality deliverables are evidence-based, clearly structured, and immediately actionable. The executive summary and recommendation quality are the measures clients use to evaluate engagement success.
