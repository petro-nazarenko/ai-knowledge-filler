"""Targeted coverage gap tests for AKF v0.4.2."""
from __future__ import annotations
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from akf.pipeline import GenerateResult, ValidateResult, Pipeline
from akf.validator import (
    validate, _check_title_type, _check_enum_fields, _check_dates,
    _check_tags, _check_related, _parse_taxonomy_file, _default_taxonomy,
    _load_taxonomy,
)
from akf.config import get_config, reset_config, load_config, AKFConfig, AKFEnums
from akf.validation_error import ErrorCode, Severity, ValidationError
from akf.error_normalizer import (
    normalize_errors, _render_missing_field, _render_type_mismatch,
    _render_taxonomy_violation, _render_date_sequence, _render_generic,
)
from akf.commit_gate import _atomic_write
from akf.retry_controller import RetryResult


@pytest.fixture(autouse=True)
def clear_config_cache():
    reset_config()
    yield
    reset_config()


VALID_DOC = textwrap.dedent("""
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
    Test.

    ## Conclusion
    Done.
""").lstrip()


def make_provider(content=None, raises=None):
    p = MagicMock()
    p.display_name = "Mock"
    p.model_name = "mock-model"
    if raises:
        p.generate.side_effect = raises
    else:
        p.generate.return_value = content or VALID_DOC
    return p


# ── Pipeline ──────────────────────────────────────────────────────────────────

class TestGenerateResultRepr:
    def test_valid(self):
        r = GenerateResult(success=True, content="x", attempts=2)
        assert "VALID" in repr(r) and "attempts=2" in repr(r)

    def test_invalid(self):
        r = GenerateResult(success=False, content="", errors=["e1", "e2"])
        assert "INVALID" in repr(r) and "errors=2" in repr(r)


class TestValidateResultRepr:
    def test_valid(self):
        assert "VALID" in repr(ValidateResult(valid=True))

    def test_invalid(self):
        r = ValidateResult(valid=False, errors=["e"], warnings=["w"])
        assert "INVALID" in repr(r) and "warnings=1" in repr(r)


class TestPipelineLog:
    def test_verbose(self, capsys):
        Pipeline(verbose=True)._log("hello")
        assert "hello" in capsys.readouterr().out

    def test_silent(self, capsys):
        Pipeline(verbose=False)._log("x")
        assert capsys.readouterr().out == ""


class TestPipelineLoadSystemPrompt:
    def test_cache_hit(self):
        p = Pipeline()
        p._system_prompt = "cached"
        assert p._load_system_prompt() == "cached"

    def test_loads_from_package(self):
        import akf as _pkg
        sp = Path(_pkg.__file__).parent / "system_prompt.md"
        if not sp.exists():
            pytest.skip("system_prompt.md not installed")
        p = Pipeline()
        p._system_prompt = None
        result = p._load_system_prompt()
        assert len(result) > 10


class TestExtractFilename:
    def test_from_title(self):
        name = Pipeline._extract_filename('title: "Docker Net"\ntype: guide\n', "x")
        assert name.endswith(".md")

    def test_fallback_prompt(self):
        name = Pipeline._extract_filename("no title", "create guide docker")
        assert name.endswith(".md")


