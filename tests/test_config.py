"""
tests/test_config.py — Tests for akf.config (Phase 2.4 / CANON-DEFER-001)

Coverage targets:
  - load_config() search order (explicit path, env var, CWD, package defaults, built-in)
  - _parse_yaml() field parsing and fallback per-section
  - AKFConfig helpers: is_valid_domain, is_valid_enum, all_domains
  - get_config() singleton + reset_config()
  - Error cases: missing explicit path, invalid YAML
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest
import yaml

from akf.config import (
    AKFConfig,
    AKFEnums,
    get_config,
    load_config,
    reset_config,
    _DEFAULT_DOMAINS,
    _DEFAULT_ENUMS,
)

# ─── FIXTURES ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_cache():
    """Reset singleton cache before and after every test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture()
def minimal_yaml(tmp_path: Path) -> Path:
    """Minimal valid akf.yaml with only schema_version."""
    p = tmp_path / "akf.yaml"
    p.write_text("schema_version: '1.0.0'\n", encoding="utf-8")
    return p


@pytest.fixture()
def full_yaml(tmp_path: Path) -> Path:
    """Full akf.yaml with custom taxonomy and enums."""
    content = textwrap.dedent("""\
        schema_version: "1.0.0"

        taxonomy:
          domains:
            - marine-engineering
            - nautical-navigation
            - vessel-maintenance

        enums:
          type:
            - concept
            - guide
            - sop
          level:
            - junior
            - senior
          status:
            - draft
            - active
            - retired
    """)
    p = tmp_path / "akf.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def partial_yaml(tmp_path: Path) -> Path:
    """akf.yaml with only custom domains, enums missing → should use defaults."""
    content = textwrap.dedent("""\
        schema_version: "1.0.0"
        taxonomy:
          domains:
            - custom-domain-a
            - custom-domain-b
    """)
    p = tmp_path / "akf.yaml"
    p.write_text(content, encoding="utf-8")
    return p


# ─── load_config: explicit path ───────────────────────────────────────────────


