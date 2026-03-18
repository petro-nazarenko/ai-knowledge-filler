"""
Tests for AKF Phase 2.1 — ValidationError contract
"""

import pytest
from akf.validation_error import (
    ValidationError,
    ErrorCode,
    Severity,
    missing_field,
    invalid_enum,
    invalid_date_format,
    type_mismatch,
    schema_violation,
    taxonomy_violation,
)


class TestValidationError:

    def test_default_severity_is_error(self):
        err = ValidationError(
            code=ErrorCode.MISSING_FIELD,
            field="domain",
            expected="present",
            received="absent",
        )
        assert err.severity == Severity.ERROR

    def test_to_dict(self):
        err = missing_field("domain")
        d = err.to_dict()
        assert d["code"] == "E002_MISSING_FIELD"
        assert d["field"] == "domain"
        assert d["severity"] == "error"

    def test_str_representation(self):
        err = missing_field("title")
        assert "E002_MISSING_FIELD" in str(err)
        assert "title" in str(err)


class TestErrorCodes:

    def test_missing_field(self):
        err = missing_field("status")
        assert err.code == ErrorCode.MISSING_FIELD
        assert err.severity == Severity.ERROR
        assert err.field == "status"

    def test_invalid_enum(self):
        err = invalid_enum("type", ["concept", "guide", "reference"], "document")
        assert err.code == ErrorCode.INVALID_ENUM
        assert err.received == "document"
        assert "concept" in err.expected

    def test_invalid_date_format(self):
        err = invalid_date_format("created", "12/02/2026")
        assert err.code == ErrorCode.INVALID_DATE_FORMAT
        assert err.expected == "YYYY-MM-DD"
        assert err.received == "12/02/2026"

    def test_type_mismatch(self):
        err = type_mismatch("tags", list, "api")
        assert err.code == ErrorCode.TYPE_MISMATCH
        assert err.expected == "list"
        assert err.received == "str"

    def test_schema_violation(self):
        err = schema_violation("tags", "min 3 items", ["api"])
        assert err.code == ErrorCode.SCHEMA_VIOLATION

    def test_taxonomy_violation(self):
        domains = ["api-design", "system-design", "security"]
        err = taxonomy_violation("domain", "Technology", domains)
        assert err.code == ErrorCode.TAXONOMY_VIOLATION
        assert err.received == "Technology"
        assert domains == err.expected


class TestSeverityPolicy:

    def test_warning_severity(self):
        err = ValidationError(
            code=ErrorCode.SCHEMA_VIOLATION,
            field="title",
            expected="max 60 chars",
            received="a very long title that exceeds the limit",
            severity=Severity.WARNING,
        )
        assert err.severity == Severity.WARNING

    def test_error_blocks_commit(self):
        err = missing_field("domain")
        assert err.severity == Severity.ERROR
        assert err.severity != Severity.WARNING

    def test_all_e_codes_exist(self):
        codes = [c.value for c in ErrorCode]
        assert "E001_INVALID_ENUM" in codes
        assert "E002_MISSING_FIELD" in codes
        assert "E003_INVALID_DATE_FORMAT" in codes
        assert "E004_TYPE_MISMATCH" in codes
        assert "E005_SCHEMA_VIOLATION" in codes
        assert "E006_TAXONOMY_VIOLATION" in codes
