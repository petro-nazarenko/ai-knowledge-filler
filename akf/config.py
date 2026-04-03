"""
akf/config.py — AKF Config Loader (Phase 2.4 / CANON-DEFER-001)

Loads taxonomy and enum configuration from akf.yaml.
Falls back to built-in defaults if no config file is found.

Search order:
  1. Path from AKF_CONFIG_PATH env var
  2. ./akf.yaml (CWD — vault root)
  3. Package defaults (akf/defaults/akf.yaml)

Usage:
    from akf.config import get_config

    cfg = get_config()
    cfg.domains       # list[str]
    cfg.enums.type    # list[str]
    cfg.enums.level   # list[str]
    cfg.enums.status  # list[str]
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml

# ─── DEFAULT VALUES ────────────────────────────────────────────────────────────
# Canonical defaults — mirrored in akf/defaults/akf.yaml
# These are the single source of truth when no config file is found.

_DEFAULT_RELATIONSHIP_TYPES: list[str] = [
    "implements",
    "requires",
    "extends",
    "references",
    "supersedes",
    "part-of",
]

_DEFAULT_DOMAINS: list[str] = [
    "ai-system",
    "api-design",
    "backend-engineering",
    "business-strategy",
    "consulting",
    "data-engineering",
    "devops",
    "frontend-engineering",
    "machine-learning",
    "mobile-engineering",
    "ontology",
    "product-management",
    "project-management",
    "security",
    "system-design",
    "testing",
    "ux-design",
]

_DEFAULT_ENUMS: dict[str, list[str]] = {
    "type": [
        "concept",
        "guide",
        "reference",
        "checklist",
        "project",
        "roadmap",
        "template",
        "audit",
    ],
    "level": [
        "beginner",
        "intermediate",
        "advanced",
    ],
    "status": [
        "draft",
        "active",
        "completed",
        "archived",
    ],
}

# ─── DATA MODEL ───────────────────────────────────────────────────────────────


@dataclass
class AKFEnums:
    """Controlled vocabulary sets."""

    type: list[str] = field(default_factory=lambda: list(_DEFAULT_ENUMS["type"]))
    level: list[str] = field(default_factory=lambda: list(_DEFAULT_ENUMS["level"]))
    status: list[str] = field(default_factory=lambda: list(_DEFAULT_ENUMS["status"]))


@dataclass
class AKFConfig:
    """
    Resolved AKF configuration.

    Attributes:
        domains:             Valid values for the `domain` metadata field.
        enums:               Valid values for `type`, `level`, and `status` fields.
        relationship_types:  Valid typed relationship labels for the `related` field.
        schema_version:      Version of the akf.yaml schema used.
        source:              Path to the loaded config file, or None if using defaults.
    """

    domains: list[str] = field(default_factory=lambda: list(_DEFAULT_DOMAINS))
    enums: AKFEnums = field(default_factory=AKFEnums)
    relationship_types: list[str] = field(default_factory=lambda: list(_DEFAULT_RELATIONSHIP_TYPES))
    schema_version: str = "1.0.0"
    source: Optional[Path] = None

    def all_domains(self) -> list[str]:
        """Return sorted domain list."""
        return sorted(self.domains)

    def is_valid_domain(self, value: str) -> bool:
        return value in self.domains

    def is_valid_enum(self, field_name: str, value: str) -> bool:
        allowed = getattr(self.enums, field_name, None)
        if allowed is None:
            return False
        return value in allowed


# ─── LOADER ───────────────────────────────────────────────────────────────────

_DEFAULT_CONFIG_FILENAME = "akf.yaml"
_PACKAGE_DEFAULTS_PATH = Path(__file__).parent / "defaults" / "akf.yaml"


def _defaults() -> AKFConfig:
    """Return a config object populated entirely from built-in defaults."""
    return AKFConfig(
        domains=list(_DEFAULT_DOMAINS),
        enums=AKFEnums(
            type=list(_DEFAULT_ENUMS["type"]),
            level=list(_DEFAULT_ENUMS["level"]),
            status=list(_DEFAULT_ENUMS["status"]),
        ),
        relationship_types=list(_DEFAULT_RELATIONSHIP_TYPES),
        schema_version="1.0.0",
        source=None,
    )


def _parse_yaml(path: Path) -> AKFConfig:
    """
    Parse an akf.yaml file and return an AKFConfig.

    Unknown keys are ignored — forward-compatible.
    Missing sections fall back to defaults.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    schema_version = str(raw.get("schema_version", "1.0.0"))

    # ── taxonomy.domains ──────────────────────────────────────────────────────
    taxonomy = raw.get("taxonomy", {})
    domains_raw = taxonomy.get("domains", None)
    if isinstance(domains_raw, list) and domains_raw:
        domains = [str(d) for d in domains_raw]
    else:
        domains = list(_DEFAULT_DOMAINS)

    # ── enums ─────────────────────────────────────────────────────────────────
    enums_raw = raw.get("enums", {})

    def _enum(key: str) -> list[str]:
        val = enums_raw.get(key, None)
        if isinstance(val, list) and val:
            return [str(v) for v in val]
        return list(_DEFAULT_ENUMS[key])

    enums = AKFEnums(
        type=_enum("type"),
        level=_enum("level"),
        status=_enum("status"),
    )

    # ── relationship_types ────────────────────────────────────────────────────
    rel_types_raw = raw.get("relationship_types", None)
    if isinstance(rel_types_raw, list) and rel_types_raw:
        relationship_types = [str(r) for r in rel_types_raw]
    else:
        relationship_types = list(_DEFAULT_RELATIONSHIP_TYPES)

    return AKFConfig(
        domains=domains,
        enums=enums,
        relationship_types=relationship_types,
        schema_version=schema_version,
        source=path.resolve(),
    )