class TestLoadConfigExplicitPath:
    def test_loads_full_yaml(self, full_yaml: Path) -> None:
        cfg = load_config(path=full_yaml)
        assert cfg.domains == ["marine-engineering", "nautical-navigation", "vessel-maintenance"]
        assert cfg.enums.type == ["concept", "guide", "sop"]
        assert cfg.enums.level == ["junior", "senior"]
        assert cfg.enums.status == ["draft", "active", "retired"]
        assert cfg.schema_version == "1.0.0"
        assert cfg.source == full_yaml.resolve()

    def test_loads_minimal_yaml_falls_back_to_defaults(self, minimal_yaml: Path) -> None:
        cfg = load_config(path=minimal_yaml)
        assert cfg.domains == list(_DEFAULT_DOMAINS)
        assert cfg.enums.type == _DEFAULT_ENUMS["type"]
        assert cfg.enums.level == _DEFAULT_ENUMS["level"]
        assert cfg.enums.status == _DEFAULT_ENUMS["status"]

    def test_explicit_path_missing_raises_file_not_found(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.yaml"
        with pytest.raises(FileNotFoundError, match="does_not_exist.yaml"):
            load_config(path=missing)

    def test_accepts_string_path(self, full_yaml: Path) -> None:
        cfg = load_config(path=str(full_yaml))
        assert "marine-engineering" in cfg.domains

    def test_source_is_resolved_absolute(self, full_yaml: Path) -> None:
        cfg = load_config(path=full_yaml)
        assert cfg.source is not None
        assert cfg.source.is_absolute()


# ─── load_config: env var ─────────────────────────────────────────────────────


class TestLoadConfigEnvVar:
    def test_env_var_takes_precedence_over_cwd(
        self, full_yaml: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Put a different akf.yaml in CWD
        cwd_yaml = tmp_path / "cwd"
        cwd_yaml.mkdir()
        (cwd_yaml / "akf.yaml").write_text(
            "taxonomy:\n  domains:\n    - cwd-domain\n", encoding="utf-8"
        )
        monkeypatch.chdir(cwd_yaml)
        monkeypatch.setenv("AKF_CONFIG_PATH", str(full_yaml))

        cfg = load_config()
        # Should load from env var (full_yaml), not CWD
        assert "marine-engineering" in cfg.domains

    def test_env_var_missing_file_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AKF_CONFIG_PATH", str(tmp_path / "no_such.yaml"))
        with pytest.raises(FileNotFoundError):
            load_config()

    def test_env_var_cleared_uses_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        cwd_yaml = tmp_path / "vault"
        cwd_yaml.mkdir()
        (cwd_yaml / "akf.yaml").write_text(
            "taxonomy:\n  domains:\n    - vault-domain\n", encoding="utf-8"
        )
        monkeypatch.chdir(cwd_yaml)
        monkeypatch.delenv("AKF_CONFIG_PATH", raising=False)

        cfg = load_config()
        assert "vault-domain" in cfg.domains


# ─── load_config: CWD discovery ───────────────────────────────────────────────


class TestLoadConfigCWD:
    def test_discovers_akf_yaml_in_cwd(
        self, full_yaml: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(full_yaml.parent)
        monkeypatch.delenv("AKF_CONFIG_PATH", raising=False)
        cfg = load_config()
        assert "marine-engineering" in cfg.domains

    def test_no_akf_yaml_in_cwd_uses_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.chdir(empty_dir)
        monkeypatch.delenv("AKF_CONFIG_PATH", raising=False)

        cfg = load_config()
        # Should fall back to package defaults or built-in defaults
        assert cfg.domains  # non-empty
        assert "ai-system" in cfg.domains or cfg.source is None or "defaults" in str(cfg.source)


# ─── load_config: built-in defaults ──────────────────────────────────────────


class TestLoadConfigDefaults:
    def test_built_in_defaults_have_required_domains(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        empty = tmp_path / "empty2"
        empty.mkdir()
        monkeypatch.chdir(empty)
        monkeypatch.delenv("AKF_CONFIG_PATH", raising=False)

        cfg = load_config()
        for domain in ["ai-system", "api-design", "devops", "security"]:
            assert domain in cfg.domains, f"Expected default domain: {domain}"

    def test_built_in_defaults_have_required_enums(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        empty = tmp_path / "empty3"
        empty.mkdir()
        monkeypatch.chdir(empty)
        monkeypatch.delenv("AKF_CONFIG_PATH", raising=False)

        cfg = load_config()
        assert "beginner" in cfg.enums.level
        assert "active" in cfg.enums.status
        assert "concept" in cfg.enums.type


# ─── partial YAML fallback ────────────────────────────────────────────────────


class TestPartialYAMLFallback:
    def test_custom_domains_default_enums(self, partial_yaml: Path) -> None:
        cfg = load_config(path=partial_yaml)
        assert cfg.domains == ["custom-domain-a", "custom-domain-b"]
        # Enums should fall back to defaults
        assert cfg.enums.type == _DEFAULT_ENUMS["type"]
        assert cfg.enums.level == _DEFAULT_ENUMS["level"]
        assert cfg.enums.status == _DEFAULT_ENUMS["status"]

    def test_empty_domains_list_falls_back_to_defaults(self, tmp_path: Path) -> None:
        p = tmp_path / "akf.yaml"
        p.write_text("taxonomy:\n  domains: []\n", encoding="utf-8")
        cfg = load_config(path=p)
        assert cfg.domains == list(_DEFAULT_DOMAINS)

    def test_missing_taxonomy_section_uses_defaults(self, tmp_path: Path) -> None:
        p = tmp_path / "akf.yaml"
        p.write_text("schema_version: '1.0.0'\nenums:\n  type:\n    - concept\n", encoding="utf-8")
        cfg = load_config(path=p)
        assert cfg.domains == list(_DEFAULT_DOMAINS)
        assert cfg.enums.type == ["concept"]


# ─── invalid YAML ─────────────────────────────────────────────────────────────


class TestInvalidYAML:
    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "akf.yaml"
        p.write_text("taxonomy:\n  domains:\n    - valid\n  bad: [\n", encoding="utf-8")
        with pytest.raises(yaml.YAMLError):
            load_config(path=p)

    def test_non_list_domains_falls_back(self, tmp_path: Path) -> None:
        """If domains is a string (not list), fall back to defaults."""
        p = tmp_path / "akf.yaml"
        p.write_text("taxonomy:\n  domains: 'not-a-list'\n", encoding="utf-8")
        cfg = load_config(path=p)
        assert cfg.domains == list(_DEFAULT_DOMAINS)


# ─── AKFConfig helpers ────────────────────────────────────────────────────────


class TestAKFConfigHelpers:
    def test_is_valid_domain_true(self, full_yaml: Path) -> None:
        cfg = load_config(path=full_yaml)
        assert cfg.is_valid_domain("marine-engineering") is True

    def test_is_valid_domain_false(self, full_yaml: Path) -> None:
        cfg = load_config(path=full_yaml)
        assert cfg.is_valid_domain("ai-system") is False  # not in custom list

    def test_is_valid_enum_type(self, full_yaml: Path) -> None:
        cfg = load_config(path=full_yaml)
        assert cfg.is_valid_enum("type", "sop") is True
        assert cfg.is_valid_enum("type", "concept") is True
        assert cfg.is_valid_enum("type", "nonexistent") is False

    def test_is_valid_enum_unknown_field(self, full_yaml: Path) -> None:
        cfg = load_config(path=full_yaml)
        assert cfg.is_valid_enum("nonexistent_field", "anything") is False

    def test_all_domains_sorted(self, full_yaml: Path) -> None:
        cfg = load_config(path=full_yaml)
        result = cfg.all_domains()
        assert result == sorted(cfg.domains)

    def test_source_none_for_built_in_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        empty = tmp_path / "empty_src"
        empty.mkdir()
        monkeypatch.chdir(empty)
        monkeypatch.delenv("AKF_CONFIG_PATH", raising=False)

        cfg = load_config()
        # source is None only when no file found at all;
        # if package defaults file exists, source points to it
        if cfg.source is None:
            assert cfg.domains == list(_DEFAULT_DOMAINS)


# ─── get_config singleton ─────────────────────────────────────────────────────


class TestGetConfigSingleton:
    def test_returns_same_instance_on_second_call(self, full_yaml: Path) -> None:
        cfg1 = get_config(path=full_yaml)
        cfg2 = get_config()
        assert cfg1 is cfg2

    def test_reset_config_clears_cache(self, full_yaml: Path, minimal_yaml: Path) -> None:
        cfg1 = get_config(path=full_yaml)
        reset_config()
        cfg2 = get_config(path=minimal_yaml)
        assert cfg1 is not cfg2

    def test_get_config_without_path_uses_defaults_when_no_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        empty = tmp_path / "singleton_empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        monkeypatch.delenv("AKF_CONFIG_PATH", raising=False)

        cfg = get_config()
        assert cfg is not None
        assert isinstance(cfg, AKFConfig)

    def test_second_call_ignores_new_path_argument(
        self, full_yaml: Path, minimal_yaml: Path
    ) -> None:
        """Once cached, passing a different path has no effect."""
        cfg1 = get_config(path=full_yaml)
        cfg2 = get_config(path=minimal_yaml)  # should be ignored
        assert cfg1 is cfg2


# ─── schema_version ───────────────────────────────────────────────────────────


class TestSchemaVersion:
    def test_schema_version_parsed(self, tmp_path: Path) -> None:
        p = tmp_path / "akf.yaml"
        p.write_text("schema_version: '2.0.0'\n", encoding="utf-8")
        cfg = load_config(path=p)
        assert cfg.schema_version == "2.0.0"

    def test_schema_version_default_when_missing(self, tmp_path: Path) -> None:
        p = tmp_path / "akf.yaml"
        p.write_text("taxonomy:\n  domains:\n    - x\n", encoding="utf-8")
        cfg = load_config(path=p)
        assert cfg.schema_version == "1.0.0"


# ─── forward compatibility ────────────────────────────────────────────────────


class TestForwardCompatibility:
    def test_unknown_top_level_keys_ignored(self, tmp_path: Path) -> None:
        """Future akf.yaml keys must not break older versions."""
        content = textwrap.dedent("""\
            schema_version: "1.0.0"
            future_feature:
              some_key: some_value
            taxonomy:
              domains:
                - ai-system
        """)
        p = tmp_path / "akf.yaml"
        p.write_text(content, encoding="utf-8")
        cfg = load_config(path=p)
        assert cfg.domains == ["ai-system"]

    def test_unknown_enum_keys_ignored(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            schema_version: "1.0.0"
            enums:
              type:
                - concept
              future_enum:
                - x
                - y
        """)
        p = tmp_path / "akf.yaml"
        p.write_text(content, encoding="utf-8")
        cfg = load_config(path=p)
        assert cfg.enums.type == ["concept"]
