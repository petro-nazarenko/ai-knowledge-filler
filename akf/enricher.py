"""
akf/enricher.py — File reader, YAML extractor, merge logic, prompt builder.

Part of the akf enrich pipeline (Phase 2.5 / v0.5.0).
"""

from __future__ import annotations

import os
import tempfile
import warnings
from datetime import date
from pathlib import Path
from typing import Any

import yaml

# ─── REQUIRED FIELDS (Canon v1.2) ─────────────────────────────────────────────

REQUIRED_FIELDS: list[str] = [
    "title",
    "type",
    "domain",
    "level",
    "status",
    "tags",
    "created",
    "updated",
]

# ─── PROMPT TEMPLATE ──────────────────────────────────────────────────────────

_PROMPT_TEMPLATE = """\
You are a metadata generator. Analyze the document and generate YAML frontmatter fields.

EXISTING FIELDS (preserve exactly):
{existing_yaml}

MISSING FIELDS TO GENERATE:
{missing_fields}

CONSTRAINTS:
- domain must be one of: {taxonomy_domains}
- type: concept|guide|reference|checklist|project|roadmap|template|audit
- level: beginner|intermediate|advanced
- status: draft|active|completed|archived
- tags: array, minimum 3 items, lowercase-hyphenated
- created: {today}
- updated: {today}

DOCUMENT CONTENT (first 500 chars):
{content_sample}

OUTPUT: valid YAML fields only. No explanation. No markdown fences. No --- delimiters.\
"""


# ─── PUBLIC FUNCTIONS ──────────────────────────────────────────────────────────


def read_file(path: Path) -> tuple[dict[str, Any], str]:
    """Read a Markdown file and return (existing_yaml_dict, body_content).

    If no frontmatter found → ({}, full_content).
    If invalid YAML → ({}, full_content) + emit warning.
    """
    raw = path.read_text(encoding="utf-8")

    if not raw.strip():
        return {}, ""

    if not raw.startswith("---"):
        return {}, raw

    # Split on the second ---
    parts = raw.split("---", 2)
    if len(parts) < 3:
        # Has opening --- but no closing ---
        return {}, raw

    yaml_block = parts[1]
    body = parts[2]

    if not yaml_block.strip():
        return {}, body

    try:
        parsed = yaml.safe_load(yaml_block)
        if not isinstance(parsed, dict):
            warnings.warn(
                f"{path}: frontmatter parsed to {type(parsed).__name__}, expected dict — treating as empty",
                stacklevel=2,
            )
            return {}, body
        return parsed, body
    except yaml.YAMLError as exc:
        warnings.warn(
            f"{path}: YAML parse error ({exc}) — treating as no frontmatter",
            stacklevel=2,
        )
        return {}, raw


def extract_missing_fields(existing: dict[str, Any], required: list[str]) -> list[str]:
    """Return list of field names not present or empty in existing dict."""
    return [
        field
        for field in required
        if field not in existing or existing[field] is None or existing[field] == ""
    ]


def build_prompt(
    body: str,
    existing: dict[str, Any],
    missing: list[str],
    taxonomy_domains: list[str],
    today: str,
) -> str:
    """Build LLM prompt string from template."""
    existing_yaml_str = (
        yaml.dump(existing, default_flow_style=False, allow_unicode=True).strip()
        if existing
        else "(none)"
    )
    missing_fields_str = "\n".join(f"- {f}" for f in missing) if missing else "(none)"
    domains_str = ", ".join(taxonomy_domains)
    content_sample = body.strip()[:500]

    return _PROMPT_TEMPLATE.format(
        existing_yaml=existing_yaml_str,
        missing_fields=missing_fields_str,
        taxonomy_domains=domains_str,
        today=today,
        content_sample=content_sample,
    )


def merge_yaml(
    existing: dict[str, Any],
    generated: dict[str, Any],
    force: bool = False,
    today: str | None = None,
) -> dict[str, Any]:
    """Merge existing + generated YAML dicts.

    Rules:
    - existing fields win unless force=True
    - created: never change if exists
    - updated: always set to today
    - tags: union + deduplicate (preserving order)
    - related: union + deduplicate
    """
    _today = today or date.today().isoformat()
    merged: dict[str, Any] = dict(existing)

    for key, value in generated.items():
        if key == "created":
            # Never overwrite created
            if "created" not in merged or merged["created"] is None:
                merged["created"] = value
            # else: preserve existing
        elif key in ("tags", "related"):
            # Union merge
            existing_list: list[Any] = merged.get(key) or []
            generated_list: list[Any] = value if isinstance(value, list) else [value]
            merged[key] = _deduplicated_union(existing_list, generated_list)
        elif force or key not in merged or merged[key] is None or merged[key] == "":
            merged[key] = value

    # Always refresh updated
    merged["updated"] = _today

    return merged


_ACRONYMS: frozenset[str] = frozenset(
    {
        "akf",
        "ai",
        "api",
        "cli",
        "ci",
        "cd",
        "css",
        "csv",
        "db",
        "dns",
        "gpu",
        "html",
        "http",
        "https",
        "id",
        "io",
        "json",
        "jwt",
        "llm",
        "mcp",
        "ml",
        "orm",
        "os",
        "pdf",
        "pkm",
        "qa",
        "rest",
        "sdk",
        "sql",
        "ssh",
        "tls",
        "ui",
        "url",
        "ux",
        "uuid",
        "vm",
        "vpn",
        "xml",
        "yaml",
    }
)


def derive_title(path: Path) -> str:
    """Derive a human-readable title from a filename.

    Rules:
    - Split on underscores and hyphens
    - Words in _ACRONYMS are uppercased; all others are title-cased

    Examples:
        cli_reference.md  → 'CLI Reference'
        my-doc.md         → 'My Doc'
        rest_api_guide.md → 'REST API Guide'

    Note: only words in the built-in acronym list are uppercased.
    Unknown abbreviations will be title-cased ('Oauth' not 'OAuth').
    Extend _ACRONYMS at module level to add project-specific terms.
    """
    stem = path.stem
    words = stem.replace("-", " ").replace("_", " ").split()
    return " ".join(w.upper() if w.lower() in _ACRONYMS else w.capitalize() for w in words)


def write_back(path: Path, yaml_dict: dict[str, Any], body: str) -> None:
    """Write merged YAML + body back to file atomically.

    Uses temp file + os.replace() — same pattern as commit_gate._atomic_write().
    """
    content = _assemble(yaml_dict, body)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=".akf_enrich_tmp_", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ─── HELPERS ──────────────────────────────────────────────────────────────────


def _assemble(yaml_dict: dict[str, Any], body: str) -> str:
    """Reconstruct full Markdown file from YAML dict + body."""
    frontmatter = yaml.dump(yaml_dict, default_flow_style=False, allow_unicode=True)
    body_stripped = body.lstrip("\n")
    return f"---\n{frontmatter}---\n{body_stripped}"


def _deduplicated_union(a: list[Any], b: list[Any]) -> list[Any]:
    """Return a + b with duplicates removed, preserving insertion order."""
    seen: set[str] = set()
    result: list[Any] = []
    for item in list(a) + list(b):
        key = str(item).lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
