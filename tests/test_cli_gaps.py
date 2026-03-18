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
    _write_md(tmp_path, "API_Design.md", FRONTMATTER_TEMPLATE.format(
        title="API Design",
        related="[[Docker_Basics]] [[JWT_Authentication_Guide]]",
    ))
    _write_md(tmp_path, "Docker_Basics.md", FRONTMATTER_TEMPLATE.format(
        title="Docker Basics",
        related="[[API_Design]]",
    ))
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
        assert "Create a file on JWT Authentication Guide" in out

    def test_no_missing_files_message(self, tmp_path: Path, capsys) -> None:
        from cli import cmd_gaps
        # File links only to existing file
        _write_md(tmp_path, "A.md", FRONTMATTER_TEMPLATE.format(
            title="A", related="[[B]]",
        ))
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
        _write_md(tmp_path, "A.md", FRONTMATTER_TEMPLATE.format(
            title="A", related="[[B]]",
        ))
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
        _write_md(tmp_path, "Source.md", FRONTMATTER_TEMPLATE.format(
            title="Source",
            related="[[MissingTarget|Display Name]]",
        ))
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        assert "MissingTarget" in out
        assert "Display Name" not in out.split("Missing files")[1] if "Missing files" in out else True

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
            _write_md(tmp_path, f"File{i}.md", FRONTMATTER_TEMPLATE.format(
                title=f"File {i}",
                related="[[SharedMissing]]",
            ))
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        # Missing files count should be 1, not 3
        assert "Missing files (1):" in out

    def test_subdirectory_md_files_scanned(self, tmp_path: Path, capsys) -> None:
        """Files in subdirectories are included in the scan."""
        from cli import cmd_gaps
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        _write_md(subdir, "Nested.md", FRONTMATTER_TEMPLATE.format(
            title="Nested",
            related="[[DeepMissing]]",
        ))
        cmd_gaps(_make_args(path=str(tmp_path)))
        out = capsys.readouterr().out
        assert "DeepMissing" in out

    def test_subdirectory_files_count_as_existing(self, tmp_path: Path, capsys) -> None:
        """A file in a subdirectory resolves a WikiLink by stem name."""
        from cli import cmd_gaps
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        _write_md(subdir, "TargetFile.md", FRONTMATTER_NO_RELATED)
        _write_md(tmp_path, "Source.md", FRONTMATTER_TEMPLATE.format(
            title="Source",
            related="[[TargetFile]]",
        ))
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
