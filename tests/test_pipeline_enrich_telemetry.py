"""tests/test_pipeline_enrich_telemetry.py

Fix 6 — verify that TelemetryWriter.write() is called during Pipeline.enrich()
when telemetry_path is set (i.e. the writer is no longer always-None).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from akf.pipeline import Pipeline

NO_FRONTMATTER_FILE = """\
# A Document
Some content about AI systems.
"""

VALID_GENERATED_YAML = """\
title: Generated Title
type: guide
domain: ai-system
level: intermediate
status: active
tags:
  - ai
created: 2026-02-27
updated: 2026-02-27
"""


def _mock_cfg():
    cfg = MagicMock()
    cfg.domains = ["ai-system", "devops"]
    return cfg


@patch("akf.config.get_config", return_value=_mock_cfg())
@patch("akf.validator.validate", return_value=[])
@patch("llm_providers.get_provider")
@patch("akf.telemetry.TelemetryWriter.write")
def test_enrich_writes_telemetry_event(mock_write, mock_get_provider, _mv, _mc, tmp_path):
    """TelemetryWriter.write is called once for a file that needs enrichment."""
    provider = MagicMock()
    provider.model_name = "mock-model"
    provider.generate.return_value = VALID_GENERATED_YAML
    mock_get_provider.return_value = provider

    f = tmp_path / "doc.md"
    f.write_text(NO_FRONTMATTER_FILE, encoding="utf-8")

    telemetry_file = tmp_path / "telemetry" / "events.jsonl"
    pipeline = Pipeline(model="auto", telemetry_path=str(telemetry_file), verbose=False)

    result = pipeline.enrich(path=f)

    assert result.success is True
    mock_write.assert_called_once()
    event = mock_write.call_args[0][0]
    assert event.event_type == "enrich"
    assert event.skipped is False
