"""tests/test_market_pipeline_domain.py

Fix 7 — verify that MarketAnalysisPipeline._build_system_prompt() loads
domain taxonomy from akf.yaml config instead of hardcoding business-strategy.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from akf.market_pipeline import MarketAnalysisPipeline


def _mock_cfg(domains):
    cfg = MagicMock()
    cfg.domains = domains
    return cfg


def test_system_prompt_contains_config_domains(tmp_path):
    """_build_system_prompt injects domains from get_config(), not hardcoded values."""
    custom_domains = ["fintech", "healthtech", "edtech"]
    pipeline = MarketAnalysisPipeline(output=str(tmp_path), model="auto", verbose=False)

    with patch("akf.config.get_config", return_value=_mock_cfg(custom_domains)):
        prompt = pipeline._build_system_prompt()

    for domain in custom_domains:
        assert domain in prompt, f"Expected domain {domain!r} in system prompt"
