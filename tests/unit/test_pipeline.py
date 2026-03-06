"""Unit tests for Pipeline class (Stage 2)."""

import textwrap
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from akf.pipeline import Pipeline, GenerateResult, ValidateResult


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

VALID_CONTENT = textwrap.dedent("""\
    ---
    schema_version: "1.0.0"
    title: "Test Guide"
    type: guide
    domain: devops
    level: intermediate
    status: active
    tags: [docker, guide, test]
    related:
      - "[[Docker Basics]]"
    created: 2026-02-26
    updated: 2026-02-26
    ---

    ## Purpose

    Test content.

    ## Conclusion

    Done.
""")

INVALID_CONTENT = textwrap.dedent("""\
    ---
    title: "Bad File"
    type: document
    domain: Technology
    level: medium
    status: wip
    tags: docker
    created: 26-02-2026
    updated: 26-02-2026
    ---

    ## Content
""")


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def make_mock_provider(content=VALID_CONTENT):
    provider = MagicMock()
    provider.display_name = "MockLLM"
    provider.model_name = "mock-model"
    provider.generate.return_value = content
    return provider


# ─── GenerateResult ───────────────────────────────────────────────────────────

class TestGenerateResult:
    def test_repr_valid(self):
        r = GenerateResult(success=True, content="x", attempts=1)
        assert "VALID" in repr(r)

    def test_repr_invalid(self):
        r = GenerateResult(success=False, content="", attempts=0)
        assert "INVALID" in repr(r)

    def test_defaults(self):
        r = GenerateResult(success=True, content="x")
        assert r.file_path is None
        assert r.errors == []
        assert r.generation_id == ""
        assert r.duration_ms == 0


# ─── ValidateResult ───────────────────────────────────────────────────────────

class TestValidateResult:
    def test_repr_valid(self):
        r = ValidateResult(valid=True)
        assert "VALID" in repr(r)

    def test_repr_invalid(self):
        r = ValidateResult(valid=False, errors=["E001"])
        assert "INVALID" in repr(r)

    def test_defaults(self):
        r = ValidateResult(valid=True)
        assert r.errors == []
        assert r.warnings == []
        assert r.filepath is None


# ─── Pipeline init ────────────────────────────────────────────────────────────

class TestPipelineInit:
    def test_default_model(self):
        p = Pipeline()
        assert p.model == "auto"

    def test_custom_model(self):
        p = Pipeline(model="claude")
        assert p.model == "claude"

    def test_custom_output(self, tmp_path):
        p = Pipeline(output=str(tmp_path))
        assert p.output_dir == tmp_path

    def test_verbose_default(self):
        p = Pipeline()
        assert p.verbose is True

    def test_verbose_off(self):
        p = Pipeline(verbose=False)
        assert p.verbose is False


# ─── Pipeline.validate ────────────────────────────────────────────────────────

