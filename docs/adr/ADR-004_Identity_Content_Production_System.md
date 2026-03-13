---
title: "ADR-004 — Identity: AI-Powered Content Production System"
type: reference
domain: ai-system
level: advanced
status: active
version: v1.0
tags:
  - adr
  - identity
  - positioning
  - architecture
  - akf
related:
  - "[[05-ADR/ADR-001_Validation_Layer_Architecture]]"
  - "[[01-CANON/AKF_Canon_v1_3]]"
  - "[[CURRENT_STATE]]"
created: 2026-03-12
updated: 2026-03-12
---

# ADR-004 — Identity: AI-Powered Content Production System

## Status

**Active** — v1.0, 2026-03-12. Decision: **accepted**.

## Context

AKF was originally positioned as a "deterministic validation pipeline." By v1.0.0 the codebase contained: pipeline, enricher, market_pipeline, rag/indexer, rag/retriever, canvas_generator, mcp_server, llm_providers. The validator is one component among eight.

Three problems with old identity:
1. Identity contradiction — docs described subset of system
2. Audience mismatch — attracted wrong segment
3. Roadmap misalignment — RAG, canvas, market analysis had no home

Full loop confirmed operational (2026-03-12):
corpus → akf index → akf ask → akf generate → akf validate → akf canvas

## Decision

AKF identity: **AI-powered content production system.**

Validator remains quality gate — component of pipeline, not the product.

## What Changes

| Before | After |
|--------|-------|
| "Deterministic validation pipeline" | "AI-powered content production system" |
| Validator = product | Validator = quality gate |
| Target: AI engineers | Target: content producers using AI at scale |
| Obsidian-centric | Any Markdown workflow |

## What Does Not Change

- E001–E008 error taxonomy
- Determinism contract
- Retry = ontology signal
- Commit gate
- All validation guarantees

## Consequences

Positive: identity matches capability, broader audience, clearer roadmap.
Negative: existing "validator only" users may be confused.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-03-12 | Initial ADR |
