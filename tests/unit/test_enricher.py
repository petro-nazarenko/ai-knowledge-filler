"""
tests/unit/test_enricher.py
────────────────────────────
Unit tests for akf/enricher.py.
Target coverage: ≥ 90%.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
import yaml

from akf.enricher import (
    REQUIRED_FIELDS,
    _assemble,
    _deduplicated_union,
    build_prompt,
    derive_title,
    extract_missing_fields,
    merge_yaml,
    read_file,
    write_back,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_md(tmp_path: Path):
    """Return a factory that creates .md files in tmp_path."""

    def _make(name: str, content: str) -> Path:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return p

    return _make


# ─── read_file ────────────────────────────────────────────────────────────────


class TestReadFile:
    def test_no_frontmatter_returns_empty_dict(self, tmp_md):
        p = tmp_md("plain.md", "# Hello\nSome text.")
        meta, body = read_file(p)
        assert meta == {}
        assert "# Hello" in body

    def test_valid_frontmatter_parsed(self, tmp_md):
        content = "---\ntitle: Test\ntype: guide\n---\n# Body"
        p = tmp_md("valid.md", content)
        meta, body = read_file(p)
        assert meta["title"] == "Test"
        assert meta["type"] == "guide"
        assert "# Body" in body

    def test_empty_file_returns_empty(self, tmp_md):
        p = tmp_md("empty.md", "")
        meta, body = read_file(p)
        assert meta == {}
        assert body == ""

    def test_invalid_yaml_warns_and_returns_empty(self, tmp_md):
        content = "---\nkey: [bad yaml\n---\n# Content"
        p = tmp_md("bad.md", content)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            meta, body = read_file(p)
        assert meta == {}
        assert len(w) >= 1

    def test_opening_dash_no_close(self, tmp_md):
        """Only opening --- with no closing --- → returns ({}, full_content)."""
        content = "---\ntitle: Incomplete"
        p = tmp_md("incomplete.md", content)
        meta, body = read_file(p)
        assert meta == {}

    def test_empty_yaml_block(self, tmp_md):
        content = "---\n---\n# Only body"
        p = tmp_md("empty_yaml.md", content)
        meta, body = read_file(p)
        assert meta == {}
        assert "# Only body" in body

    def test_frontmatter_is_list_warns(self, tmp_md):
        content = "---\n- item1\n- item2\n---\n# Body"
        p = tmp_md("list_yaml.md", content)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            meta, body = read_file(p)
        assert meta == {}
        assert any("dict" in str(warning.message) for warning in w)


# ─── extract_missing_fields ───────────────────────────────────────────────────


class TestExtractMissingFields:
    def test_all_present(self):
        existing = {f: "val" for f in REQUIRED_FIELDS}
        assert extract_missing_fields(existing, REQUIRED_FIELDS) == []

    def test_some_missing(self):
        existing = {"title": "X", "type": "guide"}
        missing = extract_missing_fields(existing, REQUIRED_FIELDS)
        assert "domain" in missing
        assert "level" in missing
        assert "title" not in missing

    def test_empty_value_counts_as_missing(self):
        existing = {"title": "", "type": None}
        missing = extract_missing_fields(existing, ["title", "type", "domain"])
        assert "title" in missing
        assert "type" in missing
        assert "domain" in missing

    def test_all_missing(self):
        missing = extract_missing_fields({}, REQUIRED_FIELDS)
        assert set(missing) == set(REQUIRED_FIELDS)


# ─── build_prompt ─────────────────────────────────────────────────────────────


class TestBuildPrompt:
    def test_contains_required_sections(self):
        prompt = build_prompt(
            body="Some document body.",
            existing={"title": "Test"},
            missing=["domain", "type"],
            taxonomy_domains=["ai-system", "devops"],
            today="2026-02-27",
        )
        assert "EXISTING FIELDS" in prompt
        assert "MISSING FIELDS TO GENERATE" in prompt
        assert "- domain" in prompt
        assert "- type" in prompt
        assert "ai-system" in prompt
        assert "2026-02-27" in prompt

    def test_body_truncated_to_500(self):
        long_body = "x" * 1000
        prompt = build_prompt(
            body=long_body,
            existing={},
            missing=["title"],
            taxonomy_domains=["ai-system"],
            today="2026-02-27",
        )
        # Should only contain 500 x's in the content sample section
        assert "x" * 501 not in prompt

    def test_empty_existing_shows_none(self):
        prompt = build_prompt(
            body="body",
            existing={},
            missing=["title"],
            taxonomy_domains=["ai-system"],
            today="2026-02-27",
        )
        assert "(none)" in prompt

    def test_no_missing_shows_none(self):
        prompt = build_prompt(
            body="body",
            existing={"title": "X"},
            missing=[],
            taxonomy_domains=["ai-system"],
            today="2026-02-27",
        )
        assert "(none)" in prompt


# ─── merge_yaml ───────────────────────────────────────────────────────────────


class TestMergeYaml:
    def test_existing_wins_without_force(self):
        existing = {"title": "Old Title", "type": "guide"}
        generated = {"title": "New Title", "domain": "ai-system"}
        merged = merge_yaml(existing, generated, force=False, today="2026-02-27")
        assert merged["title"] == "Old Title"  # existing wins
        assert merged["domain"] == "ai-system"  # new field added

    def test_force_overwrites_existing(self):
        existing = {"title": "Old", "type": "guide"}
        generated = {"title": "New", "type": "reference"}
        merged = merge_yaml(existing, generated, force=True, today="2026-02-27")
        assert merged["title"] == "New"
        assert merged["type"] == "reference"

    def test_created_never_overwritten(self):
        existing = {"created": "2025-01-01"}
        generated = {"created": "2026-02-27"}
        merged = merge_yaml(existing, generated, force=True, today="2026-02-27")
        assert merged["created"] == "2025-01-01"

    def test_created_set_if_missing(self):
        existing = {}
        generated = {"created": "2026-02-27"}
        merged = merge_yaml(existing, generated, force=False, today="2026-02-27")
        assert merged["created"] == "2026-02-27"

    def test_updated_always_refreshed(self):
        existing = {"updated": "2020-01-01"}
        generated = {}
        merged = merge_yaml(existing, generated, force=False, today="2026-02-27")
        assert merged["updated"] == "2026-02-27"

    def test_tags_union_deduplicated(self):
        existing = {"tags": ["python", "ai"]}
        generated = {"tags": ["ai", "devops"]}
        merged = merge_yaml(existing, generated, force=False, today="2026-02-27")
        assert "python" in merged["tags"]
        assert "ai" in merged["tags"]
        assert "devops" in merged["tags"]
        # No duplicate 'ai'
        assert merged["tags"].count("ai") == 1

    def test_related_union(self):
        existing = {"related": ["[[DocA]]"]}
        generated = {"related": ["[[DocA]]", "[[DocB]]"]}
        merged = merge_yaml(existing, generated, force=False, today="2026-02-27")
        assert merged["related"].count("[[DocA]]") == 1
        assert "[[DocB]]" in merged["related"]

    def test_tags_from_string_handled(self):
        """generated may sometimes return a string for tags — treat as single-item list."""
        existing = {"tags": ["ai"]}
        generated = {"tags": "devops"}
        merged = merge_yaml(existing, generated, force=False, today="2026-02-27")
        assert "ai" in merged["tags"]
        assert "devops" in merged["tags"]

    def test_today_default_used(self):
        from datetime import date

        merged = merge_yaml({}, {})
        assert merged["updated"] == date.today().isoformat()


# ─── derive_title ─────────────────────────────────────────────────────────────


class TestDeriveTitle:
    def test_underscore_to_title_case(self):
        p = Path("api_reference.md")
        assert derive_title(p) == "API Reference"

    def test_cli_uppercased(self):
        p = Path("cli_reference.md")
        assert derive_title(p) == "CLI Reference"

    def test_hyphen_to_title_case(self):
        p = Path("my-document.md")
        assert derive_title(p) == "My Document"

    def test_single_word_non_acronym(self):
        p = Path("architecture.md")
        assert derive_title(p) == "Architecture"

    def test_mixed_separators_with_acronym(self):
        p = Path("rest_api-guide.md")
        assert derive_title(p) == "REST API Guide"

    def test_unknown_abbreviation_title_cased(self):
        """Words not in _ACRONYMS are title-cased, not uppercased."""
        p = Path("oauth_guide.md")
        assert derive_title(p) == "Oauth Guide"

    def test_yaml_acronym(self):
        p = Path("yaml_schema.md")
        assert derive_title(p) == "YAML Schema"


# ─── write_back ───────────────────────────────────────────────────────────────


class TestWriteBack:
    def test_writes_valid_frontmatter(self, tmp_path):
        p = tmp_path / "output.md"
        yaml_dict = {"title": "Test", "type": "guide", "tags": ["a", "b"]}
        body = "# Test\nContent here."
        write_back(p, yaml_dict, body)
        assert p.exists()
        content = p.read_text(encoding="utf-8")
        assert content.startswith("---")
        parsed_meta, _ = __import__("akf.enricher", fromlist=["read_file"]).read_file(p)
        assert parsed_meta["title"] == "Test"

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "subdir" / "deep" / "output.md"
        write_back(p, {"title": "X"}, "body")
        assert p.exists()

    def test_atomic_replace(self, tmp_path):
        """write_back replaces existing file atomically."""
        p = tmp_path / "exists.md"
        p.write_text("original", encoding="utf-8")
        write_back(p, {"title": "New"}, "new body")
        content = p.read_text(encoding="utf-8")
        assert "New" in content
        assert "original" not in content


# ─── _assemble ────────────────────────────────────────────────────────────────


class TestAssemble:
    def test_produces_valid_structure(self):
        result = _assemble({"title": "T"}, "# Body\n")
        assert result.startswith("---\n")
        assert "---\n" in result[4:]  # closing ---
        assert "# Body" in result

    def test_body_leading_newlines_stripped(self):
        result = _assemble({"title": "T"}, "\n\n# Body")
        # Should not have blank lines between --- and # Body
        parts = result.split("---\n")
        assert parts[2].startswith("# Body")


# ─── _deduplicated_union ──────────────────────────────────────────────────────


class TestDeduplicatedUnion:
    def test_basic(self):
        result = _deduplicated_union(["a", "b"], ["b", "c"])
        assert result == ["a", "b", "c"]

    def test_empty_lists(self):
        assert _deduplicated_union([], []) == []

    def test_case_insensitive_dedup(self):
        result = _deduplicated_union(["AI"], ["ai"])
        assert len(result) == 1
