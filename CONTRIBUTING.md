---
title: "Contributing to AKF"
type: guide
domain: akf-docs
level: intermediate
status: active
version: v0.6.1
tags: [contributing, development, testing, providers, versioning]
related:
  - "ARCHITECTURE.md"
  - "docs/cli-reference.md"
created: 2026-02-06
updated: 2026-03-06
---

# Contributing to AKF

Thank you for contributing to AI Knowledge Filler.

---

## Quick Start

```bash
git clone https://github.com/petrnzrnk-creator/ai-knowledge-filler
cd ai-knowledge-filler
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Verify setup:
```bash
pytest --tb=short        # all tests pass
akf --help               # CLI available
```

---

## Development Environment

**Requirements:** Python 3.10+, pip, git

**Install dev dependencies:**
```bash
pip install -c requirements.lock -e ".[all,dev]"
```

**Environment variables** (set at least one for live provider tests):
```bash
export GROQ_API_KEY="gsk_..."       # free, recommended for dev
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Secrets hygiene (required):**
```bash
# Install and enable hooks once per clone
pre-commit install

# Run all hooks before pushing
pre-commit run --all-files
```

- Never commit `.env`, `.env.local`, or any file with real credentials.
- Keep only examples in `.env.example` and use placeholder values.
- If a secret is committed accidentally: rotate it immediately, purge from history, and notify maintainers.

---

## Quality Gates

All PRs must pass these gates before merge:

```bash
# 1. Tests — 100% must pass
pytest --tb=short

# 2. Coverage — must not decrease below 91%
pytest --cov=. --cov-report=term-missing --cov-fail-under=91

# 3. Format check
black --check .

# 4. Lint — score ≥ 9.0
pylint cli.py llm_providers.py exceptions.py logger.py akf/ --fail-under=9.0

# 5. Type check
mypy cli.py llm_providers.py exceptions.py logger.py akf/ --ignore-missing-imports

# 6. Metadata validation
akf validate --path docs/

# 7. Pre-commit (includes secret checks)
pre-commit run --all-files
```

Run all at once:
```bash
black . && pylint cli.py llm_providers.py exceptions.py logger.py akf/ --fail-under=9.0 && \
mypy cli.py llm_providers.py exceptions.py logger.py akf/ --ignore-missing-imports && pytest && \
akf validate --path docs/ && pre-commit run --all-files
```

CI runs the same gates on every push via `.github/workflows/tests.yml`, `lint.yml`, and `validate.yml`.

> GitHub Actions dependency updates may migrate actions to Node.js 24 runtime.
> If this repository ever moves to self-hosted runners, keep runner version at `>=2.327.1`.

---

## Project Structure

```
ai-knowledge-filler/
├── cli.py                  # Entry point, orchestration
├── llm_providers.py        # Provider abstractions and implementations
├── exceptions.py           # Typed exception hierarchy
├── logger.py               # Logging factory (human + JSON)
├── akf/
│   ├── __init__.py         # Package namespace
│   ├── pipeline.py         # Pipeline class — generate(), enrich(), validate(), batch_generate()
│   ├── enricher.py         # File reader, YAML extractor, merge logic (akf enrich)
│   ├── validator.py        # Validation Engine — binary VALID/INVALID, E001–E007
│   ├── validation_error.py # ValidationError dataclass + error constructors
│   ├── error_normalizer.py # Translates ValidationErrors → LLM retry instructions
│   ├── retry_controller.py # run_retry_loop() — convergence protection, max 3 attempts
│   ├── commit_gate.py      # Atomic write — only VALID files reach disk
│   ├── telemetry.py        # TelemetryWriter, append-only JSONL event stream
│   ├── config.py           # get_config() — loads akf.yaml or defaults
│   ├── server.py           # FastAPI REST API — /v1/generate, /v1/validate, /v1/batch
│   ├── system_prompt.md    # Bundled LLM instruction set (asset)
│   └── defaults/
│       └── akf.yaml        # Default taxonomy and enum configuration
├── Scripts/
│   ├── validate_yaml.py    # Standalone YAML frontmatter validator (CLI utility)
│   └── analyze_telemetry.py # Telemetry analysis — retry rates, ontology friction
├── tests/
│   ├── unit/               # Unit tests per module
│   ├── integration/        # End-to-end pipeline tests
│   └── conftest.py         # Fixtures — forces package defaults, isolates from repo akf.yaml
├── docs/
│   ├── user-guide.md
│   └── cli-reference.md
├── .github/workflows/
│   ├── ci.yml
│   ├── tests.yml
│   ├── lint.yml
│   ├── validate.yml        # akf validate --path docs/ on every PR
│   ├── changelog.yml       # git-cliff CHANGELOG.md on every tag
│   └── release.yml
├── akf.yaml                # Repo taxonomy (akf-core, akf-docs, akf-ops, akf-spec)
├── cliff.toml              # git-cliff changelog config
├── pyproject.toml
├── ARCHITECTURE.md
└── CONTRIBUTING.md         # this file
```

