---
title: "Python Packaging Best Practices for PyPI Publishing"
type: guide
domain: backend-engineering
level: intermediate
status: active
version: v1.0
tags: [python, packaging, pypi, publishing, open-source]
related:
  - "[[Backend_Service_Architecture_FastAPI]]"
  - "[[CICD_Pipeline_Design_GitHub_Actions]]"
  - "[[Technical_Documentation_Standards]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Guide to packaging Python projects for PyPI distribution — covering project structure, pyproject.toml configuration, versioning, CI publishing, and dependency management.

## Prerequisites

- Python 3.10+
- Git repository for the project
- PyPI account (test.pypi.org for staging)

## Step 1: Project Structure

```
mypackage/
├── src/
│   └── mypackage/
│       ├── __init__.py
│       └── core.py
├── tests/
│   └── test_core.py
├── pyproject.toml
├── README.md
├── LICENSE
└── CHANGELOG.md
```

**Use `src/` layout** — prevents accidental imports of local package during testing.

## Step 2: pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "1.0.0"
description = "Short description of the package"
readme = "README.md"
license = {file = "LICENSE"}
requires-python = ">=3.10"
authors = [
  {name = "Your Name", email = "you@example.com"},
]
keywords = ["your", "keywords"]
classifiers = [
  "Development Status :: 4 - Beta",
  "Intended Audience :: Developers",
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
]
dependencies = [
  "requests>=2.28.0",
  "pydantic>=2.0",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-cov", "mypy", "ruff"]
mcp = ["mcp>=1.0"]

[project.scripts]
my-cli = "mypackage.cli:main"

[project.urls]
Repository = "https://github.com/user/my-package"
Documentation = "https://my-package.readthedocs.io"
Changelog = "https://github.com/user/my-package/blob/main/CHANGELOG.md"
```

## Step 3: Versioning Strategy

Use semantic versioning (semver):
```
MAJOR.MINOR.PATCH
1.2.3
│ │ └── Bug fixes (backward compatible)
│ └──── New features (backward compatible)
└────── Breaking changes
```

### Single Source of Truth

```toml
# pyproject.toml
[tool.hatch.version]
path = "src/mypackage/__init__.py"
```

```python
# src/mypackage/__init__.py
__version__ = "1.2.3"
```

## Step 4: Building and Testing Locally

```bash
pip install build twine
python -m build                  # creates dist/ directory
twine check dist/*               # validate package
pip install dist/*.whl --dry-run # test installability

# Test on test.pypi.org first
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ my-package
```

## Step 5: Automated Publishing with GitHub Actions

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags: ["v*"]

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write  # OIDC — no password needed
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

**Use OIDC publishing** — no stored API tokens, more secure.

## Dependency Management

- **Pin in lock files, not pyproject.toml** — specify ranges in pyproject.toml
- **Use `>=` lower bounds** — don't over-pin
- **Avoid `==` in library deps** — prevents resolution in user projects
- **Separate dev deps** — use `[dev]` extras

## Conclusion

Use `src/` layout, configure via pyproject.toml, version with semver, and automate publishing via OIDC GitHub Actions. Test on test.pypi.org before every production release. Pin development dependencies strictly; use ranges for library dependencies.
