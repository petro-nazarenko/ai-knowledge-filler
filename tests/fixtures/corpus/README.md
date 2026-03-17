# Demo Corpus: AI Solutions Architect SOP Library

A set of 47 validated Markdown files representing a realistic SOP library for an AI Solutions Architect practice.

## Organization

- **13 domains** — e.g., Infrastructure, Security, Data Engineering, LLM/AI, Consulting, etc.
- **5 lifecycle phases** — Discovery → Design → Build → Deploy → Audit

## Usage with AKF

```bash
# Validate all files against the default taxonomy
akf validate tests/fixtures/corpus/

# Build a knowledge index from the corpus
akf index --corpus tests/fixtures/corpus/
```

## Entry Point

Start with [`00_Index_MOC.md`](00_Index_MOC.md) — a Map of Content linking to all 47 documents by domain and phase.

## Notes

- All files pass `akf validate` with the default taxonomy (no custom config required).
- Files use standard Markdown with YAML front matter for metadata (title, domain, phase, tags).
- Intended for testing, demos, and development against a realistic knowledge base.
