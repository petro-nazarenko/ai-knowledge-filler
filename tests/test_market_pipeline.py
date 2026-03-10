"""Tests for MarketAnalysisPipeline (akf/market_pipeline.py).

Covers:
  - StageResult and MarketPipelineResult dataclasses
  - analyze_market() — happy path and LLM failure
  - analyze_competitors() — happy path, empty context guard
  - determine_positioning() — happy path, empty context guards
  - analyze() — full pipeline success
  - analyze() — stage cascade: Stage 1 failure skips 2 and 3
  - analyze() — stage cascade: Stage 2 failure skips 3
  - analyze() — empty request guard
  - File writing: safe filename generation, output directory creation
  - MarketPipelineResult.files property
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from akf.market_pipeline import (
    MarketAnalysisPipeline,
    MarketPipelineResult,
    StageResult,
    _COMPETITOR_ANALYSIS_PROMPT,
    _MARKET_ANALYSIS_PROMPT,
    _POSITIONING_PROMPT,
)


# ─── FIXTURES ─────────────────────────────────────────────────────────────────

SAMPLE_REQUEST = "B2B SaaS project management tools for SMEs"

SAMPLE_MARKET_CONTENT = """\
---
title: "Market Analysis — B2B SaaS Project Management"
type: reference
domain: business-strategy
level: advanced
status: active
tags: [market-analysis]
created: 2026-03-10
updated: 2026-03-10
---

## Market Overview
This is a sample market analysis document.

## Market Size & Growth
The market is worth $6B and growing at 12% CAGR.
"""

SAMPLE_COMPETITOR_CONTENT = """\
---
title: "Competitor Analysis — B2B SaaS Project Management"
type: reference
domain: business-strategy
level: advanced
status: active
tags: [market-analysis]
created: 2026-03-10
updated: 2026-03-10
---

## Competitive Landscape Overview
Three dominant players control 60% of the market.

## Key Competitors
- **Asana** — leading platform
- **Monday.com** — visual PM tool
"""

SAMPLE_POSITIONING_CONTENT = """\
---
title: "Positioning — B2B SaaS Project Management"
type: reference
domain: business-strategy
level: advanced
status: active
tags: [market-analysis]
created: 2026-03-10
updated: 2026-03-10
---

## Positioning Rationale
Target underserved SME segment with focus on simplicity.

