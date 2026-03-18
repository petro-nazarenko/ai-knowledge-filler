"""
Tests — S2: Error Normalizer
AKF Phase 2.1 / ADR-001
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
from akf.error_normalizer import normalize_errors, RetryPayload, _format_list


def _warning(field: str = "title") -> ValidationError:
    return ValidationError(
        code=ErrorCode.SCHEMA_VIOLATION,
        field=field,
        expected="anything",
        received="something",
        severity=Severity.WARNING,
    )


class TestNormalizeErrors:

    def test_empty_list_returns_no_blocking(self):
        result = normalize_errors([])
        assert result.has_blocking_errors is False
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.instructions == []

    def test_single_error_sets_has_blocking(self):
        result = normalize_errors([missing_field("domain")])
        assert result.has_blocking_errors is True
        assert result.error_count == 1
        assert result.warning_count == 0

    def test_single_warning_no_blocking(self):
        result = normalize_errors([_warning()])
        assert result.has_blocking_errors is False
        assert result.error_count == 0
        assert result.warning_count == 1
        assert result.instructions == []

    def test_mixed_errors_and_warnings(self):
        errors = [
            missing_field("type"),
            _warning("title"),
            invalid_enum("level", ["beginner", "advanced"], "expert"),
            _warning("status"),
        ]
        result = normalize_errors(errors)
        assert result.error_count == 2
        assert result.warning_count == 2
        assert result.has_blocking_errors is True
        assert len(result.instructions) == 2

    def test_warnings_never_produce_instructions(self):
        result = normalize_errors([_warning(), _warning("domain")])
        assert result.instructions == []

    def test_pure_function_same_output_twice(self):
        errors = [missing_field("type"), invalid_enum("level", ["a", "b"], "c")]
        r1 = normalize_errors(errors)
        r2 = normalize_errors(errors)
        assert r1.instructions == r2.instructions
        assert r1.error_count == r2.error_count


class TestToPromptText:

    def test_no_errors_returns_empty_string(self):
        payload = normalize_errors([])
        assert payload.to_prompt_text() == ""

    def test_warnings_only_returns_empty_string(self):
        payload = normalize_errors([_warning()])
        assert payload.to_prompt_text() == ""

    def test_prompt_starts_with_header(self):
        payload = normalize_errors([missing_field("domain")])
        text = payload.to_prompt_text()
        assert text.startswith("VALIDATION ERRORS")

    def test_single_error_numbered_1(self):
        payload = normalize_errors([missing_field("domain")])
        text = payload.to_prompt_text()
        assert "1." in text

    def test_two_errors_numbered_1_and_2(self):
        payload = normalize_errors(
            [
                missing_field("domain"),
                missing_field("type"),
            ]
        )
        text = payload.to_prompt_text()
        assert "1." in text
        assert "2." in text

    def test_prompt_contains_field_name(self):
        payload = normalize_errors([missing_field("created")])
        assert "created" in payload.to_prompt_text()

    def test_do_not_modify_sentinel_present(self):
        payload = normalize_errors([missing_field("status")])
        assert "Do not modify any other fields" in payload.to_prompt_text()


class TestRenderers:

    def test_E001_invalid_enum_mentions_received(self):
        e = invalid_enum("level", ["beginner", "advanced"], "expert")
        payload = normalize_errors([e])
        text = payload.to_prompt_text()
        assert "expert" in text
        assert "level" in text
        assert "beginner" in text

    def test_E002_missing_field_says_required(self):
        e = missing_field("type")
        text = normalize_errors([e]).to_prompt_text()
        assert "required" in text.lower() or "missing" in text.lower()
        assert "type" in text

    def test_E003_invalid_date_mentions_YYYY(self):
        e = invalid_date_format("created", "12-02-2026")
        text = normalize_errors([e]).to_prompt_text()
        assert "YYYY-MM-DD" in text
        assert "12-02-2026" in text

    def test_E004_type_mismatch_shows_expected_type(self):
        e = type_mismatch("tags", list, "string_value")
        text = normalize_errors([e]).to_prompt_text()
        assert "tags" in text
        assert "list" in text

    def test_E005_schema_violation_shows_expected_and_received(self):
        e = schema_violation("schema_version", "1.0.0", "absent")
        text = normalize_errors([e]).to_prompt_text()
        assert "schema_version" in text
        assert "1.0.0" in text

    def test_E006_taxonomy_violation_mentions_taxonomy(self):
        domains = ["api-design", "devops", "security"]
        e = taxonomy_violation("domain", "backend", domains)
        text = normalize_errors([e]).to_prompt_text()
        assert "taxonomy" in text.lower()
        assert "backend" in text
        assert "api-design" in text


class TestFormatList:

    def test_list_returns_bracketed_string(self):
        result = _format_list(["a", "b", "c"])
        assert result == '["a", "b", "c"]'

    def test_empty_list(self):
        result = _format_list([])
        assert result == "[]"

    def test_scalar_returns_repr(self):
        result = _format_list("scalar")
        assert result == "'scalar'"

    def test_single_item_list(self):
        result = _format_list(["only"])
        assert '"only"' in result
