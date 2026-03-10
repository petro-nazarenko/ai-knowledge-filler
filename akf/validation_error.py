"""
AKF Phase 2.1 — Validation Error Contract
ADR-001: Validation Layer Architecture
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class ErrorCode(str, Enum):
    INVALID_ENUM = "E001_INVALID_ENUM"
    MISSING_FIELD = "E002_MISSING_FIELD"
    INVALID_DATE_FORMAT = "E003_INVALID_DATE_FORMAT"
    TYPE_MISMATCH = "E004_TYPE_MISMATCH"
    SCHEMA_VIOLATION = "E005_SCHEMA_VIOLATION"
    TAXONOMY_VIOLATION = "E006_TAXONOMY_VIOLATION"
    DATE_SEQUENCE = "E007_DATE_SEQUENCE"  # created > updated semantic violation
    INVALID_RELATIONSHIP_TYPE = "E008_INVALID_RELATIONSHIP_TYPE"


class Severity(str, Enum):
    ERROR = "error"    # blocks commit, triggers retry
    WARNING = "warning"  # allows commit, logged only, never triggers retry


@dataclass
class ValidationError:
    code: ErrorCode
    field: str
    expected: Any
    received: Any
    severity: Severity = Severity.ERROR

    def to_dict(self) -> dict:
        return {
            "code": self.code.value,
            "field": self.field,
            "expected": self.expected,
            "received": self.received,
            "severity": self.severity.value,
        }

    def __str__(self) -> str:
        return (
            f"[{self.severity.value.upper()}] {self.code.value} "
            f"field='{self.field}' "
            f"expected={self.expected!r} "
            f"received={self.received!r}"
        )


# --- Convenience constructors ---

def missing_field(field: str) -> ValidationError:
    return ValidationError(
        code=ErrorCode.MISSING_FIELD,
        field=field,
        expected="present",
        received="absent",
        severity=Severity.ERROR,
    )


def invalid_enum(field: str, expected: list, received: Any) -> ValidationError:
    return ValidationError(
        code=ErrorCode.INVALID_ENUM,
        field=field,
        expected=expected,
        received=received,
        severity=Severity.ERROR,
    )


def invalid_date_format(field: str, received: Any) -> ValidationError:
    return ValidationError(
        code=ErrorCode.INVALID_DATE_FORMAT,
        field=field,
        expected="YYYY-MM-DD",
        received=received,
        severity=Severity.ERROR,
    )


def type_mismatch(field: str, expected: type, received: Any) -> ValidationError:
    return ValidationError(
        code=ErrorCode.TYPE_MISMATCH,
        field=field,
        expected=expected.__name__,
        received=type(received).__name__,
        severity=Severity.ERROR,
    )


def schema_violation(field: str, expected: Any, received: Any) -> ValidationError:
    return ValidationError(
        code=ErrorCode.SCHEMA_VIOLATION,
        field=field,
        expected=expected,
        received=received,
        severity=Severity.ERROR,
    )


def taxonomy_violation(field: str, received: Any, valid_domains: list) -> ValidationError:
    return ValidationError(
        code=ErrorCode.TAXONOMY_VIOLATION,
        field=field,
        expected=valid_domains,
        received=received,
        severity=Severity.ERROR,
    )


def date_sequence_violation(created: Any, updated: Any) -> ValidationError:
    return ValidationError(
        code=ErrorCode.DATE_SEQUENCE,
        field="created/updated",
        expected=f"created ({created}) <= updated ({updated})",
        received=f"created ({created}) > updated ({updated})",
        severity=Severity.ERROR,
    )


def invalid_relationship_type(
    link: str, rel_type: str, valid_types: list
) -> ValidationError:
    """Construct E008 error for an unrecognized typed relationship."""
    return ValidationError(
        code=ErrorCode.INVALID_RELATIONSHIP_TYPE,
        field="related",
        expected=valid_types,
        received=f"[[{link}|{rel_type}]]",
        severity=Severity.ERROR,
    )
