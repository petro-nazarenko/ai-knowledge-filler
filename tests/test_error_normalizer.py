"""
Tests for AKF Phase 2.1 — Error Normalizer (S2)
ADR-001: Validation Layer Architecture
"""

import pytest
from akf.error_normalizer import normalize_errors, RetryPayload
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

# ---------------------------------------------------------------------------
# normalize_errors — output contract
# ---------------------------------------------------------------------------


class TestNormalizeErrors:

    def test_empty_list_returns_no_blocking(self):
        result = normalize_errors([])
        assert result.has_blocking_errors is False
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.instructions == []

    def test_single_error_produces_one_instruction(self):
        errors = [missing_field("title")]
        result = normalize_errors(errors)
        assert result.has_blocking_errors is True
        assert result.error_count == 1
        assert len(result.instructions) == 1

    def test_warning_only_no_blocking(self):
        w = ValidationError(
            code=ErrorCode.SCHEMA_VIOLATION,
            field="version",
            expected="vX.Y",
            received="1.0",
            severity=Severity.WARNING,
        )
        result = normalize_errors([w])
        assert result.has_blocking_errors is False
        assert result.error_count == 0
        assert result.warning_count == 1
        assert result.instructions == []

    def test_mixed_errors_and_warnings(self):
        errors = [
            missing_field("title"),
            ValidationError(
                code=ErrorCode.SCHEMA_VIOLATION,
                field="version",
                expected="vX.Y",
                received="1.0",
                severity=Severity.WARNING,
            ),
        ]
        result = normalize_errors(errors)
        assert result.error_count == 1
        assert result.warning_count == 1
        assert result.has_blocking_errors is True

    def test_multiple_errors_produce_multiple_instructions(self):
        errors = [
            missing_field("title"),
            invalid_enum("type", ["concept", "guide"], "document"),
            invalid_date_format("created", "12-02-2026"),
        ]
        result = normalize_errors(errors)
        assert result.error_count == 3
        assert len(result.instructions) == 3


# ---------------------------------------------------------------------------
# RetryPayload.to_prompt_text()
# ---------------------------------------------------------------------------


class TestRetryPayloadPromptText:

    def test_no_blocking_returns_empty_string(self):
        payload = RetryPayload(
            instructions=[],
            error_count=0,
            warning_count=0,
            has_blocking_errors=False,
        )
        assert payload.to_prompt_text() == ""

    def test_prompt_contains_header(self):
        errors = [missing_field("title")]
        payload = normalize_errors(errors)
        text = payload.to_prompt_text()
        assert "VALIDATION ERRORS" in text

    def test_prompt_numbers_instructions(self):
        errors = [
            missing_field("title"),
            missing_field("domain"),
        ]
        payload = normalize_errors(errors)
        text = payload.to_prompt_text()
        assert "1." in text
        assert "2." in text

    def test_prompt_contains_field_name(self):
        errors = [invalid_enum("type", ["concept", "guide"], "document")]
        payload = normalize_errors(errors)
        text = payload.to_prompt_text()
        assert "`type`" in text

    def test_prompt_contains_do_not_modify(self):
        errors = [missing_field("title")]
        payload = normalize_errors(errors)
        text = payload.to_prompt_text()
        assert "Do not modify any other fields" in text


# ---------------------------------------------------------------------------
# Per-error-code instruction rendering
# ---------------------------------------------------------------------------


class TestInstructionRendering:

    def test_invalid_enum_shows_allowed_values(self):
        errors = [invalid_enum("type", ["concept", "guide", "reference"], "document")]
        payload = normalize_errors(errors)
        instr = payload.instructions[0]
        assert "concept" in instr
        assert "guide" in instr
        assert "document" in instr

    def test_missing_field_says_required(self):
        errors = [missing_field("domain")]
        payload = normalize_errors(errors)
        instr = payload.instructions[0]
        assert "required" in instr
        assert "`domain`" in instr

    def test_invalid_date_format_shows_expected_format(self):
        errors = [invalid_date_format("created", "12-02-2026")]
        payload = normalize_errors(errors)
        instr = payload.instructions[0]
        assert "YYYY-MM-DD" in instr
        assert "12-02-2026" in instr

    def test_type_mismatch_shows_expected_and_received_types(self):
        errors = [type_mismatch("tags", list, "api")]
        payload = normalize_errors(errors)
        instr = payload.instructions[0]
        assert "list" in instr

    def test_taxonomy_violation_shows_taxonomy_values(self):
        domains = ["api-design", "system-design", "security"]
        errors = [taxonomy_violation("domain", "backend", domains)]
        payload = normalize_errors(errors)
        instr = payload.instructions[0]
        assert "api-design" in instr
        assert "backend" in instr

    def test_schema_violation_shows_expected_and_received(self):
        errors = [schema_violation("tags", "min 3 items", ["only-one"])]
        payload = normalize_errors(errors)
        instr = payload.instructions[0]
        assert "`tags`" in instr


# ---------------------------------------------------------------------------
# Determinism — same input, same output
# ---------------------------------------------------------------------------


class TestDeterminism:

    def test_same_input_produces_identical_output(self):
        errors = [
            missing_field("title"),
            invalid_enum("type", ["concept", "guide"], "document"),
        ]
        result1 = normalize_errors(errors)
        result2 = normalize_errors(errors)
        assert result1.instructions == result2.instructions
        assert result1.error_count == result2.error_count
        assert result1.to_prompt_text() == result2.to_prompt_text()
