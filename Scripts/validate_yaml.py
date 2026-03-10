#!/usr/bin/env python3
"""YAML Metadata Validator for AI Knowledge Filler.

This module validates Markdown files against the Metadata Template Standard
defined in the AI Knowledge Filler system. It checks for required fields,
valid enum values, proper date formats, and structural compliance.

Model C (Phase 2.2): Hard enum enforcement for all taxonomy fields.
  - domain  → E006_TAXONOMY_VIOLATION (was: warning)
  - type    → E001_INVALID_ENUM
  - level   → E001_INVALID_ENUM
  - status  → E001_INVALID_ENUM

Example:
    Run validation on all Markdown files in the repository::

        $ python validate_yaml.py

    The script will output validation results for each file and exit with
    code 0 if all files are valid, or code 1 if any errors are found.

Attributes:
    VALID_TYPES (list): Valid values for the 'type' metadata field.
    VALID_LEVELS (list): Valid values for the 'level' metadata field.
    VALID_STATUSES (list): Valid values for the 'status' metadata field.
    VALID_DOMAINS (list): Valid values for the 'domain' metadata field.
"""

import glob
import sys
from datetime import datetime
from typing import List, Tuple

import re
import yaml

# Valid enum values
VALID_TYPES = [
    "concept",
    "guide",
    "reference",
    "checklist",
    "project",
    "roadmap",
    "template",
    "audit",
]
VALID_LEVELS = ["beginner", "intermediate", "advanced"]
VALID_STATUSES = ["draft", "active", "completed", "archived"]

# Valid domains — must stay in sync with akf/config.py _DEFAULT_DOMAINS
VALID_DOMAINS = [
    "ai-system",
    "api-design",
    "backend-engineering",
    "business-strategy",
    "consulting",
    "data-engineering",
    "devops",
    "frontend-engineering",
    "machine-learning",
    "mobile-engineering",
    "ontology",
    "product-management",
    "project-management",
    "security",
    "system-design",
    "testing",
    "ux-design",
]

# Paths excluded from validation
EXCLUDE_PATTERNS = [
    ".github",
    "README.md",
    "CONTRIBUTING.md",
    "ARCHITECTURE.md",
    "08-TEMPLATES",  # Obsidian Templater files — not knowledge documents
]


