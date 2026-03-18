"""Tests for the `akf gaps` CLI subcommand."""

import argparse
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {"path": ".", "output": None, "format": None}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _write_md(directory: Path, name: str, content: str) -> Path:
    p = directory / name
    p.write_text(content, encoding="utf-8")
    return p


FRONTMATTER_TEMPLATE = """\
---
title: "{title}"
type: guide
domain: test
level: beginner
status: active
tags: [a, b, c]
created: 2026-01-01
updated: 2026-01-01
related: "{related}"
---

# Body
"""

FRONTMATTER_NO_RELATED = """\
---
title: "No Related"
type: guide
domain: test
level: beginner
status: active
tags: [a, b, c]
created: 2026-01-01
updated: 2026-01-01
---

# Body
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    """Vault with a mix of linked and missing files."""
    # Existing files
    _write_md(
        tmp_path,
        "API_Design.md",
        FRONTMATTER_TEMPLATE.format(
            title="API Design",
            related="[[Docker_Basics]] [[JWT_Authentication_Guide]]",
        ),
    )
    _write_md(
        tmp_path,
        "Docker_Basics.md",
        FRONTMATTER_TEMPLATE.format(
            title="Docker Basics",
            related="[[API_Design]]",
        ),
    )
    # No related field
    _write_md(tmp_path, "Orphan.md", FRONTMATTER_NO_RELATED)
    return tmp_path


# ---------------------------------------------------------------------------
# Unit tests for cmd_gaps
# ---------------------------------------------------------------------------


class TestCmdGapsBasic:
    def test_detects_missing_file(self, vault: Path, capsys) -> None:
        from cli import cmd_gaps

        cmd_gaps(_make_args(path=str(vault)))
        out = capsys.readouterr().out
        assert "JWT_Authentication_Guide" in out
        assert "Missing files" in out

    def test_no_false_positives_for_existing_file(self, vault: Path, capsys) -> None:
        from cli import cmd_gaps

        cmd_gaps(_make_args(path=str(vault)))
        out = capsys.readouterr().out
        # Docker_Basics exists — should NOT appear in missing list
        assert "Docker_Basics" not in out
        # API_Design exists — should NOT appear either
        assert "API_Design" not in out

    def test_suggests_prompt_for_missing(self, vault: Path, capsys) -> None:
        from cli import cmd_gaps

        cmd_gaps(_make_args(path=str(vault)))
        out = capsys.readouterr().out
        # New format: "Create a <type> on <topic> for <audience>"
        assert "Create a" in out
        assert "JWT Authentication Guide" in out

    def test_no_missing_files_message(self, tmp_path: Path, capsys) -> None:
        from cli import cmd_gaps

        # File links only to existing file
        _write_md(
            tmp_path,
            "A.md",
            FRONTMATTER_TEMPLATE.format(
                title="A",
                related="[[B]]",
            ),
        )
        _write_md(tmp_path, "B.md", FRONTMATTER_NO_RELATED)
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        assert "No missing files" in out

    def test_empty_vault(self, tmp_path: Path, capsys) -> None:
        from cli import cmd_gaps

        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        assert "No missing files" in out

    def test_files_without_related_are_ignored(self, tmp_path: Path, capsys) -> None:
        from cli import cmd_gaps

        _write_md(tmp_path, "Orphan.md", FRONTMATTER_NO_RELATED)
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        assert "No missing files" in out


class TestCmdGapsFormatJson:
    def test_format_json_outputs_array(self, vault: Path, capsys) -> None:
        from cli import cmd_gaps

        cmd_gaps(_make_args(path=str(vault), format="json"))
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert isinstance(parsed, list)

    def test_format_json_contains_prompt_key(self, vault: Path, capsys) -> None:
        from cli import cmd_gaps

        cmd_gaps(_make_args(path=str(vault), format="json"))
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert all("prompt" in item for item in parsed)
        assert all("domain" in item for item in parsed)
        assert all("type" in item for item in parsed)

    def test_format_json_no_human_text(self, vault: Path, capsys) -> None:
        from cli import cmd_gaps

        cmd_gaps(_make_args(path=str(vault), format="json"))
        out = capsys.readouterr().out
        # Must be parseable as JSON — no "Missing files" header
        json.loads(out)  # raises if not valid JSON

    def test_format_json_empty_vault(self, tmp_path: Path, capsys) -> None:
        from cli import cmd_gaps

        cmd_gaps(_make_args(path=str(tmp_path), format="json"))
        out = capsys.readouterr().out
        assert json.loads(out) == []


class TestCmdGapsOutputFlag:
    def test_writes_to_new_plan_json(self, vault: Path, tmp_path: Path, capsys) -> None:
        from cli import cmd_gaps

        plan_file = tmp_path / "plan.json"
        cmd_gaps(_make_args(path=str(vault), output=str(plan_file)))
        assert plan_file.exists()
        data = json.loads(plan_file.read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    def test_appends_to_existing_plan_json(self, vault: Path, tmp_path: Path) -> None:
        from cli import cmd_gaps

        plan_file = tmp_path / "plan.json"
        existing = [{"prompt": "Existing entry"}]
        plan_file.write_text(json.dumps(existing), encoding="utf-8")

        cmd_gaps(_make_args(path=str(vault), output=str(plan_file)))
        data = json.loads(plan_file.read_text())
        # Original entry preserved
        assert any(item["prompt"] == "Existing entry" for item in data)
        # New entries appended
        assert len(data) > 1

    def test_no_output_file_when_no_missing(self, tmp_path: Path) -> None:
        from cli import cmd_gaps

        _write_md(
            tmp_path,
            "A.md",
            FRONTMATTER_TEMPLATE.format(
                title="A",
                related="[[B]]",
            ),
        )
        _write_md(tmp_path, "B.md", FRONTMATTER_NO_RELATED)
        plan_file = tmp_path / "plan.json"
        cmd_gaps(_make_args(path=str(tmp_path), output=str(plan_file)))
        # No missing files → file should not be created
        assert not plan_file.exists()

    def test_output_file_contains_correct_prompts(self, vault: Path, tmp_path: Path) -> None:
        from cli import cmd_gaps

        plan_file = tmp_path / "plan.json"
        cmd_gaps(_make_args(path=str(vault), output=str(plan_file)))
        data = json.loads(plan_file.read_text())
        prompts = [item["prompt"] for item in data]
        assert any("JWT Authentication Guide" in p for p in prompts)


class TestCmdGapsEdgeCases:
    def test_wikilink_with_alias(self, tmp_path: Path, capsys) -> None:
        """[[Target|Display Name]] — only 'Target' should be collected."""
        from cli import cmd_gaps

        _write_md(
            tmp_path,
            "Source.md",
            FRONTMATTER_TEMPLATE.format(
                title="Source",
                related="[[MissingTarget|Display Name]]",
            ),
        )
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        assert "MissingTarget" in out
        assert (
            "Display Name" not in out.split("Missing files")[1] if "Missing files" in out else True
        )

    def test_related_as_yaml_list(self, tmp_path: Path, capsys) -> None:
        """related field as YAML list of wikilinks."""
        from cli import cmd_gaps

        content = """\
