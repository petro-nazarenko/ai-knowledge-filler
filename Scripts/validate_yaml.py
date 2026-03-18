#!/usr/bin/env python3
"""YAML metadata validator CLI wrapper.

This script delegates schema checks to akf.validator.validate so there is
one validation source of truth for CLI, API, tests, and standalone script use.
"""

import glob
import re
import sys
from datetime import datetime
from typing import List, Tuple

import yaml

from akf.validator import validate as core_validate
from akf.validation_error import ErrorCode, Severity, ValidationError

# Paths excluded from validation
EXCLUDE_PATTERNS = [
    ".github",
    "README.md",
    "CONTRIBUTING.md",
    "ARCHITECTURE.md",
    "08-TEMPLATES",  # Obsidian Templater files — not knowledge documents
]


def _validate_arrays(metadata: dict, errors: List[str], warnings: List[str]) -> None:
    """Legacy helper kept for compatibility with existing unit tests.

    Canonical validation happens in akf.validator; this helper only preserves
    historical assertions around related WikiLink formatting behavior.
    """
    if "tags" in metadata and not isinstance(metadata["tags"], list):
        errors.append("E004_TYPE_MISMATCH: tags must be an array")

    if "related" in metadata and metadata["related"] is not None:
        if not isinstance(metadata["related"], list):
            errors.append("E004_TYPE_MISMATCH: related must be an array or null")
            return

        for link in metadata["related"]:
            if isinstance(link, str) and not re.match(r"^\[\[.+\]\]$", link.strip("\"' ")):
                errors.append(
                    f"E005_SCHEMA_VIOLATION: invalid WikiLink format in related: '{link}'"
                )

    if "related" not in metadata or metadata.get("related") == []:
        warnings.append("No related links (recommended for knowledge graph)")


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


def _parse_frontmatter(content: str) -> Tuple[dict, List[str]]:
    """Extract and parse YAML frontmatter from Markdown content."""
    errors: List[str] = []

    if not content.startswith("---"):
        return {}, ["No YAML frontmatter found"]

    parts = content.split("---")
    if len(parts) < 3:
        return {}, ["Invalid YAML frontmatter structure"]

    try:
        metadata = yaml.safe_load(parts[1])
    except yaml.YAMLError as exc:
        return {}, [f"YAML parsing error: {exc}"]

    if not metadata:
        return {}, ["Empty YAML frontmatter"]

    return metadata, errors


def _format_validation_error(err: ValidationError) -> str:
    """Convert ValidationError to legacy human-readable CLI line."""
    code = err.code.value if isinstance(err.code, ErrorCode) else str(err.code)
    return f"{code}: field '{err.field}' expected {err.expected!r}, received {err.received!r}"


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

    metadata, parse_errors = _parse_frontmatter(content)
    if parse_errors:
        return parse_errors, []

    _ = metadata  # Parsing ensures consistent frontmatter diagnostics.

    try:
        validation_errors = core_validate(content)
    except Exception as exc:
        return [f"Unexpected error: {exc}"], []

    for err in validation_errors:
        line = _format_validation_error(err)
        if err.severity == Severity.WARNING:
            warnings.append(line)
        else:
            errors.append(line)

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

    md_files = [f for f in all_files if not any(x in f for x in EXCLUDE_PATTERNS)]

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