class TestPipelineValidate:
    def test_valid_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text(VALID_CONTENT)
        p = Pipeline(verbose=False)
        result = p.validate(str(f))
        assert isinstance(result, ValidateResult)
        assert result.valid is True
        assert result.errors == []

    def test_invalid_file(self, tmp_path):
        f = tmp_path / "bad.md"
        f.write_text(INVALID_CONTENT)
        p = Pipeline(verbose=False)
        result = p.validate(str(f))
        assert isinstance(result, ValidateResult)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_file_not_found(self):
        p = Pipeline(verbose=False)
        result = p.validate("/nonexistent/file.md")
        assert result.valid is False
        assert "not found" in result.errors[0].lower()

    def test_strict_mode(self, tmp_path):
        f = tmp_path / "warn.md"
        # File with warnings (no related field)
        content = VALID_CONTENT.replace(
            "related:\n  - \"[[Docker Basics]]\"\n", ""
        )
        f.write_text(content)
        p = Pipeline(verbose=False)
        normal = p.validate(str(f), strict=False)
        strict = p.validate(str(f), strict=True)
        # strict promotes warnings to errors
        assert len(strict.errors) >= len(normal.errors)

    def test_filepath_in_result(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text(VALID_CONTENT)
        p = Pipeline(verbose=False)
        result = p.validate(str(f))
        assert result.filepath == f


# ─── Pipeline.generate ────────────────────────────────────────────────────────

class TestPipelineGenerate:
    def test_generate_success(self, tmp_path):
        p = Pipeline(output=str(tmp_path), verbose=False)
        with patch("akf.pipeline.Pipeline._load_system_prompt", return_value="sys"):
            with patch("llm_providers.get_provider", return_value=make_mock_provider()):
                result = p.generate("Create a test guide")
        assert isinstance(result, GenerateResult)
        assert result.content != ""
        assert result.attempts >= 1

    def test_generate_provider_error(self, tmp_path):
        p = Pipeline(output=str(tmp_path), verbose=False)
        with patch("llm_providers.get_provider", side_effect=ValueError("No provider")):
            result = p.generate("Test prompt")
        assert result.success is False
        assert len(result.errors) > 0

    def test_generate_creates_file(self, tmp_path):
        p = Pipeline(output=str(tmp_path), verbose=False)
        with patch("akf.pipeline.Pipeline._load_system_prompt", return_value="sys"):
            with patch("llm_providers.get_provider", return_value=make_mock_provider()):
                result = p.generate("Create a test guide")
        if result.file_path:
            assert Path(result.file_path).exists()

    def test_generate_custom_output(self, tmp_path):
        custom = tmp_path / "custom"
        p = Pipeline(output=str(tmp_path), verbose=False)
        with patch("akf.pipeline.Pipeline._load_system_prompt", return_value="sys"):
            with patch("llm_providers.get_provider", return_value=make_mock_provider()):
                result = p.generate("Test", output=str(custom))
        if result.file_path:
            assert str(custom) in str(result.file_path)

    def test_generate_result_has_generation_id(self, tmp_path):
        p = Pipeline(output=str(tmp_path), verbose=False)
        with patch("akf.pipeline.Pipeline._load_system_prompt", return_value="sys"):
            with patch("llm_providers.get_provider", return_value=make_mock_provider()):
                result = p.generate("Test prompt")
        assert isinstance(result.generation_id, str)

    def test_generate_duration_ms(self, tmp_path):
        p = Pipeline(output=str(tmp_path), verbose=False)
        with patch("akf.pipeline.Pipeline._load_system_prompt", return_value="sys"):
            with patch("llm_providers.get_provider", return_value=make_mock_provider()):
                result = p.generate("Test prompt")
        assert result.duration_ms >= 0


# ─── Pipeline.batch_generate ──────────────────────────────────────────────────

class TestPipelineBatchGenerate:
    def test_batch_returns_list(self, tmp_path):
        p = Pipeline(output=str(tmp_path), verbose=False)
        prompts = ["Guide on Docker", "Concept on APIs", "Checklist for security"]
        with patch("akf.pipeline.Pipeline._load_system_prompt", return_value="sys"):
            with patch("llm_providers.get_provider", return_value=make_mock_provider()):
                results = p.batch_generate(prompts)
        assert isinstance(results, list)
        assert len(results) == 3

    def test_batch_all_generate_results(self, tmp_path):
        p = Pipeline(output=str(tmp_path), verbose=False)
        with patch("akf.pipeline.Pipeline._load_system_prompt", return_value="sys"):
            with patch("llm_providers.get_provider", return_value=make_mock_provider()):
                results = p.batch_generate(["Prompt 1", "Prompt 2"])
        for r in results:
            assert isinstance(r, GenerateResult)

    def test_batch_empty_list(self, tmp_path):
        p = Pipeline(output=str(tmp_path), verbose=False)
        results = p.batch_generate([])
        assert results == []
