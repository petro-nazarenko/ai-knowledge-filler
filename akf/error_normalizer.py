"""
AKF Phase 2.1 — Error Normalizer
ADR-001: Validation Layer Architecture

Deterministic module.
Input:  list[ValidationError]
Output: RetryPayload (structured text for LLM retry prompt)

Rules:
  - Does NOT re-validate
  - Does NOT decide pass/fail
  - Does NOT mutate the document
  - Pure function — same input always produces same output
"""

from dataclasses import dataclass
from typing import Any

from akf.validation_error import ErrorCode, Severity, ValidationError


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------

@dataclass
class RetryPayload:
    """Structured retry instruction passed to the LLM."""
    instructions: list[str]   # one instruction per blocking error
    error_count: int           # total blocking errors
    warning_count: int         # total warnings (informational only)
    has_blocking_errors: bool  # True → retry required

    def to_prompt_text(self) -> str:
        """
        Render as plain-text block suitable for injection into retry prompt.

        Example output:
            VALIDATION ERRORS — fix the following fields before regenerating:

            1. Field `domain`: must be one of ["api-design", "system-design"].
               You provided: "backend". Replace with a valid enum value.
               Do not modify any other fields.

            2. Field `created`: expected format YYYY-MM-DD.
               You provided: "12-02-2026". Reformat the date only.
               Do not modify any other fields.
        """
        if not self.has_blocking_errors:
            return ""

        lines = [
            "VALIDATION ERRORS — fix the following fields before regenerating:\n"
        ]
        for i, instruction in enumerate(self.instructions, start=1):
            lines.append(f"{i}. {instruction}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------

def normalize_errors(errors: list[ValidationError]) -> RetryPayload:
    """
    Translate structured ValidationError list into a RetryPayload.

    Only ERROR-severity items produce retry instructions.
    WARNING-severity items are counted but never trigger retry.
    """
    blocking = [e for e in errors if e.severity == Severity.ERROR]
    warnings = [e for e in errors if e.severity == Severity.WARNING]

    instructions = [_render_instruction(e) for e in blocking]

    return RetryPayload(
        instructions=instructions,
        error_count=len(blocking),
        warning_count=len(warnings),
        has_blocking_errors=len(blocking) > 0,
    )


# ---------------------------------------------------------------------------
# Per-error-code renderers (deterministic, pure)
# ---------------------------------------------------------------------------

def _render_instruction(error: ValidationError) -> str:
    renderers = {
        ErrorCode.INVALID_ENUM:              _render_invalid_enum,
        ErrorCode.MISSING_FIELD:             _render_missing_field,
        ErrorCode.INVALID_DATE_FORMAT:       _render_invalid_date_format,
        ErrorCode.TYPE_MISMATCH:             _render_type_mismatch,
        ErrorCode.SCHEMA_VIOLATION:          _render_schema_violation,
        ErrorCode.TAXONOMY_VIOLATION:        _render_taxonomy_violation,
        ErrorCode.DATE_SEQUENCE:             _render_date_sequence,
        ErrorCode.INVALID_RELATIONSHIP_TYPE: _render_invalid_relationship_type,
    }
    renderer = renderers.get(error.code, _render_generic)
    return renderer(error)


def _render_invalid_enum(e: ValidationError) -> str:
    expected_str = _format_list(e.expected)
    return (
        f"Field `{e.field}`: must be one of {expected_str}.\n"
        f"   You provided: {e.received!r}. Replace with a valid enum value.\n"
        f"   Do not modify any other fields."
    )


def _render_missing_field(e: ValidationError) -> str:
    if e.field == "domain" and isinstance(e.expected, list):
        domain_list = _format_list(e.expected)
        return (
            f"Field `{e.field}`: required but missing.\n"
            f"   Add this field. Valid values are: {domain_list}.\n"
            f"   Do not modify any other fields."
        )
    return (
        f"Field `{e.field}`: required but missing.\n"
        f"   Add this field with an appropriate value.\n"
        f"   Do not modify any other fields."
    )


def _render_invalid_date_format(e: ValidationError) -> str:
    return (
        f"Field `{e.field}`: expected format YYYY-MM-DD.\n"
        f"   You provided: {e.received!r}. Reformat the date only.\n"
        f"   Do not modify any other fields."
    )


def _render_type_mismatch(e: ValidationError) -> str:
    if e.field == "tags":
        return (
            f"Field `tags`: must be a YAML list (array), not a {e.received!r}.\n"
            f"   Wrong:   tags: api\n"
            f"   Correct: tags: [api, rest, design]\n"
            f"   Minimum 3 items required. Do not modify any other fields."
        )
    return (
        f"Field `{e.field}`: expected type {e.expected!r}, "
        f"got {e.received!r}.\n"
        f"   Correct the type only. Do not modify any other fields."
    )


def _render_schema_violation(e: ValidationError) -> str:
    return (
        f"Field `{e.field}`: schema violation.\n"
        f"   Expected: {e.expected!r}. Received: {e.received!r}.\n"
        f"   Do not modify any other fields."
    )


def _render_taxonomy_violation(e: ValidationError) -> str:
    expected_str = _format_list(e.expected)
    return (
        f"Field `{e.field}`: value must come from the approved taxonomy "
        f"{expected_str}.\n"
        f"   You provided: {e.received!r}. Replace with a taxonomy value.\n"
        f"   Do not modify any other fields."
    )


def _render_date_sequence(e: ValidationError) -> str:
    return (
        f"Field `created`/`updated`: the `created` date must not be after `updated`.\n"
        f"   {e.received}\n"
        f"   Set `updated` to a date >= `created`. Do not modify any other fields."
    )


def _render_invalid_relationship_type(e: ValidationError) -> str:
    valid_str = _format_list(e.expected)
    return (
        f"Field `related`: relationship_type must be one of: {valid_str}.\n"
        f"   You provided: {e.received!r}.\n"
        f"   Use [[Note|type]] format with a valid type, or [[Note]] without type.\n"
        f"   Do not modify any other fields."
    )


def _render_generic(e: ValidationError) -> str:
    return (
        f"Field `{e.field}`: {e.code.value}.\n"
        f"   Expected: {e.expected!r}. Received: {e.received!r}.\n"
        f"   Do not modify any other fields."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_list(value: Any) -> str:
    """Format a list as a compact JSON-style string."""
    if isinstance(value, list):
        items = ", ".join(f'"{v}"' for v in value)
        return f"[{items}]"
    return repr(value)