def validate_date_format(date_str: str) -> bool:
    """Validate that a date string is in ISO 8601 format (YYYY-MM-DD).

    Args:
        date_str: The date string to validate.

    Returns:
        True if the date is in valid ISO 8601 format, False otherwise.

    Example:
        >>> validate_date_format("2025-02-12")
        True
        >>> validate_date_format("12-02-2025")
        False
    """
    try:
        datetime.strptime(str(date_str), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validate_enum_fields(metadata: dict, errors: List[str], warnings: List[str]) -> None:
    """Validate enum fields: type, level, status, domain.

    Model C — Hard Enum Enforcement (Phase 2.2):
      All four taxonomy fields produce errors on invalid values.
      domain uses E006_TAXONOMY_VIOLATION; others use E001_INVALID_ENUM.
    """
    # E001_INVALID_ENUM — type
    if "type" in metadata and metadata["type"] not in VALID_TYPES:
        errors.append(
            f"E001_INVALID_ENUM: type '{metadata['type']}' is not valid. "
            f"Must be one of: {', '.join(VALID_TYPES)}"
        )

    # E001_INVALID_ENUM — level
    if "level" in metadata and metadata["level"] not in VALID_LEVELS:
        errors.append(
            f"E001_INVALID_ENUM: level '{metadata['level']}' is not valid. "
            f"Must be one of: {', '.join(VALID_LEVELS)}"
        )

    # E001_INVALID_ENUM — status
    if "status" in metadata and metadata["status"] not in VALID_STATUSES:
        errors.append(
            f"E001_INVALID_ENUM: status '{metadata['status']}' is not valid. "
            f"Must be one of: {', '.join(VALID_STATUSES)}"
        )

    # E006_TAXONOMY_VIOLATION — domain (Model C: promoted from warning to error)
    if "domain" in metadata and metadata["domain"] not in VALID_DOMAINS:
        errors.append(
            f"E006_TAXONOMY_VIOLATION: domain '{metadata['domain']}' not in taxonomy. "
            f"Must be one of: {', '.join(VALID_DOMAINS)}"
        )


def _validate_dates(metadata: dict, errors: List[str]) -> None:
    """Validate created and updated date fields."""
    if "created" in metadata and not validate_date_format(metadata["created"]):
        errors.append(
            f"E003_INVALID_DATE_FORMAT: created '{metadata['created']}'. Use YYYY-MM-DD"
        )

    if "updated" in metadata and not validate_date_format(metadata["updated"]):
        errors.append(
            f"E003_INVALID_DATE_FORMAT: updated '{metadata['updated']}'. Use YYYY-MM-DD"
        )


def _validate_arrays(metadata: dict, errors: List[str], warnings: List[str]) -> None:
    """Validate tags and related array fields."""
    if "tags" in metadata and not isinstance(metadata["tags"], list):
        errors.append("E004_TYPE_MISMATCH: tags must be an array")

    if "related" in metadata and metadata["related"] is not None:
        if not isinstance(metadata["related"], list):
            errors.append("E004_TYPE_MISMATCH: related must be an array or null")

    if "tags" in metadata and isinstance(metadata["tags"], list) and len(metadata["tags"]) < 3:
        warnings.append("Fewer than 3 tags (recommended: 3-10)")

    if "related" in metadata and isinstance(metadata["related"], list):
        for link in metadata["related"]:
            if isinstance(link, str) and not re.match(r'^\[\[.+\]\]$', link.strip('"\' ')):
                errors.append(
                    f"E005_SCHEMA_VIOLATION: invalid WikiLink format in related: "
                    f"'{link}' — use [[...]] syntax"
                )

    if "related" not in metadata or not metadata["related"]:
        warnings.append("No related links (recommended for knowledge graph)")


def _parse_frontmatter(content: str) -> Tuple[dict, List[str]]:
    """Extract and parse YAML frontmatter from Markdown content."""
    errors: List[str] = []

    if not content.startswith("---"):
        return {}, ["No YAML frontmatter found"]

    parts = content.split("---")
    if len(parts) < 3:
        return {}, ["Invalid YAML frontmatter structure"]

    metadata = yaml.safe_load(parts[1])
    if not metadata:
        return {}, ["Empty YAML frontmatter"]

    return metadata, errors


def validate_file(filepath: str, strict: bool = False) -> Tuple[List[str], List[str]]:
    """Validate a single Markdown file's YAML frontmatter.

    Checks for:
        - Presence of YAML frontmatter
        - All required metadata fields (E002_MISSING_FIELD)
        - Hard enum enforcement: type, level, status (E001_INVALID_ENUM)
        - Hard taxonomy enforcement: domain (E006_TAXONOMY_VIOLATION)
        - Correct date formats ISO 8601 (E003_INVALID_DATE_FORMAT)
        - Proper data types for tags/related (E004_TYPE_MISMATCH)
        - WikiLink format in related (E005_SCHEMA_VIOLATION)

    Args:
        filepath: Path to the Markdown file to validate.
        strict: If True, warnings are promoted to errors.

    Returns:
        A tuple containing two lists:
            - errors: Critical validation failures (block commit)
            - warnings: Non-critical issues (logged only)

    Example:
        >>> errors, warnings = validate_file("example.md")
        >>> if not errors:
        ...     print("File is valid!")
    """
    errors: List[str] = []
    warnings: List[str] = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, OSError) as e:
        return [f"Cannot read file: {e}"], []

    try:
        metadata, parse_errors = _parse_frontmatter(content)
        if parse_errors:
            return parse_errors, []

        required_fields = ["title", "type", "domain", "level", "status", "created", "updated"]
        for field in required_fields:
            if field not in metadata:
                errors.append(f"E002_MISSING_FIELD: required field '{field}' is absent")

        _validate_enum_fields(metadata, errors, warnings)
        _validate_dates(metadata, errors)
        _validate_arrays(metadata, errors, warnings)

    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error: {str(e)}")
    except Exception as e:
        errors.append(f"Unexpected error: {str(e)}")

    if strict:
        errors.extend(f"[strict] {w}" for w in warnings)
        warnings = []

    return errors, warnings


def main() -> None:
    """Execute validation on all Markdown files in the repository.

    Scans for .md files recursively, excludes system files and template folders,
    validates each file, and outputs results with color-coded status indicators.

    Exit codes:
        0: All files valid
        1: One or more files have validation errors

    Example:
        >>> main()
        🔍 AI Knowledge Filler - YAML Metadata Validator

        ✅ example.md
        ❌ invalid.md
           ERROR: E006_TAXONOMY_VIOLATION: domain 'backend' not in taxonomy...

        📊 Validation Summary:
           Total files: 2
           ✅ Valid: 1
           ❌ Errors: 1
    """
    print("🔍 AI Knowledge Filler - YAML Metadata Validator\n")

    all_files = glob.glob("**/*.md", recursive=True)

    md_files = [
        f for f in all_files
        if not any(x in f for x in EXCLUDE_PATTERNS)
    ]

    total_files = len(md_files)
    valid_files = 0
    files_with_errors = 0
    files_with_warnings = 0

    for filepath in sorted(md_files):
        errors, warnings = validate_file(filepath)

        if errors:
            files_with_errors += 1
            print(f"❌ {filepath}")
            for error in errors:
                print(f"   ERROR: {error}")
        elif warnings:
            files_with_warnings += 1
            print(f"⚠️  {filepath}")
            for warning in warnings:
                print(f"   WARNING: {warning}")
        else:
            valid_files += 1
            print(f"✅ {filepath}")

    print("\n📊 Validation Summary:")
    print(f"   Total files: {total_files}")
    print(f"   ✅ Valid: {valid_files}")
    print(f"   ⚠️  Warnings: {files_with_warnings}")
    print(f"   ❌ Errors: {files_with_errors}")

    if files_with_errors > 0:
        print(f"\n❌ Validation failed: {files_with_errors} file(s) with errors")
        sys.exit(1)
    else:
        print("\n✅ All files valid!")
        sys.exit(0)


if __name__ == "__main__":
    main()