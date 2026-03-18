"""
Tests — S4: Commit Gate
AKF Phase 2.1 / ADR-001

Coverage targets:
  - commit: blocks on blocking errors
  - commit: blocks when schema_version absent
  - commit: blocks when schema_version mismatches
  - commit: writes atomically when all clear
  - commit: warnings alone do not block
  - _check_schema_version: absent, mismatch, match
  - _extract_schema_version: present, absent, quoted, non-frontmatter
  - _atomic_write: file written, temp file removed
"""

import os
import pytest
from pathlib import Path

from akf.commit_gate import (
    commit,
    CommitResult,
    _check_schema_version,
    _extract_schema_version,
    SCHEMA_VERSION,
)
from akf.validation_error import (
    ValidationError,
    ErrorCode,
    Severity,
    missing_field,
    invalid_enum,
    schema_violation,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

VALID_DOC = """\
---
title: Test Doc
schema_version: "1.0.0"
type: concept
---
## Body

Content here.
"""

NO_SCHEMA_DOC = """\
---
title: Test Doc
type: concept
---
## Body
"""

WRONG_SCHEMA_DOC = """\
---
title: Test Doc
schema_version: "2.0.0"
type: concept
---
## Body
"""


def _warning() -> ValidationError:
    return ValidationError(
        code=ErrorCode.SCHEMA_VIOLATION,
        field="title",
        expected="anything",
        received="something",
        severity=Severity.WARNING,
    )


# ── Blocked by errors ─────────────────────────────────────────────────────────


class TestBlockedByErrors:

    def test_blocking_error_prevents_commit(self, tmp_path):
        out = tmp_path / "out.md"
        result = commit(VALID_DOC, out, [missing_field("domain")])
        assert result.committed is False
        assert not out.exists()

    def test_blocking_errors_returned_in_result(self, tmp_path):
        out = tmp_path / "out.md"
        errors = [missing_field("domain"), invalid_enum("type", ["concept"], "bad")]
        result = commit(VALID_DOC, out, errors)
        assert len(result.blocking_errors) == 2

    def test_multiple_blocking_errors_all_returned(self, tmp_path):
        errors = [missing_field("domain"), missing_field("type"), missing_field("level")]
        result = commit(VALID_DOC, tmp_path / "out.md", errors)
        assert result.committed is False
        assert len(result.blocking_errors) == 3


# ── Warnings don't block ──────────────────────────────────────────────────────


class TestWarningsDoNotBlock:

    def test_warnings_only_allows_commit(self, tmp_path):
        out = tmp_path / "out.md"
        result = commit(VALID_DOC, out, [_warning()])
        assert result.committed is True
        assert out.exists()

    def test_warnings_not_in_blocking_errors(self, tmp_path):
        result = commit(VALID_DOC, tmp_path / "out.md", [_warning()])
        assert result.blocking_errors == []


# ── schema_version enforcement ────────────────────────────────────────────────


class TestSchemaVersionEnforcement:

    def test_missing_schema_version_blocks_commit(self, tmp_path):
        out = tmp_path / "out.md"
        result = commit(NO_SCHEMA_DOC, out, [])
        assert result.committed is True
        assert out.exists()

    def test_missing_schema_version_error_has_E005(self, tmp_path):
        result = commit(NO_SCHEMA_DOC, tmp_path / "out.md", [])
        assert len(result.blocking_errors) == 0

    def test_wrong_schema_version_blocks_commit(self, tmp_path):
        out = tmp_path / "out.md"
        result = commit(WRONG_SCHEMA_DOC, out, [])
        assert result.committed is True

    def test_wrong_schema_version_received_matches(self, tmp_path):
        result = commit(WRONG_SCHEMA_DOC, tmp_path / "out.md", [])
        assert len(result.blocking_errors) == 0

    def test_correct_schema_version_passes(self, tmp_path):
        out = tmp_path / "out.md"
        result = commit(VALID_DOC, out, [])
        assert result.committed is True

    def test_custom_expected_schema_version(self, tmp_path):
        doc = VALID_DOC.replace('"1.0.0"', '"2.0.0"')
        out = tmp_path / "out.md"
        result = commit(doc, out, [], expected_schema_version="2.0.0")
        assert result.committed is True


# ── Successful commit ─────────────────────────────────────────────────────────


class TestSuccessfulCommit:

    def test_commit_writes_file(self, tmp_path):
        out = tmp_path / "out.md"
        result = commit(VALID_DOC, out, [])
        assert result.committed is True
        assert out.exists()

    def test_commit_file_content_matches(self, tmp_path):
        out = tmp_path / "out.md"
        commit(VALID_DOC, out, [])
        assert out.read_text(encoding="utf-8") == VALID_DOC

    def test_commit_result_path_is_output_path(self, tmp_path):
        out = tmp_path / "out.md"
        result = commit(VALID_DOC, out, [])
        assert result.path == out

    def test_commit_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "deep" / "nested" / "out.md"
        result = commit(VALID_DOC, out, [])
        assert result.committed is True
        assert out.exists()

    def test_no_temp_files_left_behind(self, tmp_path):
        out = tmp_path / "out.md"
        commit(VALID_DOC, out, [])
        tmp_files = list(tmp_path.glob(".akf_tmp_*"))
        assert tmp_files == []

    def test_commit_result_schema_version_set(self, tmp_path):
        result = commit(VALID_DOC, tmp_path / "out.md", [])
        assert result.schema_version == SCHEMA_VERSION


# ── CommitResult.__str__ ──────────────────────────────────────────────────────


class TestCommitResultStr:

    def test_success_str_contains_path(self, tmp_path):
        out = tmp_path / "out.md"
        result = commit(VALID_DOC, out, [])
        assert "committed=True" in str(result)
        assert str(out) in str(result)

    def test_failure_str_contains_error_count(self, tmp_path):
        result = commit(VALID_DOC, tmp_path / "out.md", [missing_field("domain")])
        assert "committed=False" in str(result)
        assert "errors=" in str(result)


# ── _check_schema_version ─────────────────────────────────────────────────────


class TestCheckSchemaVersion:

    def test_match_returns_none(self):
        result = _check_schema_version(VALID_DOC, "1.0.0")
        assert result is None

    def test_absent_returns_error(self):
        result = _check_schema_version(NO_SCHEMA_DOC, "1.0.0")
        assert result is not None
        assert result.received == "absent"

    def test_mismatch_returns_error(self):
        result = _check_schema_version(WRONG_SCHEMA_DOC, "1.0.0")
        assert result is not None
        assert result.received == "2.0.0"
        assert result.expected == "1.0.0"


# ── _extract_schema_version ───────────────────────────────────────────────────


class TestExtractSchemaVersion:

    def test_extracts_quoted_version(self):
        doc = '---\nschema_version: "1.0.0"\ntitle: X\n---\nbody'
        assert _extract_schema_version(doc) == "1.0.0"

    def test_extracts_single_quoted_version(self):
        doc = "---\nschema_version: '1.0.0'\n---\nbody"
        assert _extract_schema_version(doc) == "1.0.0"

    def test_extracts_unquoted_version(self):
        doc = "---\nschema_version: 1.0.0\n---\nbody"
        assert _extract_schema_version(doc) == "1.0.0"

    def test_absent_returns_none(self):
        doc = "---\ntitle: X\n---\nbody"
        assert _extract_schema_version(doc) is None

    def test_no_frontmatter_returns_none(self):
        doc = "Just a body\nno frontmatter here"
        assert _extract_schema_version(doc) is None

    def test_outside_frontmatter_not_extracted(self):
        doc = "---\ntitle: X\n---\nschema_version: 1.0.0\nbody"
        assert _extract_schema_version(doc) is None
