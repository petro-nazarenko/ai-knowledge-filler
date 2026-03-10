---
title: "Product Roadmap Prioritization Frameworks"
type: reference
domain: product-management
level: intermediate
status: active
version: v1.0
tags: [product-management, roadmap, prioritization, frameworks, strategy]
related:
  - "[[Technical_Product_Requirements_Documents]]"
  - "[[Agile_Project_Management_Solo_Developers]]"
  - "[[Risk_Management_Software_Projects]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for product roadmap prioritization frameworks — systematic approaches to choosing what to build next based on value, effort, risk, and strategy.

## Framework 1: RICE Scoring

**Reach × Impact × Confidence / Effort**

```
Reach:      Number of users affected per period
Impact:     Effect on goal metric (0.25=minimal, 0.5=low, 1=medium, 2=high, 3=massive)
Confidence: Certainty in estimates (100%=high, 80%=medium, 50%=low)
Effort:     Person-months to deliver

RICE Score = (Reach × Impact × Confidence) / Effort
```

| Feature | Reach | Impact | Confidence | Effort | RICE |
|---------|-------|--------|------------|--------|------|
| Feature A | 1000 | 2 | 80% | 2 | 800 |
| Feature B | 500 | 3 | 50% | 1 | 750 |
| Feature C | 2000 | 1 | 100% | 5 | 400 |

**Priority:** Feature A → B → C

## Framework 2: ICE Scoring

Simplified RICE without Reach:

```
ICE = Impact × Confidence × Ease (inverse of effort)
```

Quick scoring for early-stage teams or solo developers.

## Framework 3: MoSCoW

Categorical prioritization for release planning:

| Category | Meaning | % of Scope |
|----------|---------|-----------|
| **Must Have** | Release-blocking | 60% |
| **Should Have** | High value, not blocking | 20% |
| **Could Have** | Nice to have | 15% |
| **Won't Have** | Out of scope (this release) | 5% |

**Rule:** If all Must-Haves take longer than deadline allows, remove Should-Haves first.

## Framework 4: Opportunity Scoring (Kano)

Survey users on importance vs satisfaction:
- **Attractive** (delighters) — not expected, big impact when present
- **One-Dimensional** (performance) — more is better
- **Must-Be** (basics) — expected, no delight when present
- **Indifferent** — users don't care

## Framework 5: Value vs Effort Matrix

Plot items on a 2x2:

```
High Value / Low Effort  ← DO FIRST (Quick Wins)
High Value / High Effort ← PLAN CAREFULLY (Big Bets)
Low Value / Low Effort   ← FILL GAPS (Low Priority)
Low Value / High Effort  ← DON'T DO (Time Sinks)
```

## Roadmap Horizons

| Horizon | Timeframe | Certainty | Format |
|---------|-----------|----------|--------|
| Now | 0–3 months | High | Sprint backlog |
| Next | 3–6 months | Medium | Feature list |
| Later | 6–12 months | Low | Themes/outcomes |
| Future | 12+ months | Very low | Vision/strategy |

## Strategic Alignment Check

Before prioritizing, filter against strategy:
1. Does this advance the north star metric?
2. Does this serve our target customer segment?
3. Does this differentiate from competitors?
4. Does this reduce technical debt (sustainable velocity)?

## Anti-Patterns

- **HiPPO effect** — Highest Paid Person's Opinion overrides data
- **Feature factory** — prioritizing features over outcomes
- **Roadmap as commitment** — roadmaps are plans, not contracts
- **Ignoring tech debt** — short-term speed at long-term velocity cost

## Conclusion

RICE is the most widely used quantitative framework. Use Value vs Effort matrix for quick whiteboard sessions. Whatever framework you choose, make the scoring criteria explicit and revisit priorities monthly — markets change faster than annual plans.
