"""Unit tests for Phase 1.6 schema validation features.

Covers:
- WikiLink format validation in related field (_validate_arrays)
- strict mode in validate_file
"""

import os
import textwrap
import tempfile

import pytest

from Scripts.validate_yaml import _validate_arrays, validate_file

# ─── VALID FRONTMATTER for reuse ─────────────────────────────────────────────

VALID_FM = textwrap.dedent("""\
    ---
    title: "Test File"
    type: concept
    domain: ai-system
    level: intermediate
    status: active
    tags: [ai, test, validation]
    related:
      - "[[Valid Link]]"
      - "[[Another Link]]"
    created: 2026-02-19
    updated: 2026-02-19
    ---

    ## Overview

    Content here.
""")

# Valid structure but missing related → will produce warning
WARN_FM = textwrap.dedent("""\
    ---
    title: "Test"
    type: concept
    domain: ai-system
    level: intermediate
    status: active
    tags: [a, b, c]
    created: 2026-02-19
    updated: 2026-02-19
    ---

    ## Content
""")


# ─── WIKILINK VALIDATION ──────────────────────────────────────────────────────


class TestWikiLinkValidation:
    """Tests for [[WikiLink]] format enforcement in related field."""

    def test_valid_wikilinks_pass(self):
        errors, warnings = [], []
        _validate_arrays(
            {"tags": ["a", "b", "c"], "related": ["[[Valid Link]]", "[[Another]]"]},
            errors,
            warnings,
        )
        assert not errors

    def test_unquoted_plain_text_caught(self):
        errors, warnings = [], []
        _validate_arrays(
            {"tags": ["a", "b", "c"], "related": ["plain text", "[[Valid]]"]},
            errors,
            warnings,
        )
        assert any("WikiLink" in e for e in errors)
        assert "plain text" in str(errors)

    def test_url_in_related_caught(self):
        errors, warnings = [], []
        _validate_arrays(
            {"tags": ["a", "b", "c"], "related": ["https://example.com"]},
            errors,
            warnings,
        )
        assert any("WikiLink" in e for e in errors)

    def test_partial_brackets_caught(self):
        errors, warnings = [], []
        _validate_arrays(
            {"tags": ["a", "b", "c"], "related": ["[Single Bracket]"]},
            errors,
            warnings,
        )
        assert any("WikiLink" in e for e in errors)

    def test_wikilink_with_alias_passes(self):
        errors, warnings = [], []
        _validate_arrays(
            {"tags": ["a", "b", "c"], "related": ["[[Note|Alias]]"]},
            errors,
            warnings,
        )
        assert not errors

    def test_wikilink_with_path_passes(self):
        errors, warnings = [], []
        _validate_arrays(
            {"tags": ["a", "b", "c"], "related": ["[[07-REFERENCE/Domain_Taxonomy]]"]},
            errors,
            warnings,
        )
        assert not errors

    def test_mixed_valid_invalid_reports_all_bad(self):
        errors, warnings = [], []
        _validate_arrays(
            {
                "tags": ["a", "b", "c"],
                "related": ["[[Valid]]", "bad link", "also bad"],
            },
            errors,
            warnings,
        )
        assert any("WikiLink" in e for e in errors)
        assert "bad link" in str(errors)
        assert "also bad" in str(errors)

    def test_empty_related_gives_warning_not_error(self):
        errors, warnings = [], []
        _validate_arrays({"tags": ["a", "b", "c"], "related": []}, errors, warnings)
        assert not errors
        assert any("related" in w.lower() for w in warnings)

    def test_missing_related_gives_warning_not_error(self):
        errors, warnings = [], []
        _validate_arrays({"tags": ["a", "b", "c"]}, errors, warnings)
        assert not errors
        assert warnings


# ─── STRICT MODE ──────────────────────────────────────────────────────────────


class TestStrictMode:
    """Tests for strict=True mode in validate_file."""

    def _tmp(self, content: str) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return f.name

    def test_strict_false_warning_stays_warning(self):
        path = self._tmp(WARN_FM)
        try:
            errors, warnings = validate_file(path, strict=False)
            assert not errors
            assert warnings
        finally:
            os.unlink(path)

    def test_strict_true_warning_becomes_error(self):
        path = self._tmp(WARN_FM)
        try:
            errors, warnings = validate_file(path, strict=True)
            assert errors
            assert not warnings
            assert all("[strict]" in e for e in errors)
        finally:
            os.unlink(path)

    def test_strict_true_real_errors_remain_errors(self):
        fm = textwrap.dedent("""\
            ---
            title: "Test"
            type: INVALID_TYPE
            domain: ai-system
            level: intermediate
            status: active
            tags: [a, b, c]
            created: 2026-02-19
            updated: 2026-02-19
            ---

            ## Content
        """)
        path = self._tmp(fm)
        try:
            errors, warnings = validate_file(path, strict=True)
            assert any("type" in e.lower() for e in errors)
        finally:
            os.unlink(path)

    def test_strict_valid_file_no_errors(self):
        path = self._tmp(VALID_FM)
        try:
            errors, warnings = validate_file(path, strict=True)
            assert not errors
            assert not warnings
        finally:
            os.unlink(path)
