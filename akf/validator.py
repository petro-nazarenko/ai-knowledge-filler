"""
AKF Phase 2.4 — Validation Engine (Model D)
ADR-001: Validation Layer Architecture

Binary judgment: VALID or INVALID. No intermediate states.

Enforces:
  - Required fields (E002)
  - title isinstance str (E004) — CANON-DEFER-003 ✅
  - Enum fields: type, level, status (E001) — via get_config() — CANON-DEFER-001 ✅
  - Domain taxonomy (E006) — via get_config() — CANON-DEFER-001 ✅
  - Date format ISO 8601 (E003)
  - created ≤ updated (E007) — CANON-DEFER-002 ✅
  - Tags array min 3 items (E004)
  - Typed related links [[Note|type]] validated against allowed types (E008)

Changelog:
  - Phase 2.2 (Model C): E006 promoted to error, E001–E006 enforced
  - Phase 2.4 (Model D):
      CANON-DEFER-001: enums + taxonomy loaded from get_config() (akf.yaml)
      CANON-DEFER-002: created ≤ updated semantic constraint (E007)
      CANON-DEFER-003: title isinstance str enforcement (E004)
  - Phase 2.5 (Model E):
      Typed relationships: [[Note|type]] syntax with E008_INVALID_RELATIONSHIP_TYPE
"""

import re
from datetime import date as DateType
from pathlib import Path
from typing import Any

import yaml

from akf.config import get_config
from akf.validation_error import (
    ErrorCode,
    Severity,
    ValidationError,
    date_sequence_violation,
    invalid_date_format,
    invalid_enum,
    invalid_relationship_type,
    missing_field,
    taxonomy_violation,
    type_mismatch,
)

# ---------------------------------------------------------------------------
# Static constraints (not configurable — structural, not ontological)
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "title", "type", "domain", "level",
    "status", "tags", "created", "updated",
]

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

TAGS_MIN = 3

# Matches [[Note Name]] (untyped) or [[Note Name|rel-type]] (typed).
# Group 1: note name; Group 2: relationship type (optional).
_RELATED_LINK_RE = re.compile(r"^\[\[([^\|\]]+?)(?:\|([^\]]+))?\]\]$")


# ---------------------------------------------------------------------------
# Validation Engine
# ---------------------------------------------------------------------------

def validate(document: str, taxonomy_path: Path | None = None) -> list[ValidationError]:
    """
    Validate a Markdown document with YAML frontmatter.
    Returns list of ValidationError. Empty = VALID.

    taxonomy_path: legacy parameter, kept for backwards compatibility.
                   Ignored when akf.yaml config is present.
                   If no config found, falls back to _load_taxonomy(taxonomy_path).
    """
    errors: list[ValidationError] = []

    metadata, parse_error = _parse_frontmatter(document)
    if parse_error:
        errors.append(parse_error)
        return errors

    # Resolve enums + domains from config (CANON-DEFER-001)
    cfg = get_config()

    # Legacy fallback: if config has no custom domains and taxonomy_path provided,
    # use the old file-based loader. This preserves backwards compatibility
    # for callers that pass taxonomy_path explicitly.
    if taxonomy_path is not None and cfg.source is None:
        valid_domains = _load_taxonomy(taxonomy_path)
    else:
        valid_domains = cfg.domains

    errors.extend(_check_required_fields(metadata))
    errors.extend(_check_title_type(metadata))           # CANON-DEFER-003
    errors.extend(_check_enum_fields(metadata, cfg))     # CANON-DEFER-001
    errors.extend(_check_taxonomy(metadata, valid_domains))
    errors.extend(_check_dates(metadata))                # includes CANON-DEFER-002
    errors.extend(_check_tags(metadata))
    errors.extend(_check_related(metadata, cfg))         # WARNING + E008 typed links

    return errors


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------

def _parse_frontmatter(document: str) -> tuple[dict, ValidationError | None]:
    """Parse YAML frontmatter block from Markdown document."""
    lines = document.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, ValidationError(
            code=ErrorCode.SCHEMA_VIOLATION,
            field="frontmatter",
            expected="--- YAML block ---",
            received="missing or malformed",
        )

    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break

    if end is None:
        return {}, ValidationError(
            code=ErrorCode.SCHEMA_VIOLATION,
            field="frontmatter",
            expected="closing ---",
            received="not found",
        )

    yaml_text = "\n".join(lines[1:end])
    try:
        metadata = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        return {}, ValidationError(
            code=ErrorCode.SCHEMA_VIOLATION,
            field="frontmatter",
            expected="valid YAML",
            received=str(exc),
        )

    return metadata, None


# ---------------------------------------------------------------------------
# Field checkers
# ---------------------------------------------------------------------------

def _check_required_fields(metadata: dict) -> list[ValidationError]:
    return [missing_field(f) for f in REQUIRED_FIELDS if f not in metadata]


def _check_title_type(metadata: dict) -> list[ValidationError]:
    """
    CANON-DEFER-003: title must be a string.

    PyYAML may parse unquoted numeric titles (e.g. `title: 42`) as int/float.
    This is a schema contract violation — title is always str.
    """
    title = metadata.get("title")
    if title is None:
        return []  # caught by _check_required_fields
    if not isinstance(title, str):
        return [type_mismatch("title", str, title)]
    return []


