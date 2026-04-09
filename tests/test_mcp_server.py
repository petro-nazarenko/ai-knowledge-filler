"""
tests/test_mcp_server.py — AKF MCP Server tests (v0.6.0)

Patches target top-level names in akf.mcp_server (Pipeline, validate).
No mcp package required — FastMCP only imported inside run(), not tested here.

13 tests, 4 classes.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

# ─── shared fixtures ─────────────────────────────────────────────────────────

VALID_MD = textwrap.dedent("""\
    ---
    title: "Test Document"
    type: concept
    domain: ai-system
    level: beginner
    status: active
    tags: [testing, mcp, akf]
    created: 2026-03-01
    updated: 2026-03-01
    ---

    ## Body

    Content here.
""")

INVALID_MD = textwrap.dedent("""\
    ---
    title: "Bad Doc"
    type: UNKNOWN_TYPE
    domain: not-a-real-domain
    level: expert
    status: active
    tags: [x]
    created: 2026-03-01
    updated: 2026-03-01
    ---
""")

NO_FRONTMATTER_MD = "## Just a heading\n\nNo YAML here.\n"


def _gen_result(
    success: bool = True,
    file_path: str | None = "/vault/test.md",
    attempts: int = 1,
    generation_id: str = "uuid-test",
    errors: list | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        success=success,
        file_path=Path(file_path) if file_path else None,
        attempts=attempts,
        generation_id=generation_id,
        errors=errors or [],
    )


def _enrich_result(path: str, status: str) -> SimpleNamespace:
    return SimpleNamespace(
        path=Path(path),
        status=status,
        success=status == "enriched",
        skip_reason=None,
        attempts=1,
        errors=[],
    )


def _make_validation_error(severity_value: str = "error") -> MagicMock:
    e = MagicMock()
    e.severity = MagicMock()
    e.severity.value = severity_value
    # Match how Severity.ERROR comparison works
    from akf.validation_error import Severity

    e.severity = Severity.ERROR if severity_value == "error" else Severity.WARNING
    e.__str__ = lambda self: f"E001 ({severity_value})"
    return e


# ─── TestAkfGenerateTool ─────────────────────────────────────────────────────


class TestAkfGenerateTool:

    @patch("akf.mcp_server.Pipeline")
    def test_valid_prompt_returns_success(self, MockPipeline):
        """Valid prompt → success=True, file_path not None."""
        MockPipeline.return_value.generate.return_value = _gen_result()

        from akf.mcp_server import akf_generate

        response = akf_generate(prompt="Explain AKF validation pipeline")

        assert response["success"] is True
        assert response["file_path"] is not None
        assert response["attempts"] == 1
        assert response["generation_id"] == "uuid-test"
        assert response["errors"] == []

    @patch("akf.mcp_server.Pipeline")
    def test_domain_and_type_hints_forwarded(self, MockPipeline):
        """domain/type hints passed to pipeline.generate."""
        mock_instance = MockPipeline.return_value
        mock_instance.generate.return_value = _gen_result()

        from akf.mcp_server import akf_generate

        akf_generate(prompt="Guide to API design", domain="api-design", type="guide", model="groq")

        mock_instance.generate.assert_called_once_with(
            "Guide to API design",
            model="groq",
            hints={"domain": "api-design", "type": "guide"},
        )

    @patch("akf.mcp_server.Pipeline")
    def test_provider_error_propagates(self, MockPipeline):
        """Pipeline raises → exception propagates."""
        MockPipeline.return_value.generate.side_effect = RuntimeError("GROQ_API_KEY not set")

        from akf.mcp_server import akf_generate

        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            akf_generate(prompt="test", model="groq")


# ─── TestAkfValidateTool ─────────────────────────────────────────────────────


class TestAkfValidateTool:

    @patch("akf.mcp_server.validate")
    def test_valid_file(self, mock_validate, tmp_path):
        """Valid file → is_valid=True, errors=[]."""
        f = tmp_path / "valid.md"
        f.write_text(VALID_MD, encoding="utf-8")
        mock_validate.return_value = []

        from akf.mcp_server import akf_validate

        response = akf_validate(path=str(f))

        assert response["is_valid"] is True
        assert response["errors"] == []

    @patch("akf.mcp_server.validate")
    def test_invalid_file(self, mock_validate, tmp_path):
        """Invalid file → is_valid=False, errors not empty."""
        f = tmp_path / "invalid.md"
        f.write_text(INVALID_MD, encoding="utf-8")

        err = _make_validation_error("error")
        mock_validate.return_value = [err]

        from akf.mcp_server import akf_validate

        response = akf_validate(path=str(f))

        assert response["is_valid"] is False
        assert len(response["errors"]) == 1

    @patch("akf.mcp_server.validate")
    def test_directory_returns_counts(self, mock_validate, tmp_path):
        """Directory with 3 files (2 valid, 1 invalid) → correct counts."""
        (tmp_path / "a.md").write_text(VALID_MD, encoding="utf-8")
        (tmp_path / "b.md").write_text(INVALID_MD, encoding="utf-8")
        (tmp_path / "c.md").write_text(VALID_MD, encoding="utf-8")

        err = _make_validation_error("error")

        def side_effect(content):
            return [err] if "UNKNOWN_TYPE" in content else []

        mock_validate.side_effect = side_effect

        from akf.mcp_server import akf_validate

        response = akf_validate(path=str(tmp_path))

        assert response["total"] == 3
        assert response["ok"] == 2
        assert response["failed"] == 1
        assert len(response["results"]) == 3

    def test_nonexistent_path_returns_error(self):
        """Non-existent path → error key in response."""
        from akf.mcp_server import akf_validate

        response = akf_validate(path="/nonexistent/path/file.md")

        assert "error" in response
        assert "/nonexistent/path/file.md" in response["error"]


# ─── TestAkfEnrichTool ───────────────────────────────────────────────────────


class TestAkfEnrichTool:

    @patch("akf.mcp_server.Pipeline")
    def test_file_enriched(self, MockPipeline, tmp_path):
        """File without frontmatter → status=enriched."""
        f = tmp_path / "bare.md"
        f.write_text(NO_FRONTMATTER_MD, encoding="utf-8")

        MockPipeline.return_value.enrich.return_value = _enrich_result(str(f), "enriched")

        from akf.mcp_server import akf_enrich

        response = akf_enrich(path=str(f))

        assert response["total"] == 1
        assert response["enriched"] == 1
        assert response["skipped"] == 0
        assert response["failed"] == 0

    @patch("akf.mcp_server.Pipeline")
    def test_file_skipped_no_force(self, MockPipeline, tmp_path):
        """File with frontmatter, force=False → skipped."""
        f = tmp_path / "existing.md"
        f.write_text(VALID_MD, encoding="utf-8")

        MockPipeline.return_value.enrich.return_value = _enrich_result(str(f), "skipped")

        from akf.mcp_server import akf_enrich

        response = akf_enrich(path=str(f), force=False)

        assert response["skipped"] == 1
        assert response["enriched"] == 0

    @patch("akf.mcp_server.Pipeline")
    def test_dry_run_forwarded(self, MockPipeline, tmp_path):
        """dry_run=True is forwarded to pipeline.enrich."""
        f = tmp_path / "bare.md"
        f.write_text(NO_FRONTMATTER_MD, encoding="utf-8")

        mock_instance = MockPipeline.return_value
        mock_instance.enrich.return_value = _enrich_result(str(f), "enriched")

        from akf.mcp_server import akf_enrich

        akf_enrich(path=str(f), dry_run=True)

        mock_instance.enrich.assert_called_once_with(
            path=f, force=False, dry_run=True, model="auto"
        )


# ─── TestAkfBatchTool ────────────────────────────────────────────────────────


class TestAkfBatchTool:

    @patch("akf.mcp_server.Pipeline")
    def test_valid_plan_three_items(self, MockPipeline):
        """Plan 3 items → total=3, ok=3."""
        plan = [
            {"prompt": "Concept A", "domain": "ai-system", "type": "concept"},
            {"prompt": "Guide B", "domain": "devops", "type": "guide"},
            {"prompt": "Ref C", "domain": "api-design", "type": "reference"},
        ]
        MockPipeline.return_value.batch_generate.return_value = [
            _gen_result(file_path=f"/vault/f{i}.md") for i in range(3)
        ]

        from akf.mcp_server import akf_batch

        response = akf_batch(plan=plan)

        assert response["total"] == 3
        assert response["ok"] == 3
        assert response["failed"] == 0
        assert len(response["results"]) == 3

    def test_empty_plan(self):
        """Empty plan → zeros, no Pipeline created."""
        from akf.mcp_server import akf_batch

        response = akf_batch(plan=[])

        assert response == {"total": 0, "ok": 0, "failed": 0, "results": []}

    @patch("akf.mcp_server.Pipeline")
    def test_partial_failure(self, MockPipeline):
        """2 ok + 1 fail → ok=2, failed=1."""
        plan = [{"prompt": "OK 1"}, {"prompt": "FAIL"}, {"prompt": "OK 2"}]
        MockPipeline.return_value.batch_generate.return_value = [
            _gen_result(success=True, file_path="/vault/ok1.md"),
            _gen_result(success=False, file_path=None, errors=[MagicMock()]),
            _gen_result(success=True, file_path="/vault/ok2.md"),
        ]

        from akf.mcp_server import akf_batch

        response = akf_batch(plan=plan)

        assert response["total"] == 3
        assert response["ok"] == 2
        assert response["failed"] == 1


# ─── TestAkfValidateStrictMode ───────────────────────────────────────────────


class TestAkfValidateStrictMode:

    @patch("akf.mcp_server.validate")
    def test_strict_file_includes_warnings(self, mock_validate, tmp_path):
        """strict=True on a file → warnings also included in errors list."""
        f = tmp_path / "warn.md"
        f.write_text(VALID_MD, encoding="utf-8")

        from akf.validation_error import Severity

        warn = _make_validation_error("warning")
        mock_validate.return_value = [warn]

        from akf.mcp_server import akf_validate

        response = akf_validate(path=str(f), strict=True)

        assert response["is_valid"] is False
        assert len(response["errors"]) == 1

    @patch("akf.mcp_server.validate")
    def test_strict_directory_includes_warnings(self, mock_validate, tmp_path):
        """strict=True on a directory → warnings also included in errors list."""
        (tmp_path / "a.md").write_text(VALID_MD, encoding="utf-8")
        (tmp_path / "b.md").write_text(VALID_MD, encoding="utf-8")

        from akf.validation_error import Severity

        warn = _make_validation_error("warning")
        mock_validate.return_value = [warn]

        from akf.mcp_server import akf_validate

        response = akf_validate(path=str(tmp_path), strict=True)

        assert response["total"] == 2
        assert response["failed"] == 2


# ─── TestAkfEnrichErrorPaths ──────────────────────────────────────────────────


class TestAkfEnrichErrorPaths:

    @patch("akf.mcp_server.Pipeline")
    def test_directory_enriched(self, MockPipeline, tmp_path):
        """Directory path → all .md files processed."""
        (tmp_path / "a.md").write_text(NO_FRONTMATTER_MD, encoding="utf-8")
        (tmp_path / "b.md").write_text(NO_FRONTMATTER_MD, encoding="utf-8")

        MockPipeline.return_value.enrich.side_effect = [
            _enrich_result(str(tmp_path / "a.md"), "enriched"),
            _enrich_result(str(tmp_path / "b.md"), "enriched"),
        ]

        from akf.mcp_server import akf_enrich

        response = akf_enrich(path=str(tmp_path))

        assert response["total"] == 2
        assert response["enriched"] == 2

    @patch("akf.mcp_server.Pipeline")
    def test_enrich_exception_caught(self, MockPipeline, tmp_path):
        """pipeline.enrich raises → caught and counted as failed."""
        f = tmp_path / "bad.md"
        f.write_text(NO_FRONTMATTER_MD, encoding="utf-8")

        MockPipeline.return_value.enrich.side_effect = RuntimeError("LLM error")

        from akf.mcp_server import akf_enrich

        response = akf_enrich(path=str(f))

        assert response["total"] == 1
        assert response["failed"] == 1

    def test_nonexistent_path_returns_error(self):
        """Non-existent path → error key in response."""
        from akf.mcp_server import akf_enrich

        response = akf_enrich(path="/nonexistent/path")

        assert "error" in response


# ─── TestMcpRun ───────────────────────────────────────────────────────────────


class TestMcpRun:

    def test_run_raises_import_error_when_mcp_missing(self):
        """ImportError raised when mcp package is not installed."""
        import builtins
        import sys
        from unittest.mock import patch

        original_import = builtins.__import__

        def import_blocker(name, *args, **kwargs):
            if name == "mcp.server.fastmcp" or name.startswith("mcp.server"):
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_blocker):
            from akf.mcp_server import run

            with pytest.raises(ImportError, match="mcp package not installed"):
                run()

    def test_run_registers_tools_and_calls_mcp_run(self):
        """run() registers the four tools and calls mcp.run()."""
        from unittest.mock import MagicMock, patch

        mock_mcp_instance = MagicMock()
        mock_fastmcp_class = MagicMock(return_value=mock_mcp_instance)
        mock_mcp_module = MagicMock()
        mock_mcp_module.FastMCP = mock_fastmcp_class

        import sys

        with patch.dict(sys.modules, {"mcp.server.fastmcp": mock_mcp_module}):
            from akf.mcp_server import run

            run(transport="stdio")

        mock_fastmcp_class.assert_called_once_with("akf")
        assert mock_mcp_instance.tool.call_count == 4
        mock_mcp_instance.run.assert_called_once_with(transport="stdio")