For a deeper module-by-module breakdown, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Adding a New LLM Provider

1. **Subclass `LLMProvider`** in `llm_providers.py`:

```python
class MyProvider(LLMProvider):
    name = "myprovider"
    display_name = "My Provider"
    model_name = "my-model-v1"

    def is_available(self) -> bool:
        return bool(os.getenv("MYPROVIDER_API_KEY")) and _has_package("myprovider_sdk")

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        import myprovider_sdk
        client = myprovider_sdk.Client(api_key=os.getenv("MYPROVIDER_API_KEY"))
        response = client.complete(prompt=prompt, system=system_prompt)
        return response.text
```

2. **Register** in `PROVIDERS` dict and add to `FALLBACK_ORDER` if appropriate.

3. **Add to CLI** — `argparse` choices and `cmd_models()` env var hint in `cli.py`.

4. **Add to `pyproject.toml`** optional dependencies.

5. **Write tests** in `tests/test_llm_providers.py` — mock the SDK, test `is_available()`, `generate()`, error handling, and retry behaviour.

---

## Adding a New Domain

Edit `akf/defaults/akf.yaml` — add the domain to the `taxonomy.domain` list:

```yaml
taxonomy:
  domain:
    - existing-domain
    - my-new-domain      # add here
```

The validator reads from `akf.yaml` at runtime — no code change required. Run `akf validate --path docs/` after to confirm the domain is recognised.

---

## Writing Tests

Tests live in `tests/`. Use `pytest` with mocking for external calls.

**Important:** `tests/conftest.py` forces package defaults for all tests — repo `akf.yaml` is ignored. This prevents E006 taxonomy violations when running tests from the repo directory.

**Test validation:**
```python
from akf.validator import Validator
from akf.config import get_config

def test_valid_file(tmp_path):
    f = tmp_path / "test.md"
    f.write_text("---\ntitle: Test\ntype: concept\ndomain: ai-system\n"
                 "level: intermediate\nstatus: active\ntags: [a,b,c]\n"
                 "created: 2026-01-01\nupdated: 2026-01-01\n---\n## Content\n")
    config = get_config()
    validator = Validator(config)
    result = validator.validate(f.read_text())
    assert result.is_valid
```

**Coverage requirement:** do not decrease below 93%. Check with:
```bash
pytest --cov=. --cov-report=term-missing --cov-fail-under=91
```

---

## Fixing a Bug

1. Reproduce with a failing test first
2. Fix the code
3. Confirm the test passes and no regressions introduced
4. Run full quality gate suite

**Known issues** are documented in [ARCHITECTURE.md — Known Issues](ARCHITECTURE.md#known-issues). If you fix one, remove it from that section in the same PR.

---

## Pull Request Process

1. Fork the repo and create a branch: `git checkout -b fix/my-fix` or `git checkout -b feat/my-feature`
2. Make changes with tests
3. Run the full quality gate suite locally
4. Push and open a PR
5. CI will run tests, lint, and `akf validate --path docs/` automatically
6. One approval required before merge

**Branch naming:**
- `feat/short-description` — new feature
- `fix/short-description` — bug fix
- `docs/short-description` — documentation only
- `refactor/short-description` — no behaviour change
- `chore/short-description` — tooling, deps, CI

---

## Commit Style

```
type: short description (≤72 chars)

Optional longer explanation.
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `security`

---

## Versioning Policy

AKF follows [Semantic Versioning 2.0.0](https://semver.org/). The public API is declared in [ARCHITECTURE.md](ARCHITECTURE.md).

| Change | Increment | Examples |
|--------|-----------|---------|
| Bug fix, CI fix, docs only | **PATCH** | Fix retry abort, update README, fix CI |
| New functionality — backward compatible | **MINOR** | New CLI command, new SDK method, new E-code |
| Breaking change to public API | **MAJOR** | Remove CLI command, rename REST field |

`1.0.0` means: public API as declared in `ARCHITECTURE.md` is stable.

---

## Release Process (maintainers)

1. Bump `version` in `pyproject.toml`
2. Commit: `chore: bump version to X.Y.Z`
3. Tag: `git tag vX.Y.Z && git push origin main && git push origin vX.Y.Z`
4. GitHub Actions `release.yml` builds and publishes to PyPI automatically
5. `changelog.yml` generates `CHANGELOG.md` and commits to main

---

## Questions

Open a GitHub Issue with the `question` label.