def _check_enum_fields(metadata: dict, cfg=None) -> list[ValidationError]:
    """
    CANON-DEFER-001: enum values loaded from config, not hardcoded.

    Falls back to module-level defaults only if cfg is None (should not happen
    in normal operation — get_config() always returns a valid AKFConfig).
    """
    if cfg is None:
        cfg = get_config()

    errors = []
    checks = [
        ("type",   cfg.enums.type),
        ("level",  cfg.enums.level),
        ("status", cfg.enums.status),
    ]
    for field_name, valid_values in checks:
        value = metadata.get(field_name)
        if value is not None and value not in valid_values:
            errors.append(invalid_enum(field_name, valid_values, value))
    return errors


def _check_taxonomy(metadata: dict, valid_domains: list[str]) -> list[ValidationError]:
    domain = metadata.get("domain")
    if domain is not None and domain not in valid_domains:
        return [taxonomy_violation("domain", domain, valid_domains)]
    return []


def _check_dates(metadata: dict) -> list[ValidationError]:
    """
    Validate ISO 8601 date fields + semantic constraint created ≤ updated.

    Fix (audit finding #2): PyYAML parses unquoted YYYY-MM-DD values as
    datetime.date objects, not strings. We handle both cases explicitly.

    CANON-DEFER-002: created ≤ updated constraint.
    Fires E007_SEMANTIC_VIOLATION when created > updated.
    """
    errors = []
    resolved: dict[str, DateType | None] = {}

    for field_name in ("created", "updated"):
        value = metadata.get(field_name)
        if value is None:
            resolved[field_name] = None
            continue

        # PyYAML auto-converts unquoted YYYY-MM-DD → datetime.date
        if isinstance(value, DateType):
            resolved[field_name] = value
            continue

        # String: must match ISO 8601 pattern
        if not DATE_PATTERN.match(str(value)):
            errors.append(invalid_date_format(field_name, str(value)))
            resolved[field_name] = None
        else:
            # Parse string to date for cross-field comparison
            try:
                resolved[field_name] = DateType.fromisoformat(str(value))
            except ValueError:
                errors.append(invalid_date_format(field_name, str(value)))
                resolved[field_name] = None

    # CANON-DEFER-002: created ≤ updated (E007_DATE_SEQUENCE)
    c = resolved.get("created")
    u = resolved.get("updated")
    if c is not None and u is not None and c > u:
        errors.append(date_sequence_violation(c, u))

    return errors


def _check_tags(metadata: dict) -> list[ValidationError]:
    """Validate tags field: must be a list with >= TAGS_MIN items."""
    tags = metadata.get("tags")
    if tags is None:
        return []
    if not isinstance(tags, list):
        return [type_mismatch("tags", list, tags)]
    if len(tags) < TAGS_MIN:
        return [ValidationError(
            code=ErrorCode.TYPE_MISMATCH,
            field="tags",
            expected=f"list with >= {TAGS_MIN} items",
            received=f"list with {len(tags)} items",
        )]
    return []


def _check_related(metadata: dict, cfg=None) -> list[ValidationError]:
    """
    Validate the related field.

    W001: field missing or empty — warning only, never blocks commit.
    E008: typed link [[Note|type]] uses an unrecognized relationship type.

    Untyped links [[Note]] are always valid (backward compatible).

    Args:
        metadata: Parsed frontmatter dict.
        cfg:      AKFConfig providing relationship_types; loaded via get_config()
                  if not supplied.

    Returns:
        List of ValidationError (W001 warnings and/or E008 errors).
    """
    if cfg is None:
        cfg = get_config()

    related = metadata.get("related")
    if not related:
        return [ValidationError(
            code=ErrorCode.SCHEMA_VIOLATION,
            field="related",
            expected="list with >= 1 WikiLink",
            received="absent" if related is None else "empty list",
            severity=Severity.WARNING,
        )]

    if not isinstance(related, list):
        return [type_mismatch("related", list, related)]

    errors: list[ValidationError] = []
    valid_types = cfg.relationship_types

    for item in related:
        if not isinstance(item, str):
            continue
        match = _RELATED_LINK_RE.match(item.strip())
        if match is None:
            continue  # not a WikiLink — ignore (not our schema to enforce here)
        note_name = match.group(1)
        rel_type = match.group(2)
        if rel_type is not None and rel_type not in valid_types:
            errors.append(invalid_relationship_type(note_name, rel_type, valid_types))

    return errors


# ---------------------------------------------------------------------------
# Legacy taxonomy loader (backwards compatibility — taxonomy_path API)
# ---------------------------------------------------------------------------

def _load_taxonomy(taxonomy_path: Path | None = None) -> list[str]:
    """Legacy loader. Used only when taxonomy_path is passed and no akf.yaml exists."""
    if taxonomy_path and taxonomy_path.exists():
        return _parse_taxonomy_file(taxonomy_path)
    return _default_taxonomy()


def _parse_taxonomy_file(path: Path) -> list[str]:
    domains = []
    pattern = re.compile(r"^####\s+([\w-]+)")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match and "(DEPRECATED" not in line:
            domains.append(match.group(1).strip())
    return sorted(set(domains)) if domains else _default_taxonomy()


def _default_taxonomy() -> list[str]:
    """Legacy fallback — used only when no akf.yaml and no taxonomy_path."""
    return sorted([
        "ai-system", "api-design", "backend-engineering",
        "business-strategy", "consulting", "data-engineering",
        "data-science", "devops", "documentation",
        "e-commerce", "education-tech", "finance",
        "finance-tech", "frontend-engineering", "healthcare",
        "infrastructure", "knowledge-management", "learning-systems",
        "machine-learning", "marketing", "operations",
        "product-management", "project-management", "prompt-engineering",
        "sales", "security", "system-design", "workflow-automation",
    ])
