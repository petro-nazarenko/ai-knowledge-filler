"""
tests/unit/test_pipeline_enrich.py
────────────────────────────────────
Unit tests for Pipeline.enrich() and Pipeline.enrich_dir().

Patch targets use the module where each symbol is DEFINED,
because enrich() uses local imports inside the method body.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from akf.pipeline import Pipeline, EnrichResult


# ─── Sample content ───────────────────────────────────────────────────────────

VALID_GENERATED_YAML = """\
title: Generated Title
type: guide
domain: ai-system
level: intermediate
status: active
tags:
  - ai
  - knowledge
  - automation
created: 2026-02-27
updated: 2026-02-27
"""

VALID_FRONTMATTER_FILE = """\
---
title: Existing Title
type: reference
domain: ai-system
level: advanced
status: active
tags:
  - akf
  - ai
  - system
created: 2025-01-01
updated: 2026-02-01
---
# Existing Document
Content here.
"""

INCOMPLETE_FRONTMATTER_FILE = """\
---
title: Partial Title
---
# Partial Document
Some content about AI systems.
"""

NO_FRONTMATTER_FILE = """\
# No Frontmatter
This document has no YAML at all.
"""

EMPTY_FILE = ""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mock_cfg():
    cfg = MagicMock()
    cfg.domains = ["ai-system", "devops"]
    return cfg


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_provider():
    p = MagicMock()
    p.model_name = "mock-model"
    p.generate.return_value = VALID_GENERATED_YAML
    return p


@pytest.fixture()
def mock_writer():
    return MagicMock()


@pytest.fixture()
def pipeline(mock_writer):
    p = Pipeline(model="auto", telemetry_path=None, verbose=False)
    p.writer = mock_writer
    p.model_name = "auto"
    return p


@pytest.fixture()
def tmp_md(tmp_path):
    def _make(name, content):
        f = tmp_path / name
        f.write_text(content, encoding="utf-8")
        return f
    return _make


# ─── enrich() ─────────────────────────────────────────────────────────────────

class TestPipelineEnrich:

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    @patch("llm_providers.get_provider")
    def test_no_frontmatter_enriched(self, mock_get_provider, _mv, _mc, pipeline, tmp_md, mock_provider):
        mock_get_provider.return_value = mock_provider
        f = tmp_md("no_fm.md", NO_FRONTMATTER_FILE)
        result = pipeline.enrich(path=f)
        assert result.success is True
        assert result.status == "enriched"
        assert f.read_text(encoding="utf-8").startswith("---")

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    @patch("llm_providers.get_provider")
    def test_incomplete_frontmatter_enriched(self, mock_get_provider, _mv, _mc, pipeline, tmp_md, mock_provider):
        mock_get_provider.return_value = mock_provider
        f = tmp_md("partial.md", INCOMPLETE_FRONTMATTER_FILE)
        result = pipeline.enrich(path=f, force=False)
        assert result.success is True
        assert result.status == "enriched"
        assert "Partial Title" in f.read_text(encoding="utf-8")

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    def test_valid_frontmatter_skipped(self, _mv, _mc, pipeline, tmp_md):
        f = tmp_md("valid.md", VALID_FRONTMATTER_FILE)
        result = pipeline.enrich(path=f, force=False)
        assert result.status == "skipped"
        assert result.skip_reason == "valid_frontmatter"

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    @patch("llm_providers.get_provider")
    def test_force_overwrites_valid(self, mock_get_provider, _mv, _mc, pipeline, tmp_md, mock_provider):
        mock_get_provider.return_value = mock_provider
        f = tmp_md("valid_force.md", VALID_FRONTMATTER_FILE)
        result = pipeline.enrich(path=f, force=True)
        assert result.status == "enriched"
        mock_provider.generate.assert_called()

    def test_empty_file_returns_warning(self, pipeline, tmp_md):
        f = tmp_md("empty.md", EMPTY_FILE)
        result = pipeline.enrich(path=f)
        assert result.status == "warning"
        assert result.skip_reason == "empty_file"

    def test_non_markdown_skipped(self, pipeline, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("some text", encoding="utf-8")
        result = pipeline.enrich(path=f)
        assert result.status == "skipped"
        assert result.skip_reason == "non_markdown"

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    @patch("llm_providers.get_provider")
    def test_dry_run_no_file_write(self, mock_get_provider, _mv, _mc, pipeline, tmp_md, mock_provider, capsys):
        mock_get_provider.return_value = mock_provider
        f = tmp_md("dry.md", NO_FRONTMATTER_FILE)
        mtime_before = f.stat().st_mtime
        pipeline.enrich(path=f, dry_run=True)
        assert f.stat().st_mtime == pytest.approx(mtime_before, abs=0.01)
        assert "---" in capsys.readouterr().out

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    @patch("llm_providers.get_provider")
    def test_dry_run_no_telemetry(self, mock_get_provider, _mv, _mc, pipeline, tmp_md, mock_provider, mock_writer):
        mock_get_provider.return_value = mock_provider
        pipeline.writer = mock_writer
        f = tmp_md("dry_tel.md", NO_FRONTMATTER_FILE)
        pipeline.enrich(path=f, dry_run=True)
        mock_writer.write.assert_not_called()

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    @patch("llm_providers.get_provider")
    def test_output_dir_copies_file(self, mock_get_provider, _mv, _mc, pipeline, tmp_md, tmp_path, mock_provider):
        mock_get_provider.return_value = mock_provider
        f = tmp_md("orig.md", NO_FRONTMATTER_FILE)
        out_dir = tmp_path / "enriched"
        result = pipeline.enrich(path=f, output=out_dir)
        assert result.success is True
        assert (out_dir / "orig.md").exists()

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    @patch("llm_providers.get_provider")
    def test_created_never_changes(self, mock_get_provider, _mv, _mc, pipeline, tmp_md, mock_provider):
        mock_get_provider.return_value = mock_provider
        f = tmp_md("created.md", "---\ncreated: 2024-01-15\n---\n# Doc\nContent.")
        pipeline.enrich(path=f, force=True)
        import yaml
        parts = f.read_text(encoding="utf-8").split("---", 2)
        meta = yaml.safe_load(parts[1])
        assert str(meta.get("created")) == "2024-01-15"

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    @patch("llm_providers.get_provider")
    def test_telemetry_event_emitted(self, mock_get_provider, _mv, _mc, pipeline, tmp_md, mock_provider, mock_writer):
        mock_get_provider.return_value = mock_provider
        pipeline.writer = mock_writer
        f = tmp_md("tel.md", NO_FRONTMATTER_FILE)
        pipeline.enrich(path=f)
        mock_writer.write.assert_called_once()
        event = mock_writer.write.call_args[0][0]
        assert event.event_type == "enrich"
        assert event.skipped is False

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.retry_controller.run_retry_loop")
    @patch("akf.validator.validate")
    @patch("llm_providers.get_provider")
    def test_failed_after_max_retries(self, mock_get_provider, mock_validate, mock_retry, _mc, pipeline, tmp_md, mock_provider):
        from akf.validation_error import ValidationError, ErrorCode, Severity
        mock_get_provider.return_value = mock_provider
        blocking = ValidationError(
            code=ErrorCode.TAXONOMY_VIOLATION, field="domain",
            expected=["ai-system"], received="invalid-domain",
            severity=Severity.ERROR,
        )
        mock_validate.return_value = [blocking]
        retry_result = MagicMock()
        retry_result.document = NO_FRONTMATTER_FILE
        retry_result.attempts = 3
        retry_result.success = False
        retry_result.errors = [blocking]
        mock_retry.return_value = retry_result
        f = tmp_md("fail.md", NO_FRONTMATTER_FILE)
        result = pipeline.enrich(path=f)
        assert result.status == "failed"
        assert result.success is False


# ─── enrich_dir() ─────────────────────────────────────────────────────────────

class TestPipelineEnrichDir:

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    @patch("llm_providers.get_provider")
    def test_processes_all_md_files(self, mock_get_provider, _mv, _mc, pipeline, tmp_path, mock_provider):
        mock_get_provider.return_value = mock_provider
        (tmp_path / "a.md").write_text(NO_FRONTMATTER_FILE, encoding="utf-8")
        (tmp_path / "b.md").write_text(NO_FRONTMATTER_FILE, encoding="utf-8")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "c.md").write_text(NO_FRONTMATTER_FILE, encoding="utf-8")
        (tmp_path / "ignore.txt").write_text("not markdown", encoding="utf-8")
        results = pipeline.enrich_dir(path=tmp_path)
        assert len(results) == 3

    @patch("akf.config.get_config", return_value=_mock_cfg())
    @patch("akf.validator.validate", return_value=[])
    @patch("llm_providers.get_provider")
    def test_returns_list_of_enrich_results(self, mock_get_provider, _mv, _mc, pipeline, tmp_path, mock_provider):
        mock_get_provider.return_value = mock_provider
        (tmp_path / "doc.md").write_text(NO_FRONTMATTER_FILE, encoding="utf-8")
        results = pipeline.enrich_dir(path=tmp_path)
        assert len(results) == 1
        assert isinstance(results[0], EnrichResult)

    def test_empty_dir_returns_empty_list(self, pipeline, tmp_path):
        assert pipeline.enrich_dir(path=tmp_path) == []


# ─── EnrichResult dataclass ───────────────────────────────────────────────────

class TestEnrichResult:
    def test_defaults(self):
        r = EnrichResult(success=True, path=Path("x.md"), status="enriched")
        assert r.attempts == 0
        assert r.errors == []
        assert r.existing_fields == []
        assert r.generated_fields == []
        assert r.generation_id == ""
        assert r.skip_reason == ""
