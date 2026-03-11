# Contributing

Thank you for contributing to AI Knowledge Filler. This page covers how to set up a development environment, run the quality gates, add new providers, and submit pull requests.

---

## Quick Start

```bash
git clone https://github.com/petro-nazarenko/ai-knowledge-filler
cd ai-knowledge-filler
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Verify setup:
```bash
pytest --tb=short      # all tests pass
akf --help             # CLI available
```

---

## Requirements

- Python 3.10+
- `pip`, `git`
- At least one LLM API key for live provider tests (Groq free tier recommended)

---

## Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Or install specific tools
pip install pytest pytest-cov ruff black mypy

# Set at least one API key
export GROQ_API_KEY="gsk_..."       # free tier, recommended for dev
export ANTHROPIC_API_KEY="sk-ant-..." # optional
```

---

## Quality Gates

All pull requests must pass these gates before merge:

```bash
# 1. Tests — 100% must pass
pytest --tb=short

# 2. Coverage — must not decrease below 85%
pytest --cov=. --cov-report=term-missing --cov-fail-under=85

# 3. Format check
black --check .

# 4. Lint
ruff check .

# 5. Type check
mypy cli.py llm_providers.py exceptions.py logger.py akf/ --ignore-missing-imports

# 6. Metadata validation
akf validate --path docs/
```

Tooling source-of-truth policy:
- `pyproject.toml` is the single source of truth for linting/formatting/type-check configuration.
- Primary tools are `ruff`, `black`, and `mypy`.
- Legacy configs (`.flake8`, `.pylintrc`, `.pydocstyle`) are intentionally removed.
Run all at once:
```bash
black --check . && \
ruff check . && \
mypy cli.py llm_providers.py exceptions.py logger.py akf/ --ignore-missing-imports && \
pytest && \
akf validate --path docs/
```

CI runs the same gates on every push via `.github/workflows/ci.yml`, `tests.yml`, and `validate.yml`.

Codecov policy (stabilization phase):
- Codecov upload runs only on `push` to `main` and is non-blocking.
- PR coverage remains blocking through `pytest --cov-fail-under=...`.

GitHub Actions runtime policy:
- Workflows use Node 24-compatible action majors.
- If using self-hosted runners, keep runner version `>=2.327.1`.
- For Docker container action credential-persistence scenarios, use `>=2.329.0`.

---

## Project Structure

```
ai-knowledge-filler/
├── cli.py                  Entry point, command routing
├── llm_providers.py        Provider abstractions and implementations
├── exceptions.py           Typed exception hierarchy
├── logger.py               Logging factory (human + JSON)
├── akf/
│   ├── __init__.py
│   ├── pipeline.py         Pipeline class
│   ├── enricher.py         File reader, YAML extractor, merge logic
│   ├── validator.py        Validation Engine
│   ├── validation_error.py ValidationError dataclass
│   ├── error_normalizer.py ValidationErrors → LLM repair instructions
│   ├── retry_controller.py run_retry_loop() — convergence protection
│   ├── commit_gate.py      Atomic write
│   ├── telemetry.py        Append-only JSONL event stream
│   ├── config.py           Loads akf.yaml or defaults
│   ├── server.py           FastAPI REST API
│   ├── mcp_server.py       MCP server (FastMCP)
│   └── defaults/
│       └── akf.yaml        Default taxonomy
├── Scripts/
│   ├── validate_yaml.py    Standalone YAML validator
│   └── analyze_telemetry.py Telemetry aggregation
├── tests/
│   ├── unit/               Unit tests per module
│   ├── integration/        End-to-end pipeline tests
│   └── conftest.py         Test fixtures
├── docs/                   Documentation
├── wiki/                   GitHub wiki pages
├── akf.yaml                Repo taxonomy config
└── pyproject.toml
```

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

3. **Update CLI** — add to `argparse` choices and `cmd_models()` env var hint in `cli.py`.

4. **Update `pyproject.toml`** optional dependencies.

5. **Write tests** in `tests/test_llm_providers.py` — mock the SDK, test `is_available()`, `generate()`, error handling, and retry behaviour.

---

## Adding a New Domain

Edit `akf/defaults/akf.yaml` to add the domain to the `taxonomy.domain` list:

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
    f.write_text(
        "---\ntitle: Test\ntype: concept\ndomain: ai-system\n"
        "level: intermediate\nstatus: active\ntags: [a,b,c]\n"
        "created: 2026-01-01\nupdated: 2026-01-01\n---\n## Content\n"
    )
    config = get_config()
    validator = Validator(config)
    result = validator.validate(f.read_text())
    assert result.is_valid
```

**Coverage requirement:** do not decrease below 85%. Check with:
```bash
pytest --cov=. --cov-report=term-missing --cov-fail-under=85
```

---

## Fixing a Bug

1. Reproduce with a failing test first
2. Fix the code
3. Confirm the test passes with no regressions
4. Run the full quality gate suite

Known issues are documented in [Architecture](Architecture). If you fix one, remove it from that section in the same PR.

---

## Pull Request Process

1. Fork the repo and create a branch:
   - `feat/short-description` — new feature
   - `fix/short-description` — bug fix
   - `docs/short-description` — documentation only
   - `refactor/short-description` — no behaviour change
   - `chore/short-description` — tooling, deps, CI

2. Make changes with tests
3. Run the full quality gate suite locally
4. Push and open a PR
5. CI will run tests, lint, and `akf validate --path docs/` automatically
6. One approval required before merge

---

## Commit Style

```
type: short description (≤72 chars)

Optional longer explanation.
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `security`

---

## Versioning Policy

AKF follows [Semantic Versioning 2.0.0](https://semver.org/). The public API is declared in [Architecture](Architecture).

| Change | Version Increment | Examples |
|--------|------------------|---------|
| Bug fix, CI fix, docs only | **PATCH** | Fix retry abort, update README |
| New functionality (backward compatible) | **MINOR** | New CLI command, new SDK method |
| Breaking change to public API | **MAJOR** | Remove CLI command, rename REST field |

`1.0.0` means the public API as declared in [Architecture](Architecture) is stable.

---

## Release Process (Maintainers)

1. Bump `version` in `pyproject.toml`
2. Commit: `chore: bump version to X.Y.Z`
3. Tag: `git tag vX.Y.Z && git push origin main && git push origin vX.Y.Z`
4. GitHub Actions `release.yml` builds and publishes to PyPI automatically
5. `changelog.yml` generates `CHANGELOG.md` and commits to main

---

## Questions

Open a GitHub Issue with the `question` label at https://github.com/petro-nazarenko/ai-knowledge-filler/issues.

---

## Related Pages

- [Architecture](Architecture) — module map and design decisions
- [CLI Reference](CLI-Reference) — all commands
- [Installation](Installation) — dev environment setup
