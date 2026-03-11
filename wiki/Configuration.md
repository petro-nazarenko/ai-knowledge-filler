# Configuration

AKF is configured through an `akf.yaml` file in your project directory. This file defines your taxonomy, enum values, and runtime settings. It is the only place you need to change to update your ontology — no code changes required.

---

## Generate a Config File

```bash
akf init
```

Creates `akf.yaml` in the current directory with sensible defaults. Pass `--path` to target a different directory:

```bash
akf init --path ./my-vault
```

Use `--force` to overwrite an existing config:

```bash
akf init --force
```

---

## Full Schema Reference

```yaml
schema_version: "1.0.0"   # required — frozen until breaking schema change
vault_path: "./vault"      # required — where generated files are written

taxonomy:
  domain:                  # domain taxonomy (E006 validates against this list)
    - ai-system
    - api-design
    - backend-engineering
    - data-engineering
    - devops
    - frontend-engineering
    - mobile-engineering
    - platform-engineering
    - product-management
    - project-management
    - security
    - system-design
    - testing-qa

enums:
  type:                    # valid values for the `type` frontmatter field (E001)
    - concept
    - guide
    - reference
    - checklist
    - project
    - roadmap
    - template
    - audit

  level:                   # valid values for the `level` frontmatter field (E001)
    - beginner
    - intermediate
    - advanced

  status:                  # valid values for the `status` frontmatter field (E001)
    - draft
    - active
    - completed
    - archived

relationship_types:        # valid labels for [[Note|label]] typed relationships (E008)
  - implements
  - requires
  - extends
  - references
  - supersedes
  - part-of
```

---

## Fields Reference

### `schema_version`

**Required.** Must be `"1.0.0"`. This value is frozen at the current config schema. When a breaking change occurs, it will increment to `"2.0.0"`.

### `vault_path`

**Required.** Directory where AKF writes generated Markdown files. Relative paths are resolved from the location of `akf.yaml`.

```yaml
vault_path: "./vault"          # relative to akf.yaml
vault_path: "/home/user/notes" # absolute path
```

### `taxonomy.domain`

**Required.** List of valid domain strings. Any generated or enriched file must use a value from this list in its `domain` frontmatter field. Violations produce error code **E006**.

```yaml
taxonomy:
  domain:
    - api-design
    - devops
    - security
```

### `enums.type`

List of valid values for the `type` field. Violations produce error code **E001**.

Default values: `concept`, `guide`, `reference`, `checklist`, `project`, `roadmap`, `template`, `audit`

### `enums.level`

List of valid values for the `level` field. Violations produce error code **E001**.

Default values: `beginner`, `intermediate`, `advanced`

### `enums.status`

List of valid values for the `status` field. Violations produce error code **E001**.

Default values: `draft`, `active`, `completed`, `archived`

### `relationship_types`

List of valid typed relationship labels for the `related` field. Used with Obsidian-style `[[Note|label]]` syntax. Violations produce error code **E008**.

Default values: `implements`, `requires`, `extends`, `references`, `supersedes`, `part-of`

---

## Minimal Config

The minimum valid `akf.yaml` is:

```yaml
schema_version: "1.0.0"
vault_path: "./vault"
taxonomy:
  domain:
    - api-design
```

AKF falls back to bundled defaults for any unspecified enum lists.

---

## Customizing Your Taxonomy

You can freely add, rename, or remove values from the lists. The validator reads from `akf.yaml` at runtime:

```yaml
taxonomy:
  domain:
    - my-custom-domain    # add here — no code changes required
    - another-domain
```

After updating, validate existing files to find stale domain values:

```bash
akf validate --path ./vault/
```

---

## Environment Variables

In addition to `akf.yaml`, AKF respects these environment variables:

### API Keys

| Variable | Provider |
|----------|----------|
| `ANTHROPIC_API_KEY` | Claude |
| `GOOGLE_API_KEY` | Gemini |
| `OPENAI_API_KEY` | GPT-4 |
| `GROQ_API_KEY` | Groq |
| `XAI_API_KEY` | Grok (xAI) |

### Runtime Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `AKF_OUTPUT_DIR` | `.` | Default output directory when `--output` not specified |
| `AKF_TELEMETRY_PATH` | `telemetry/events.jsonl` | Path for the telemetry JSONL log |
| `AKF_CONFIG_PATH` | — | Explicit path to `akf.yaml` (overrides auto-discovery) |
| `AKF_API_KEY` | — | REST API bearer token (optional; if unset, all requests pass) |
| `AKF_CORS_ORIGINS` | `*` | Allowed CORS origins for the REST API server |

---

## Config Discovery Order

AKF looks for `akf.yaml` in the following order:

1. Value of `AKF_CONFIG_PATH` environment variable (if set)
2. `akf.yaml` in the current working directory
3. Bundled defaults at `akf/defaults/akf.yaml` (package fallback)

---

## Versioning Policy

| Change | Version Impact |
|--------|---------------|
| Adding a new domain to `taxonomy.domain` | Non-breaking (MINOR) |
| Adding a new enum value to `type`, `level`, or `status` | Non-breaking (MINOR) |
| Removing or renaming an existing enum value | Breaking (MAJOR) |
| Renaming a top-level key (e.g. `vault_path`) | Breaking (MAJOR) |
| Bumping `schema_version` | Breaking (MAJOR) |

---

## Related Pages

- [CLI Reference](CLI-Reference) — `akf init` command
- [Error Codes](Error-Codes) — how validation errors map to config values
- [Architecture](Architecture) — how config is loaded at runtime