class TestPipelineGenerate:
    def test_provider_error(self, tmp_path):
        p = Pipeline(output=str(tmp_path))
        p._system_prompt = "## ROLE\nGen."
        with patch("llm_providers.get_provider", side_effect=ValueError("no prov")):
            r = p.generate("prompt")
        assert not r.success and "no prov" in str(r.errors)

    def test_llm_exception(self, tmp_path):
        p = Pipeline(output=str(tmp_path))
        p._system_prompt = "## ROLE\nGen."
        with patch("llm_providers.get_provider",
                   return_value=make_provider(raises=RuntimeError("timeout"))):
            r = p.generate("prompt")
        assert not r.success and "timeout" in str(r.errors)

    def test_retry_triggered(self, tmp_path):
        p = Pipeline(output=str(tmp_path))
        p._system_prompt = "## ROLE\nGen."
        err = ValidationError(code=ErrorCode.TAXONOMY_VIOLATION, field="domain",
                              expected=["devops"], received="INVALID")
        fake_retry = RetryResult(success=True, document=VALID_DOC, attempts=2,
                                 abort_reason=None, errors=[])
        with patch("llm_providers.get_provider", return_value=make_provider()), \
             patch("akf.validator.validate", return_value=[err]), \
             patch("akf.retry_controller.run_retry_loop", return_value=fake_retry) as mock_rl:
            p.generate("prompt")
        assert mock_rl.called

    def test_commit_failure_fallback_write(self, tmp_path):
        p = Pipeline(output=str(tmp_path))
        p._system_prompt = "## ROLE\nGen."
        from akf.commit_gate import CommitResult
        fake_commit = CommitResult(
            committed=False, path=None,
            blocking_errors=[ValidationError(code=ErrorCode.MISSING_FIELD,
                field="domain", expected=["devops"], received=None)],
            schema_version="1.0.0",
        )
        with patch("llm_providers.get_provider", return_value=make_provider()), \
             patch("akf.validator.validate", return_value=[]), \
             patch("akf.commit_gate.commit", return_value=fake_commit):
            r = p.generate("prompt")
        assert not r.success and r.file_path is not None and r.file_path.exists()

    def test_rejected_domain_candidates(self, tmp_path):
        p = Pipeline(output=str(tmp_path))
        p._system_prompt = "## ROLE\nGen."
        err = ValidationError(code=ErrorCode.TAXONOMY_VIOLATION, field="domain",
                              expected=["devops"], received="backend")
        fake_retry = RetryResult(success=True, document=VALID_DOC, attempts=2,
                                 abort_reason=None, errors=[err])
        with patch("llm_providers.get_provider", return_value=make_provider()), \
             patch("akf.validator.validate", return_value=[err]), \
             patch("akf.retry_controller.run_retry_loop", return_value=fake_retry) as mock_rl:
            p.generate("prompt")
        assert mock_rl.called


# ── Validator ─────────────────────────────────────────────────────────────────

class TestTitleType:
    def test_int(self):
        assert _check_title_type({"title": 42})[0].code == ErrorCode.TYPE_MISMATCH

    def test_float(self):
        assert len(_check_title_type({"title": 3.14})) == 1

    def test_str_ok(self):
        assert _check_title_type({"title": "ok"}) == []

    def test_absent(self):
        assert _check_title_type({}) == []


class TestEnumFields:
    def test_none_skipped(self):
        assert _check_enum_fields({"type": None}, get_config()) == []

    def test_invalid_type(self):
        assert _check_enum_fields({"type": "document"}, get_config())[0].field == "type"


class TestDates:
    def test_wrong_format(self):
        assert any(e.field == "created" for e in
                   _check_dates({"created": "12-02-2026", "updated": "2026-02-12"}))

    def test_unparseable(self):
        assert any(e.field == "created" for e in
                   _check_dates({"created": "not-a-date", "updated": "2026-02-12"}))


class TestTags:
    def test_not_list(self):
        assert _check_tags({"tags": "api"})[0].code == ErrorCode.TYPE_MISMATCH

    def test_too_few(self):
        assert len(_check_tags({"tags": ["a", "b"]})) == 1

    def test_absent(self):
        assert _check_tags({}) == []

    def test_ok(self):
        assert _check_tags({"tags": ["a", "b", "c"]}) == []


class TestRelated:
    def test_empty_list(self):
        assert _check_related({"related": []})[0].severity == Severity.WARNING

    def test_absent(self):
        assert _check_related({})[0].severity == Severity.WARNING

    def test_ok(self):
        assert _check_related({"related": ["[[N]]"]}) == []


class TestLegacyTaxonomy:
    def test_with_path(self, tmp_path):
        f = tmp_path / "tax.md"
        f.write_text("#### api-design\n#### devops\n")
        assert "api-design" in _load_taxonomy(f)

    def test_none(self):
        assert "devops" in _load_taxonomy(None)

    def test_default(self):
        assert "security" in _default_taxonomy()

    def test_parse_file(self, tmp_path):
        f = tmp_path / "tax.md"
        f.write_text("#### api-design\n#### legacy (DEPRECATED -> x)\n#### devops\n")
        d = _parse_taxonomy_file(f)
        assert "api-design" in d and "legacy" not in d

    def test_parse_empty_fallback(self, tmp_path):
        f = tmp_path / "e.md"
        f.write_text("# nothing\n")
        assert len(_parse_taxonomy_file(f)) > 0

    def test_validate_uses_taxonomy_path(self, tmp_path):
        f = tmp_path / "tax.md"
        f.write_text("#### custom-domain\n")
        doc = textwrap.dedent("""
            ---
            schema_version: "1.0.0"
            title: "Test"
            type: guide
            domain: custom-domain
            level: intermediate
            status: active
            tags: [a, b, c]
            related:
              - "[[X]]"
            created: 2026-02-26
            updated: 2026-02-26
            ---
            ## Purpose
            Test.
        """).lstrip()
        with patch("akf.validator.get_config", return_value=AKFConfig(source=None)):
            errors = validate(doc, taxonomy_path=f)
        assert not any(e.field == "domain" and e.code == ErrorCode.TAXONOMY_VIOLATION
                       for e in errors)