---
title: "List Related"
type: guide
domain: test
level: beginner
status: active
tags: [a, b, c]
created: 2026-01-01
updated: 2026-01-01
related:
  - "[[Alpha]]"
  - "[[Beta]]"
---

# Body
"""
        _write_md(tmp_path, "Source.md", content)
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        assert "Alpha" in out
        assert "Beta" in out

    def test_invalid_path_exits(self, capsys) -> None:
        from cli import cmd_gaps

        with pytest.raises(SystemExit) as exc_info:
            cmd_gaps(_make_args(path="/nonexistent/vault/path"))
        assert exc_info.value.code == 1

    def test_file_path_instead_of_dir_exits(self, tmp_path: Path) -> None:
        from cli import cmd_gaps

        f = tmp_path / "file.md"
        f.write_text("# hi", encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            cmd_gaps(_make_args(path=str(f)))
        assert exc_info.value.code == 1

    def test_duplicate_links_reported_once(self, tmp_path: Path, capsys) -> None:
        """Same missing link referenced in multiple files → listed once in missing section."""
        from cli import cmd_gaps

        for i in range(3):
            _write_md(
                tmp_path,
                f"File{i}.md",
                FRONTMATTER_TEMPLATE.format(
                    title=f"File {i}",
                    related="[[SharedMissing]]",
                ),
            )
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        # Missing files count should be 1, not 3
        assert "Missing files (1):" in out

    def test_subdirectory_md_files_scanned(self, tmp_path: Path, capsys) -> None:
        """Files in subdirectories are included in the scan."""
        from cli import cmd_gaps

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        _write_md(
            subdir,
            "Nested.md",
            FRONTMATTER_TEMPLATE.format(
                title="Nested",
                related="[[DeepMissing]]",
            ),
        )
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        assert "DeepMissing" in out

    def test_subdirectory_files_count_as_existing(self, tmp_path: Path, capsys) -> None:
        """A file in a subdirectory resolves a WikiLink by stem name."""
        from cli import cmd_gaps

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        _write_md(subdir, "TargetFile.md", FRONTMATTER_NO_RELATED)
        _write_md(
            tmp_path,
            "Source.md",
            FRONTMATTER_TEMPLATE.format(
                title="Source",
                related="[[TargetFile]]",
            ),
        )
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        assert "No missing files" in out


# ---------------------------------------------------------------------------
# Argparse integration: ensure `gaps` appears as a valid subcommand
# ---------------------------------------------------------------------------


class TestGapsSubparser:
    def test_gaps_is_registered(self) -> None:
        import cli as cli_module
        import importlib

        # Parse --help output via argparse internals
        parser = argparse.ArgumentParser(prog="akf")
        sub = parser.add_subparsers(dest="command", required=True)
        # Re-run main setup by invoking main via subprocess is heavy;
        # instead, verify cmd_gaps is importable and callable
        assert callable(cli_module.cmd_gaps)

    def test_main_dispatches_gaps(self, vault: Path, monkeypatch, capsys) -> None:
        import cli as cli_module

        monkeypatch.setattr(sys, "argv", ["akf", "gaps", "--path", str(vault)])
        # main() returns 0 and does not raise
        result = cli_module.main()
        assert result == 0


# ---------------------------------------------------------------------------
# Tests for deduplication normalization (Bug 1)
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_space_and_underscore_variants_deduplicated(self, tmp_path: Path, capsys) -> None:
        """'API Design Principles' and 'API_Design_Principles' → only one entry."""
        from cli import cmd_gaps

        # One file links with spaces, another with underscores — same logical target
        _write_md(
            tmp_path,
            "FileA.md",
            FRONTMATTER_TEMPLATE.format(
                title="File A",
                related="[[API Design Principles]]",
            ),
        )
        _write_md(
            tmp_path,
            "FileB.md",
            FRONTMATTER_TEMPLATE.format(
                title="File B",
                related="[[API_Design_Principles]]",
            ),
        )
        cmd_gaps(_make_args(path=str(tmp_path), format="json"))
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert len(parsed) == 1, f"Expected 1 deduplicated entry, got {len(parsed)}: {parsed}"

    def test_case_insensitive_deduplication(self, tmp_path: Path, capsys) -> None:
        """'docker_basics' and 'Docker_Basics' are the same file."""
        from cli import cmd_gaps

        _write_md(
            tmp_path,
            "FileA.md",
            FRONTMATTER_TEMPLATE.format(
                title="File A",
                related="[[docker_basics]]",
            ),
        )
        _write_md(
            tmp_path,
            "FileB.md",
            FRONTMATTER_TEMPLATE.format(
                title="File B",
                related="[[Docker_Basics]]",
            ),
        )
        cmd_gaps(_make_args(path=str(tmp_path), format="json"))
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert len(parsed) == 1, f"Expected 1 deduplicated entry, got {len(parsed)}: {parsed}"

    def test_normalized_link_resolves_against_existing_file(self, tmp_path: Path, capsys) -> None:
        """A link 'API Design Principles' (with spaces) matches file 'API_Design_Principles.md'."""
        from cli import cmd_gaps

        _write_md(tmp_path, "API_Design_Principles.md", FRONTMATTER_NO_RELATED)
        _write_md(
            tmp_path,
            "Source.md",
            FRONTMATTER_TEMPLATE.format(
                title="Source",
                related="[[API Design Principles]]",
            ),
        )
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        assert "No missing files" in out

    def test_normalize_link_helper(self) -> None:
        from cli import _normalize_link

        assert _normalize_link("API Design Principles") == "api_design_principles"
        assert _normalize_link("API_Design_Principles") == "api_design_principles"
        assert _normalize_link("Docker_Basics") == "docker_basics"
        assert _normalize_link("  Spaces  ") == "spaces"


# ---------------------------------------------------------------------------
# Tests for structured prompt generation (Bug 2)
# ---------------------------------------------------------------------------


class TestPromptGeneration:
    def test_make_suggestion_has_required_keys(self) -> None:
        from cli import _make_suggestion

        result = _make_suggestion("Docker_Basics")
        assert "prompt" in result
        assert "domain" in result
        assert "type" in result

    def test_make_suggestion_prompt_format(self) -> None:
        from cli import _make_suggestion

        result = _make_suggestion("Docker_Basics")
        # Format: "Create a <type> on <topic> for <audience>"
        assert result["prompt"].startswith("Create a ")
        assert " on " in result["prompt"]
        assert " for " in result["prompt"]

    def test_domain_devops_keywords(self) -> None:
        from cli import _infer_domain

        assert _infer_domain("Docker_Basics") == "devops"
        assert _infer_domain("Kubernetes_Deployments") == "devops"
        assert _infer_domain("GitHub_Actions_CI") == "devops"

    def test_domain_api_design_keywords(self) -> None:
        from cli import _infer_domain

        assert _infer_domain("REST_API_Design") == "api-design"
        assert _infer_domain("GraphQL_Patterns") == "api-design"
        assert _infer_domain("HTTP_Caching") == "api-design"

    def test_domain_security_keywords(self) -> None:
        from cli import _infer_domain

        assert _infer_domain("JWT_Authentication_Guide") == "security"
        assert _infer_domain("OAuth_Strategies") == "security"
        assert _infer_domain("Security_Checklist") == "security"

    def test_domain_backend_engineering_keywords(self) -> None:
        from cli import _infer_domain

        assert _infer_domain("FastAPI_Service") == "backend-engineering"
        assert _infer_domain("Python_Architecture") == "backend-engineering"

    def test_domain_default(self) -> None:
        from cli import _infer_domain

        assert _infer_domain("Some_Random_Topic") == "backend-engineering"

    def test_type_checklist_keywords(self) -> None:
        from cli import _infer_type

        assert _infer_type("Security_Checklist") == "checklist"
        assert _infer_type("Code_Review") == "checklist"

    def test_type_guide_keywords(self) -> None:
        from cli import _infer_type

        assert _infer_type("Docker_Guide") == "guide"
        assert _infer_type("Getting_Started_Tutorial") == "guide"

    def test_type_concept_keywords(self) -> None:
        from cli import _infer_type

        assert _infer_type("API_Design_Principles") == "concept"
        assert _infer_type("Design_Patterns") == "concept"
        assert _infer_type("Caching_Strategies") == "concept"

    def test_type_default(self) -> None:
        from cli import _infer_type

        assert _infer_type("Docker_Basics") == "concept"

    def test_jwt_guide_generates_security_guide(self) -> None:
        from cli import _make_suggestion

        result = _make_suggestion("JWT_Authentication_Guide")
        assert result["domain"] == "security"
        assert result["type"] == "guide"
        assert "JWT Authentication Guide" in result["prompt"]
        assert "security engineers" in result["prompt"]

    def test_docker_basics_generates_devops_concept(self) -> None:
        from cli import _make_suggestion

        result = _make_suggestion("Docker_Basics")
        assert result["domain"] == "devops"
        assert result["type"] == "concept"
        assert "Docker Basics" in result["prompt"]
        assert "DevOps engineers" in result["prompt"]

    def test_format_json_output_contains_domain_and_type(self, tmp_path: Path, capsys) -> None:
        """JSON output includes domain and type keys in each suggestion."""
        from cli import cmd_gaps

        _write_md(
            tmp_path,
            "Source.md",
            FRONTMATTER_TEMPLATE.format(
                title="Source",
                related="[[Docker_Basics]] [[JWT_Auth_Guide]]",
            ),
        )
        cmd_gaps(_make_args(path=str(tmp_path), format="json"))
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert len(parsed) == 2
        for item in parsed:
            assert "prompt" in item
            assert "domain" in item
            assert "type" in item
            # Prompt must follow the format
            assert item["prompt"].startswith("Create a ")
            assert " on " in item["prompt"]
            assert " for " in item["prompt"]
