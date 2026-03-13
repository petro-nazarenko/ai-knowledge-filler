---
title: "ADR-002 — Vault Taxonomy vs Repository Taxonomy"
type: reference
domain: akf-core
level: advanced
status: active
version: v1.0
tags:
  - adr
  - taxonomy
  - akf
  - configuration
created: 2026-03-01
updated: 2026-03-12
---

# ADR-002 — Vault Taxonomy vs Repository Taxonomy

## Status

**Active** — v1.0. Decision: layered akf.yaml with `extends:` key.

## Context

AKF uses `akf.yaml` for taxonomy configuration. Two consumers exist:
- Repository (code, CI, tests) — needs a base taxonomy
- Vault (Obsidian, personal) — may need additional or different domains

Without a layered config, users must duplicate taxonomy or maintain two separate files.

## Decision

Implement `extends:` key in `akf.yaml` to support layered configuration:

```yaml
# vault/akf.yaml
extends: "../akf.yaml"
enums:
  domain:
    - knowledge-management
    - consulting
```

Merge rules:
- `domain` → union of base + surface
- `type`, `level`, `status` → base only (surface cannot override)
- Surface cannot remove base domains

## Implementation Status

**Deferred to v0.6.x** — `extends:` key not yet implemented in `akf/config.py`.

## Consequences

- Multi-tenant and personal vault use cases unblocked
- Base taxonomy remains canonical
- Surface configs extend, never replace

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-03-01 | Initial ADR |