# ── Error Normalizer ──────────────────────────────────────────────────────────

class TestRenderMissingField:
    def test_domain_list(self):
        e = ValidationError(code=ErrorCode.MISSING_FIELD, field="domain",
                            expected=["api-design", "devops"], received=None)
        assert "api-design" in _render_missing_field(e)

    def test_other(self):
        e = ValidationError(code=ErrorCode.MISSING_FIELD, field="title",
                            expected="str", received=None)
        assert "title" in _render_missing_field(e)


class TestRenderTypeMismatch:
    def test_tags(self):
        e = ValidationError(code=ErrorCode.TYPE_MISMATCH, field="tags",
                            expected=list, received="api")
        assert "YAML list" in _render_type_mismatch(e)

    def test_other(self):
        e = ValidationError(code=ErrorCode.TYPE_MISMATCH, field="title",
                            expected=str, received=42)
        assert "title" in _render_type_mismatch(e)


class TestRenderTaxonomy:
    def test_renders(self):
        e = ValidationError(code=ErrorCode.TAXONOMY_VIOLATION, field="domain",
                            expected=["api-design"], received="backend")
        assert "backend" in _render_taxonomy_violation(e)


class TestRenderDateSeq:
    def test_renders(self):
        from datetime import date
        from akf.validation_error import date_sequence_violation
        e = date_sequence_violation(date(2026, 3, 1), date(2026, 2, 1))
        assert "created" in _render_date_sequence(e)


class TestRenderGeneric:
    def test_renders(self):
        e = ValidationError(code=ErrorCode.SCHEMA_VIOLATION, field="fm",
                            expected="x", received="y")
        assert "fm" in _render_generic(e)


class TestNormalizeErrors:
    def test_empty(self):
        assert not normalize_errors([]).has_blocking_errors

    def test_warning_not_blocking(self):
        w = ValidationError(code=ErrorCode.SCHEMA_VIOLATION, field="related",
                            expected="list", received="absent",
                            severity=Severity.WARNING)
        p = normalize_errors([w])
        assert not p.has_blocking_errors and p.warning_count == 1

    def test_mixed(self):
        err = ValidationError(code=ErrorCode.MISSING_FIELD, field="title",
                              expected="str", received=None)
        warn = ValidationError(code=ErrorCode.SCHEMA_VIOLATION, field="related",
                               expected="list", received="absent",
                               severity=Severity.WARNING)
        p = normalize_errors([err, warn])
        assert p.has_blocking_errors and p.error_count == 1 and p.warning_count == 1


# ── Commit Gate ───────────────────────────────────────────────────────────────

class TestAtomicWrite:
    def test_cleans_tmp_on_error(self, tmp_path):
        with patch("os.replace", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                _atomic_write("content", tmp_path / "out.md")
        assert list(tmp_path.glob(".akf_tmp_*.md")) == []


# ── Config ────────────────────────────────────────────────────────────────────

class TestConfigParse:
    def test_empty_domains_fallback(self, tmp_path):
        f = tmp_path / "akf.yaml"
        f.write_text("schema_version: '1.0.0'\ntaxonomy:\n  domains: []\n")
        from akf.config import _parse_yaml
        assert "devops" in _parse_yaml(f).domains

    def test_non_list_fallback(self, tmp_path):
        f = tmp_path / "akf.yaml"
        f.write_text("schema_version: '1.0.0'\ntaxonomy:\n  domains: not-a-list\n")
        from akf.config import _parse_yaml
        assert "devops" in _parse_yaml(f).domains


class TestLoadConfig:
    def test_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(path=tmp_path / "missing.yaml")

    def test_found_loads(self, tmp_path):
        f = tmp_path / "akf.yaml"
        f.write_text("schema_version: '1.0.0'\ntaxonomy:\n  domains:\n    - custom\n    - devops\n")
        cfg = load_config(path=f)
        assert "custom" in cfg.domains and cfg.source == f.resolve()
