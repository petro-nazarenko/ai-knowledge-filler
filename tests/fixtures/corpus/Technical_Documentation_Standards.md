---
title: "Technical Documentation Standards for Open-Source Projects"
type: guide
domain: product-management
level: intermediate
status: active
version: v1.0
tags: [documentation, open-source, standards, readme, technical-writing]
related:
  - "[[API_Documentation_Structure_OpenAPI]]"
  - "[[Python_Packaging_Best_Practices]]"
  - "[[Knowledge_Management_Architecture]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to technical documentation standards for open-source projects — covering README structure, API docs, changelogs, and contribution guides.

## Prerequisites

- Open-source project with at least one public user
- Markdown knowledge
- Git repository (GitHub/GitLab)

## README Structure

The README is the project's front door. Required sections:

```markdown
# Project Name

One-sentence description.

## What It Does (30 seconds)
Clear value proposition. What problem does it solve?

## Quick Start (5 minutes)
Minimal working example:
```bash
pip install myproject
myproject generate "Create a guide on X"
```

## Installation
Detailed installation for all platforms/configurations.

## Usage
Common use cases with examples.

## Configuration
All configuration options documented.

## Contributing
How to set up development environment and submit changes.

## License
SPDX identifier.
```

## Documentation Types

| Type | Location | Audience | Update Frequency |
|------|----------|----------|-----------------|
| README | repo root | All users | Per major release |
| API Reference | docs/ or /docs site | Developers | Per API change |
| Guides | docs/ | Users | Per feature |
| Changelog | CHANGELOG.md | All | Per release |
| Contributing | CONTRIBUTING.md | Contributors | Quarterly |
| ADRs | docs/decisions/ | Maintainers | Per decision |

## Changelog Format (Keep a Changelog)

```markdown
# Changelog

## [Unreleased]

## [1.2.0] - 2026-03-10

### Added
- `--batch` flag for processing multiple prompts from JSON file
- Claude provider support

### Changed
- Improved error messages for invalid YAML frontmatter

### Fixed
- Path traversal vulnerability in output filename sanitization

### Removed
- Deprecated `--config` flag (use `akf.yaml` instead)
```

## Code Documentation

### Docstrings

```python
def validate(document: str, taxonomy_path: Path | None = None) -> list[ValidationError]:
    """
    Validate a Markdown document with YAML frontmatter.

    Args:
        document: Full Markdown content including frontmatter.
        taxonomy_path: Legacy parameter for backwards compatibility.
                       Ignored when akf.yaml config is present.

    Returns:
        List of ValidationError objects. Empty list means VALID.

    Example:
        >>> errors = validate("---\\ntitle: Test\\n---\\n")
        >>> assert errors  # Missing required fields
    """
```

### Code Comments

- Comment the **why**, not the **what**
- Use TODO/FIXME with issue references: `# TODO(#123): remove after migration`

## Versioned Docs

For APIs with multiple supported versions:
```
docs/
├── v1/
│   └── api-reference.md
├── v2/
│   └── api-reference.md
└── latest -> v2/
```

## Documentation Testing

- **Doctests** — test code examples in docstrings
- **Link checking** — CI job to catch broken links
- **Screenshot freshness** — flag stale UI screenshots

```yaml
# .github/workflows/docs.yml
- name: Check links
  uses: lycheeverse/lychee-action@v1
  with:
    args: --no-progress '**/*.md'
```

## Conclusion

Great documentation is a product feature. Write for the reader who has no context: explain what, why, and how. Keep CHANGELOG current, maintain API docs in code (OpenAPI/docstrings), and test your documentation as rigorously as your code.