## Unique Selling Proposition (USP)
The simplest PM tool that grows with your team.
"""


def _make_pipeline(tmp_path: Path) -> MarketAnalysisPipeline:
    return MarketAnalysisPipeline(
        output=str(tmp_path),
        model="auto",
        verbose=False,
    )


def _mock_provider(content: str) -> MagicMock:
    provider = MagicMock()
    provider.generate.return_value = content
    return provider


# ─── StageResult ──────────────────────────────────────────────────────────────


class TestStageResult:
    def test_success_defaults(self):
        r = StageResult(success=True, content="hello", stage="market_analysis")
        assert r.success is True
        assert r.content == "hello"
        assert r.file_path is None
        assert r.error == ""

    def test_failure_defaults(self):
        r = StageResult(success=False, content="", error="boom")
        assert r.success is False
        assert r.error == "boom"


# ─── MarketPipelineResult ─────────────────────────────────────────────────────


class TestMarketPipelineResult:
    def _make(self, s1_ok=True, s2_ok=True, s3_ok=True) -> MarketPipelineResult:
        def _stage(ok, name, path=None):
            return StageResult(
                success=ok, content="x", stage=name,
                file_path=Path(path) if (ok and path) else None,
            )

        return MarketPipelineResult(
            success=s1_ok and s2_ok and s3_ok,
            request=SAMPLE_REQUEST,
            market_analysis=_stage(s1_ok, "market_analysis", "/tmp/s1.md"),
            competitor_analysis=_stage(s2_ok, "competitor_analysis", "/tmp/s2.md"),
            positioning=_stage(s3_ok, "positioning", "/tmp/s3.md"),
        )

    def test_files_all_success(self):
        result = self._make()
        assert len(result.files) == 3

    def test_files_partial_success(self):
        result = self._make(s3_ok=False)
        assert len(result.files) == 2

    def test_files_all_failure(self):
        result = self._make(s1_ok=False, s2_ok=False, s3_ok=False)
        assert result.files == []

    def test_repr(self):
        result = self._make()
        assert "MarketPipelineResult" in repr(result)
        assert "stages_ok=3" in repr(result)

    def test_repr_partial(self):
        result = self._make(s3_ok=False)
        assert "stages_ok=2" in repr(result)


# ─── analyze_market ───────────────────────────────────────────────────────────


class TestAnalyzeMarket:
    def test_success_writes_file(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.return_value = SAMPLE_MARKET_CONTENT
            result = pipeline.analyze_market(SAMPLE_REQUEST)

        assert result.success is True
        assert result.stage == "market_analysis"
        assert result.file_path is not None
        assert result.file_path.exists()
        assert result.duration_ms >= 0
        assert result.error == ""

    def test_file_contains_llm_output(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.return_value = SAMPLE_MARKET_CONTENT
            result = pipeline.analyze_market(SAMPLE_REQUEST)

        assert result.file_path.read_text(encoding="utf-8") == SAMPLE_MARKET_CONTENT

    def test_llm_failure_returns_failed_stage(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.side_effect = RuntimeError("provider error")
            result = pipeline.analyze_market(SAMPLE_REQUEST)

        assert result.success is False
        assert result.file_path is None
        assert "provider error" in result.error

    def test_prompt_contains_request(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.return_value = SAMPLE_MARKET_CONTENT
            pipeline.analyze_market("unique-market-xyz-123")

        call_args = mock_llm.call_args[0][0]
        assert "unique-market-xyz-123" in call_args


# ─── analyze_competitors ──────────────────────────────────────────────────────


class TestAnalyzeCompetitors:
    def test_success_writes_file(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.return_value = SAMPLE_COMPETITOR_CONTENT
            result = pipeline.analyze_competitors(
                SAMPLE_REQUEST, SAMPLE_MARKET_CONTENT
            )

        assert result.success is True
        assert result.stage == "competitor_analysis"
        assert result.file_path is not None
        assert result.file_path.exists()

    def test_prompt_includes_market_context(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.return_value = SAMPLE_COMPETITOR_CONTENT
            pipeline.analyze_competitors(SAMPLE_REQUEST, SAMPLE_MARKET_CONTENT)

        call_args = mock_llm.call_args[0][0]
        assert "Market Analysis" in call_args  # market context is included

    def test_llm_failure(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.side_effect = RuntimeError("timeout")
            result = pipeline.analyze_competitors(SAMPLE_REQUEST, SAMPLE_MARKET_CONTENT)

        assert result.success is False
        assert "timeout" in result.error


# ─── determine_positioning ────────────────────────────────────────────────────


class TestDeterminePositioning:
    def test_success_writes_file(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.return_value = SAMPLE_POSITIONING_CONTENT
            result = pipeline.determine_positioning(
                SAMPLE_REQUEST, SAMPLE_MARKET_CONTENT, SAMPLE_COMPETITOR_CONTENT
            )

        assert result.success is True
        assert result.stage == "positioning"
        assert result.file_path is not None

    def test_empty_market_context_fails(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        result = pipeline.determine_positioning(SAMPLE_REQUEST, "", SAMPLE_COMPETITOR_CONTENT)

        assert result.success is False
        assert "market_context" in result.error

    def test_empty_competitor_context_fails(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        result = pipeline.determine_positioning(
            SAMPLE_REQUEST, SAMPLE_MARKET_CONTENT, ""
        )

        assert result.success is False
        assert "competitor_context" in result.error

    def test_whitespace_only_market_context_fails(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        result = pipeline.determine_positioning(SAMPLE_REQUEST, "   ", SAMPLE_COMPETITOR_CONTENT)

        assert result.success is False

    def test_prompt_includes_both_contexts(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.return_value = SAMPLE_POSITIONING_CONTENT
            pipeline.determine_positioning(
                SAMPLE_REQUEST, SAMPLE_MARKET_CONTENT, SAMPLE_COMPETITOR_CONTENT
            )

        call_args = mock_llm.call_args[0][0]
        assert SAMPLE_REQUEST in call_args
        assert "Market Overview" in call_args          # from market context
        assert "Competitive Landscape" in call_args    # from competitor context


# ─── analyze() — full pipeline ────────────────────────────────────────────────


class TestAnalyzeFullPipeline:
    def _patch_all_stages(self, mock_llm):
        """Configure mock_llm to return correct content per call order."""
        mock_llm.side_effect = [
            SAMPLE_MARKET_CONTENT,
            SAMPLE_COMPETITOR_CONTENT,
            SAMPLE_POSITIONING_CONTENT,
        ]

    def test_full_pipeline_success(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            self._patch_all_stages(mock_llm)
            result = pipeline.analyze(SAMPLE_REQUEST)

        assert result.success is True
        assert result.market_analysis.success is True
        assert result.competitor_analysis.success is True
        assert result.positioning.success is True
        assert len(result.files) == 3
        assert result.total_duration_ms >= 0
        assert result.output_dir == tmp_path

    def test_three_files_written_to_output_dir(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            self._patch_all_stages(mock_llm)
            result = pipeline.analyze(SAMPLE_REQUEST)

        for fp in result.files:
            assert fp.parent == tmp_path
            assert fp.suffix == ".md"

    def test_stage1_failure_skips_stages_2_and_3(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.side_effect = RuntimeError("llm unavailable")
            result = pipeline.analyze(SAMPLE_REQUEST)

        assert result.success is False
        assert result.market_analysis.success is False
        assert result.competitor_analysis.success is False
        assert "Stage 1" in result.competitor_analysis.error or "prior" in result.competitor_analysis.error or "skipped" in result.competitor_analysis.error
        assert result.positioning.success is False
        assert len(result.files) == 0
        # LLM called only once (Stage 1 fails, no further calls)
        assert mock_llm.call_count == 1

    def test_stage2_failure_skips_stage3(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.side_effect = [
                SAMPLE_MARKET_CONTENT,  # Stage 1 succeeds
                RuntimeError("competitor llm error"),  # Stage 2 fails
            ]
            result = pipeline.analyze(SAMPLE_REQUEST)

        assert result.success is False
        assert result.market_analysis.success is True
        assert result.competitor_analysis.success is False
        assert result.positioning.success is False
        assert "prior" in result.positioning.error or "skipped" in result.positioning.error
        assert len(result.files) == 1  # only Stage 1 file

    def test_empty_request_returns_error(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        result = pipeline.analyze("")

        assert result.success is False
        assert result.market_analysis.success is False
        assert "empty" in result.market_analysis.error

    def test_whitespace_request_returns_error(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        result = pipeline.analyze("   ")

        assert result.success is False

    def test_output_dir_created_if_missing(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "output"
        pipeline = MarketAnalysisPipeline(output=str(nested), model="auto", verbose=False)
        with patch("akf.market_pipeline.MarketAnalysisPipeline._call_llm") as mock_llm:
            mock_llm.side_effect = [
                SAMPLE_MARKET_CONTENT,
                SAMPLE_COMPETITOR_CONTENT,
                SAMPLE_POSITIONING_CONTENT,
            ]
            result = pipeline.analyze(SAMPLE_REQUEST)

        assert nested.exists()
        assert result.success is True


# ─── _safe_filename ───────────────────────────────────────────────────────────


class TestSafeFilename:
    def test_returns_md_extension(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        name = pipeline._safe_filename("analysis", SAMPLE_REQUEST)
        assert name.endswith(".md")

    def test_no_special_chars(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        name = pipeline._safe_filename("analysis", "市场分析 — B2B! SaaS?")
        # Should only contain safe chars
        import re
        assert re.match(r"^[\w.\-_]+$", name)

    def test_includes_stage_prefix(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        name = pipeline._safe_filename("competitors", SAMPLE_REQUEST)
        assert name.startswith("market_competitors_")

    def test_long_request_truncated(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        long_request = "a" * 200
        name = pipeline._safe_filename("analysis", long_request)
        # slug is truncated at 40 chars, total filename should be manageable
        assert len(name) < 100


# ─── _write (path traversal guard) ───────────────────────────────────────────


class TestWrite:
    def test_avoids_overwrite_with_timestamp(self, tmp_path):
        pipeline = _make_pipeline(tmp_path)
        # Write same filename twice
        pipeline._write("content1", "test_file.md")
        pipeline._write("content2", "test_file.md")
        files = list(tmp_path.glob("test_file*.md"))
        assert len(files) == 2

    def test_path_traversal_blocked(self, tmp_path):
        """Filenames with path traversal components must not escape output_dir."""
        pipeline = _make_pipeline(tmp_path)
        # _write uses Path(filename).name — traversal component stripped
        fp = pipeline._write("safe content", "../../evil.md")
        assert fp.parent == tmp_path
        assert fp.name == "evil.md"
