"""
tests/test_validator.py — Phase 2.4/2.5 validator tests

Covers CANON-DEFER-001/002/003 changes and typed relationships (E008).
Existing Phase 2.2/2.3 tests remain untouched.

Fixtures use reset_config() to isolate config state between tests.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import yaml

import pytest

from akf.config import reset_config, load_config, get_config
from akf.error_normalizer import normalize_errors
from akf.validator import validate
from akf.validation_error import ErrorCode, Severity

# ─── helpers ──────────────────────────────────────────────────────────────────

def make_doc(**overrides) -> str:
    """Build a minimal valid document, overriding specific fields."""
    fields = {
        "title": "Test Document",
        "type": "concept",
        "domain": "ai-system",
        "level": "beginner",
        "status": "active",
        "tags": ["a", "b", "c"],
        "related": ["[[Test Link]]"],
        "created": "2026-01-01",
        "updated": "2026-01-02",
    }
    fields.update(overrides)

    frontmatter = yaml.safe_dump(fields, default_flow_style=False, allow_unicode=True)
    return f"---\n{frontmatter}---\n\n# Body"


@pytest.fixture(autouse=True)
def clear_config():
    reset_config()
    yield
    reset_config()


# ─── CANON-DEFER-001: enums from config ───────────────────────────────────────

class TestEnumsFromConfig:
    def test_default_config_accepts_standard_type(self):
        doc = make_doc(type="concept")
        errors = validate(doc)
        type_errors = [e for e in errors if e.field == "type"]
        assert type_errors == []

    def test_default_config_rejects_unknown_type(self):
        doc = make_doc(type="sop")
        errors = validate(doc)
        type_errors = [e for e in errors if e.field == "type"]
        assert len(type_errors) == 1
        assert type_errors[0].code == ErrorCode.INVALID_ENUM

    def test_custom_config_accepts_custom_type(self, tmp_path: Path):
        cfg_file = tmp_path / "akf.yaml"
        cfg_file.write_text(
            "enums:\n  type:\n    - sop\n    - concept\n"
            "taxonomy:\n  domains:\n    - ai-system\n",
            encoding="utf-8",
        )
        reset_config()
        get_config(path=cfg_file)

        doc = make_doc(type="sop")
        errors = validate(doc)
        type_errors = [e for e in errors if e.field == "type"]
        assert type_errors == []

    def test_custom_config_rejects_removed_type(self, tmp_path: Path):
        cfg_file = tmp_path / "akf.yaml"
        cfg_file.write_text(
            "enums:\n  type:\n    - sop\n"
            "taxonomy:\n  domains:\n    - ai-system\n",
            encoding="utf-8",
        )
        reset_config()
        get_config(path=cfg_file)

        doc = make_doc(type="concept")  # not in custom config
        errors = validate(doc)
        type_errors = [e for e in errors if e.field == "type"]
        assert len(type_errors) == 1

    def test_custom_config_accepts_custom_domain(self, tmp_path: Path):
        cfg_file = tmp_path / "akf.yaml"
        cfg_file.write_text(
            "taxonomy:\n  domains:\n    - marine-engineering\n",
            encoding="utf-8",
        )
        reset_config()
        get_config(path=cfg_file)

        doc = make_doc(domain="marine-engineering")
        errors = validate(doc)
        domain_errors = [e for e in errors if e.field == "domain"]
        assert domain_errors == []

    def test_custom_config_rejects_default_domain_when_not_listed(self, tmp_path: Path):
        cfg_file = tmp_path / "akf.yaml"
        cfg_file.write_text(
            "taxonomy:\n  domains:\n    - marine-engineering\n",
            encoding="utf-8",
        )
        reset_config()
        get_config(path=cfg_file)

        doc = make_doc(domain="ai-system")  # not in custom list
        errors = validate(doc)
        domain_errors = [e for e in errors if e.field == "domain"]
        assert len(domain_errors) == 1
        assert domain_errors[0].code == ErrorCode.TAXONOMY_VIOLATION

    def test_custom_level_enum(self, tmp_path: Path):
        cfg_file = tmp_path / "akf.yaml"
        cfg_file.write_text(
            "enums:\n  level:\n    - junior\n    - senior\n"
            "taxonomy:\n  domains:\n    - ai-system\n",
            encoding="utf-8",
        )
        reset_config()
        get_config(path=cfg_file)

        doc = make_doc(level="junior")
        errors = validate(doc)
        level_errors = [e for e in errors if e.field == "level"]
        assert level_errors == []

        doc2 = make_doc(level="beginner")
        errors2 = validate(doc2)
        level_errors2 = [e for e in errors2 if e.field == "level"]
        assert len(level_errors2) == 1

    def test_custom_status_enum(self, tmp_path: Path):
        cfg_file = tmp_path / "akf.yaml"
        cfg_file.write_text(
            "enums:\n  status:\n    - retired\n    - active\n"
            "taxonomy:\n  domains:\n    - ai-system\n",
            encoding="utf-8",
        )
        reset_config()
        get_config(path=cfg_file)

        doc = make_doc(status="retired")
        errors = validate(doc)
        status_errors = [e for e in errors if e.field == "status"]
        assert status_errors == []


# ─── CANON-DEFER-002: created ≤ updated ──────────────────────────────────────

class TestCreatedUpdatedConstraint:
    def test_valid_created_before_updated(self):
        doc = make_doc(created="2026-01-01", updated="2026-01-02")
        errors = validate(doc)
        date_errors = [e for e in errors if "created" in e.field]
        assert date_errors == []

    def test_valid_created_equals_updated(self):
        doc = make_doc(created="2026-01-01", updated="2026-01-01")
        errors = validate(doc)
        date_errors = [e for e in errors if "created" in e.field]
        assert date_errors == []

    def test_invalid_created_after_updated(self):
        doc = make_doc(created="2026-02-01", updated="2026-01-01")
        errors = validate(doc)
        date_errors = [e for e in errors if "created/updated" in e.field]
        assert len(date_errors) == 1
        assert date_errors[0].code == ErrorCode.DATE_SEQUENCE

    def test_created_after_updated_is_error_severity(self):
        from akf.validation_error import Severity
        doc = make_doc(created="2026-12-31", updated="2026-01-01")
        errors = validate(doc)
        date_errors = [e for e in errors if "created/updated" in e.field]
        assert date_errors[0].severity == Severity.ERROR

    def test_no_constraint_when_created_missing(self):
        """Missing created is caught by E002, not E007."""
        doc = make_doc(created="2026-01-01", updated="2026-01-02")
        # Remove created from doc
        doc = doc.replace("created: 2026-01-01\n", "")
        errors = validate(doc)
        date_errors = [e for e in errors if "created/updated" in e.field]
        assert date_errors == []  # E002 fires, not the cross-field check

    def test_no_constraint_when_updated_missing(self):
        doc = make_doc(created="2026-01-01", updated="2026-01-02")
        doc = doc.replace("updated: 2026-01-02\n", "")
        errors = validate(doc)
        date_errors = [e for e in errors if "created/updated" in e.field]
        assert date_errors == []

    def test_invalid_date_format_skips_constraint(self):
        """If a date is invalid, constraint check is skipped (not double-reported)."""
        doc = make_doc(created="not-a-date", updated="2026-01-01")
        errors = validate(doc)
        format_errors = [e for e in errors if e.field == "created"]
        constraint_errors = [e for e in errors if "created/updated" in e.field]
        assert len(format_errors) == 1
        assert constraint_errors == []

    def test_datetime_date_objects_compared_correctly(self):
        """PyYAML parses unquoted dates as datetime.date — must still compare."""
        # Unquoted dates in YAML → PyYAML parses as date objects
        doc = textwrap.dedent("""\
            ---
            title: Test
            type: concept
            domain: ai-system
            level: beginner
            status: active
            tags:
              - a
              - b
              - c
            created: 2026-02-01
            updated: 2026-01-01
            ---

            # Body
        """)
        errors = validate(doc)
        date_errors = [e for e in errors if "created/updated" in e.field]
        assert len(date_errors) == 1


# ─── CANON-DEFER-003: title isinstance str ───────────────────────────────────

class TestTitleTypeEnforcement:
    def test_string_title_passes(self):
        doc = make_doc(title="Valid Title")
        errors = validate(doc)
        title_errors = [e for e in errors if e.field == "title"]
        assert title_errors == []

    def test_numeric_title_fails(self):
        """title: 42 — PyYAML parses as int."""
        doc = textwrap.dedent("""\
            ---
            title: 42
            type: concept
            domain: ai-system
            level: beginner
            status: active
            tags:
              - a
              - b
              - c
            created: 2026-01-01
            updated: 2026-01-02
            ---

            # Body
        """)
        errors = validate(doc)
        title_errors = [e for e in errors if e.field == "title"]
        assert len(title_errors) == 1
        assert title_errors[0].code == ErrorCode.TYPE_MISMATCH

    def test_float_title_fails(self):
        doc = textwrap.dedent("""\
            ---
            title: 3.14
            type: concept
            domain: ai-system
            level: beginner
            status: active
            tags:
              - a
              - b
              - c
            created: 2026-01-01
            updated: 2026-01-02
            ---

            # Body
        """)
        errors = validate(doc)
        title_errors = [e for e in errors if e.field == "title"]
        assert len(title_errors) == 1

    def test_missing_title_caught_by_required_not_type(self):
        doc = make_doc(title="placeholder")
        doc = doc.replace("title: placeholder\n", "")
        errors = validate(doc)
        # E002 (missing field), not E004 (type mismatch)
        title_errors = [e for e in errors if e.field == "title"]
        assert any(e.code == ErrorCode.MISSING_FIELD for e in title_errors)
        assert all(e.code != ErrorCode.TYPE_MISMATCH for e in title_errors)

    def test_bool_title_fails(self):
        """title: true — PyYAML parses as bool."""
        doc = textwrap.dedent("""\
            ---
            title: true
            type: concept
            domain: ai-system
            level: beginner
            status: active
            tags:
              - a
              - b
              - c
            created: 2026-01-01
            updated: 2026-01-02
            ---

            # Body
        """)
        errors = validate(doc)
        title_errors = [e for e in errors if e.field == "title"]
        assert len(title_errors) == 1
        assert title_errors[0].code == ErrorCode.TYPE_MISMATCH


# ─── backwards compatibility: taxonomy_path ───────────────────────────────────

class TestTaxonomyPathBackwardsCompat:
    def test_taxonomy_path_ignored_when_config_exists(self, tmp_path: Path):
        """When akf.yaml is loaded, taxonomy_path is ignored."""
        cfg_file = tmp_path / "akf.yaml"
        cfg_file.write_text(
            "taxonomy:\n  domains:\n    - marine-engineering\n",
            encoding="utf-8",
        )
        reset_config()
        get_config(path=cfg_file)

        # Even with a taxonomy_path, config domains win
        doc = make_doc(domain="marine-engineering")
        errors = validate(doc, taxonomy_path=tmp_path / "nonexistent.md")
        domain_errors = [e for e in errors if e.field == "domain"]
        assert domain_errors == []


# ─── valid document end-to-end ────────────────────────────────────────────────

class TestValidDocumentEndToEnd:
    def test_valid_doc_returns_no_errors(self):
        doc = make_doc()
        errors = validate(doc)
        assert errors == []

    def test_all_three_defers_pass_on_valid_doc(self):
        doc = textwrap.dedent("""\
            ---
            title: "My Knowledge Document"
            type: reference
            domain: devops
            level: intermediate
            status: active
            tags:
              - devops
              - ci-cd
              - automation
            related:
              - "[[Some Reference]]"
            created: 2026-01-15
            updated: 2026-02-20
            ---

            ## Content

            Body text here.
        """)
        errors = validate(doc)
        assert errors == [], f"Unexpected errors: {errors}"


# ─── E008: typed relationship validation ─────────────────────────────────────


class TestTypedRelationships:
    """Tests for E008_INVALID_RELATIONSHIP_TYPE (Phase 2.5)."""

    def test_untyped_link_is_valid(self):
        """[[Note Name]] without type always passes."""
        doc = make_doc(related=["[[Some Note]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors == []

    def test_valid_typed_link_implements(self):
        doc = make_doc(related=["[[Auth Service|implements]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors == []

    def test_valid_typed_link_requires(self):
        doc = make_doc(related=["[[Base Schema|requires]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors == []

    def test_valid_typed_link_extends(self):
        doc = make_doc(related=["[[Base Pattern|extends]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors == []

    def test_valid_typed_link_references(self):
        doc = make_doc(related=["[[RFC 7231|references]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors == []

    def test_valid_typed_link_supersedes(self):
        doc = make_doc(related=["[[Old Design|supersedes]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors == []

    def test_valid_typed_link_part_of(self):
        doc = make_doc(related=["[[Parent System|part-of]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors == []

    def test_invalid_typed_link_emits_e008(self):
        """[[Note|unknown-type]] → E008."""
        doc = make_doc(related=["[[Some Note|unknown-type]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert len(rel_errors) == 1
        assert rel_errors[0].severity == Severity.ERROR

    def test_invalid_typed_link_received_contains_link(self):
        """E008 received field includes the full [[Note|type]] string."""
        doc = make_doc(related=["[[My Note|invalid]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert len(rel_errors) == 1
        assert "[[My Note|invalid]]" == rel_errors[0].received

    def test_invalid_typed_link_expected_contains_valid_types(self):
        """E008 expected field lists the allowed relationship types."""
        doc = make_doc(related=["[[X|bogus]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert isinstance(rel_errors[0].expected, list)
        assert "implements" in rel_errors[0].expected

    def test_mixed_valid_and_invalid_typed_links(self):
        """One valid typed + one invalid typed → exactly one E008."""
        doc = make_doc(related=["[[Good Note|implements]]", "[[Bad Note|invented]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert len(rel_errors) == 1

    def test_multiple_invalid_typed_links(self):
        """Two invalid typed links → two E008 errors."""
        doc = make_doc(related=["[[A|bad1]]", "[[B|bad2]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert len(rel_errors) == 2

    def test_untyped_and_typed_mixed_all_valid(self):
        """Untyped + typed valid links → no E008."""
        doc = make_doc(related=["[[Plain Note]]", "[[Other|requires]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors == []

    def test_custom_config_with_custom_relationship_types(self, tmp_path: Path):
        """Custom relationship_types in config overrides defaults."""
        cfg_file = tmp_path / "akf.yaml"
        cfg_file.write_text(
            "taxonomy:\n  domains:\n    - ai-system\n"
            "relationship_types:\n  - uses\n  - defines\n",
            encoding="utf-8",
        )
        reset_config()
        get_config(path=cfg_file)

        doc = make_doc(related=["[[A|uses]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors == []

    def test_custom_config_rejects_default_type_not_in_custom_list(self, tmp_path: Path):
        """Default types like 'implements' rejected if not in custom list."""
        cfg_file = tmp_path / "akf.yaml"
        cfg_file.write_text(
            "taxonomy:\n  domains:\n    - ai-system\n"
            "relationship_types:\n  - uses\n",
            encoding="utf-8",
        )
        reset_config()
        get_config(path=cfg_file)

        doc = make_doc(related=["[[A|implements]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert len(rel_errors) == 1

    def test_e008_is_blocking_error(self):
        """E008 must have ERROR severity — blocks commit."""
        doc = make_doc(related=["[[A|totally-wrong]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors[0].severity == Severity.ERROR

    def test_e008_field_is_related(self):
        """E008 reports field='related'."""
        doc = make_doc(related=["[[A|bad]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors[0].field == "related"

    def test_untyped_link_backward_compat_no_e008(self):
        """Backward compat: existing [[Note Name]] docs never get E008."""
        doc = make_doc(related=["[[LLM_Output_Validation_Pipeline_Architecture]]",
                                 "[[Prompt_Engineering_Techniques]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert rel_errors == []

    def test_e008_normalizer_renders_instruction(self):
        """E008 errors appear in RetryPayload with correct instruction text."""
        doc = make_doc(related=["[[A|garbage]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        assert len(rel_errors) == 1
        payload = normalize_errors(rel_errors)
        assert payload.has_blocking_errors
        assert len(payload.instructions) == 1
        instruction = payload.instructions[0]
        assert "relationship_type" in instruction
        assert "implements" in instruction

    def test_e008_normalizer_prompt_text(self):
        """to_prompt_text() includes the E008 instruction."""
        doc = make_doc(related=["[[X|not-a-type]]"])
        errors = validate(doc)
        rel_errors = [e for e in errors if e.code == ErrorCode.INVALID_RELATIONSHIP_TYPE]
        payload = normalize_errors(rel_errors)
        text = payload.to_prompt_text()
        assert "VALIDATION ERRORS" in text
        assert "relationship_type" in text

    def test_related_empty_string_emits_type_mismatch(self):
        """related: '' (empty string, not a list) → E004_TYPE_MISMATCH."""
        doc = textwrap.dedent("""\
            ---
            title: Test Document
            type: concept
            domain: ai-system
            level: beginner
            status: active
            tags:
              - a
              - b
              - c
            related: ''
            created: '2026-01-01'
            updated: '2026-01-02'
            ---

            # Body
        """)
        errors = validate(doc)
        related_errors = [e for e in errors if e.field == "related"]
        assert len(related_errors) == 1
        assert related_errors[0].code == ErrorCode.TYPE_MISMATCH

    def test_related_zero_emits_type_mismatch(self):
        """related: 0 (integer, not a list) → E004_TYPE_MISMATCH."""
        doc = textwrap.dedent("""\
            ---
            title: Test Document
            type: concept
            domain: ai-system
            level: beginner
            status: active
            tags:
              - a
              - b
              - c
            related: 0
            created: '2026-01-01'
            updated: '2026-01-02'
            ---

            # Body
        """)
        errors = validate(doc)
        related_errors = [e for e in errors if e.field == "related"]
        assert len(related_errors) == 1
        assert related_errors[0].code == ErrorCode.TYPE_MISMATCH

    def test_related_none_emits_schema_violation_warning(self):
        """related absent (None) → W001 SCHEMA_VIOLATION warning, not E004."""
        doc = textwrap.dedent("""\
            ---
            title: Test Document
            type: concept
            domain: ai-system
            level: beginner
            status: active
            tags:
              - a
              - b
              - c
            created: '2026-01-01'
            updated: '2026-01-02'
            ---

            # Body
        """)
        errors = validate(doc)
        related_errors = [e for e in errors if e.field == "related"]
        assert len(related_errors) == 1
        assert related_errors[0].code == ErrorCode.SCHEMA_VIOLATION
        assert related_errors[0].severity == Severity.WARNING
        assert related_errors[0].code != ErrorCode.TYPE_MISMATCH

    def test_related_non_list_emits_type_mismatch(self):
        """related: 'a string' (not a list) → E004_TYPE_MISMATCH immediately."""
        doc = textwrap.dedent("""\
            ---
            title: Test Document
            type: concept
            domain: ai-system
            level: beginner
            status: active
            tags:
              - a
              - b
              - c
            related: "[[Some Note]]"
            created: "2026-01-01"
            updated: "2026-01-02"
            ---

            # Body
        """)
        errors = validate(doc)
        related_errors = [e for e in errors if e.field == "related"]
        assert len(related_errors) == 1
        assert related_errors[0].code == ErrorCode.TYPE_MISMATCH