def load_config(path: Optional[Path | str] = None) -> AKFConfig:
    """
    Load AKF configuration.

    Search order:
      1. Explicit `path` argument
      2. AKF_CONFIG_PATH environment variable
      3. ./akf.yaml in current working directory
      4. Package defaults (akf/defaults/akf.yaml)
      5. Built-in Python defaults (no file required)

    Args:
        path: Optional explicit path to an akf.yaml file.

    Returns:
        AKFConfig populated from the first found source.

    Raises:
        FileNotFoundError: Only if an explicit path is given and doesn't exist.
        yaml.YAMLError: If the config file contains invalid YAML.
    """
    candidates: list[tuple[Path, bool]] = []  # (path, raise_if_missing)

    # 1. Explicit argument
    if path is not None:
        candidates.append((Path(path), True))

    # 2. Env var
    env_path = os.environ.get("AKF_CONFIG_PATH")
    if env_path:
        candidates.append((Path(env_path), True))

    # 3. CWD
    candidates.append((Path.cwd() / _DEFAULT_CONFIG_FILENAME, False))

    # 4. Package defaults file
    candidates.append((_PACKAGE_DEFAULTS_PATH, False))

    for candidate, raise_if_missing in candidates:
        if candidate.exists():
            return _parse_yaml(candidate)
        if raise_if_missing:
            raise FileNotFoundError(f"AKF config file not found: {candidate}")

    # 5. Built-in defaults — no file required
    return _defaults()


# ─── SINGLETON ────────────────────────────────────────────────────────────────
# Module-level singleton. Call reset_config() in tests to clear between cases.

_config_lock = threading.Lock()
_config_cache: Optional[AKFConfig] = None


def get_config(path: Optional[Path | str] = None) -> AKFConfig:
    """
    Return the cached AKF config, loading it on first call.

    Subsequent calls return the cached instance.
    Pass `path` only on the first call (or after reset_config()).

    Use reset_config() in tests to clear the cache.
    """
    global _config_cache
    if _config_cache is None:
        with _config_lock:
            if _config_cache is None:
                _config_cache = load_config(path)
    return _config_cache


def reset_config() -> None:
    """
    Clear the cached config. Use in tests between test cases.

    Example:
        def teardown_function():
            reset_config()
    """
    global _config_cache
    with _config_lock:
        _config_cache = None
