"""
Market Analysis Pipeline for AI Knowledge Filler.

Three-stage pipeline:
  Stage 1 — Market Analysis:    size, trends, segments, drivers
  Stage 2 — Competitor Analysis: key players, comparison, SWOT
  Stage 3 — Positioning:        gaps, USP, strategy (only when market request present)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


# ─── PROMPTS ──────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a senior market research analyst and business strategist.
Your task is to produce structured, data-driven Markdown documents with YAML frontmatter.

Every response MUST start with a YAML frontmatter block in exactly this format:
---
title: "<descriptive title>"
type: reference
domain: business-strategy
level: advanced
status: active
tags: [market-analysis]
created: {today}
updated: {today}
---

After the frontmatter, write a thorough Markdown document using ## headings.
Be specific, analytical, and actionable. Avoid vague generalisations.
"""

_MARKET_ANALYSIS_PROMPT = """\
Perform a comprehensive market analysis for the following request:

MARKET REQUEST: {request}

Your analysis MUST cover all of these sections:

## Market Overview
Brief description and scope of the market.

## Market Size & Growth
- Current market size (estimate with sources/reasoning)
- CAGR and growth forecast (3-5 years)
- Key growth drivers

## Market Segments
Table or list of main segments with size/share and growth rate.

## Customer Landscape
- Primary customer profiles / personas
- Main pain points and unmet needs
- Buying behaviour and decision criteria

## Technology & Innovation Trends
Current and emerging technologies shaping this market.

## Regulatory & Environmental Factors
Key regulations, compliance requirements, macro factors.

## Market Maturity
Is the market nascent, growing, mature, or declining? Reasoning.

## Summary & Key Takeaways
3-5 bullet points of the most important findings.
"""

_COMPETITOR_ANALYSIS_PROMPT = """\
Based on the market analysis below, perform a detailed competitor analysis.

MARKET REQUEST: {request}

MARKET CONTEXT:
{market_context}

Your competitor analysis MUST cover:

## Competitive Landscape Overview
High-level description of the competitive environment.

## Key Competitors
For each major competitor (aim for 4-6 players) provide:
- **Company name** — one-line description
- Target segment
- Core value proposition
- Pricing model (if known)
- Key strengths (2-3 bullets)
- Key weaknesses (2-3 bullets)
- Estimated market share or relative position

## Competitive Comparison Matrix
A Markdown table comparing competitors across 5-7 key dimensions
(e.g. pricing, features, geographic reach, integrations, support).

## Competitive Dynamics
- Who are the dominant players and why?
- Recent moves (M&A, product launches, pivots)
- Barriers to entry

## Whitespace / Gaps
What customer needs or segments are underserved by current competitors?

## Summary
Top 3 competitive insights most relevant to the market request.
"""

_POSITIONING_PROMPT = """\
Based on the market analysis and competitor analysis below, determine the optimal
market positioning strategy.

MARKET REQUEST: {request}

MARKET CONTEXT:
{market_context}

COMPETITOR CONTEXT:
{competitor_context}

Your positioning analysis MUST cover:

## Positioning Rationale
Why this positioning is optimal given the market and competitive landscape.

## Target Segment
Precise definition of the primary customer segment to target.

## Unique Selling Proposition (USP)
A single, compelling sentence that captures the differentiated value.

## Positioning Statement
Fill in: "For [target customer] who [pain point], [product/brand] is the [category]
that [key benefit] because [reason to believe]."

## Key Messaging Pillars
3-5 core messages that support the positioning.

## Differentiation Strategy
How to stand out from competitors across:
- Product / feature differentiation
- Pricing strategy
- Channel strategy
- Brand and communication

## Go-to-Market Implications
Top 3 tactical recommendations that flow from this positioning.

## Risks & Mitigations
2-3 risks to this positioning and how to mitigate them.

## Summary
One-paragraph positioning summary for executive communication.
"""


# ─── RESULT TYPES ─────────────────────────────────────────────────────────────


@dataclass
class StageResult:
    """Result of a single pipeline stage."""
    success: bool
    content: str
    file_path: Optional[Path] = None
    stage: str = ""
    duration_ms: int = 0
    error: str = ""
    validation_errors: list = field(default_factory=list)


@dataclass
class MarketPipelineResult:
    """Combined result of all three market analysis stages."""
    success: bool
    request: str
    market_analysis: StageResult = field(default_factory=lambda: StageResult(False, ""))
    competitor_analysis: StageResult = field(default_factory=lambda: StageResult(False, ""))
    positioning: StageResult = field(default_factory=lambda: StageResult(False, ""))
    total_duration_ms: int = 0
    output_dir: Optional[Path] = None

    @property
    def files(self) -> list[Path]:
        """All successfully written output files."""
        return [
            r.file_path
            for r in (self.market_analysis, self.competitor_analysis, self.positioning)
            if r.success and r.file_path
        ]

    def __repr__(self) -> str:
        stages_ok = sum(
            1 for r in (self.market_analysis, self.competitor_analysis, self.positioning)
            if r.success
        )
        return (
            f"MarketPipelineResult(success={self.success}, "
            f"stages_ok={stages_ok}/3, files={len(self.files)})"
        )


# ─── PIPELINE ─────────────────────────────────────────────────────────────────


class MarketAnalysisPipeline:
    """Three-stage AI-powered market analysis pipeline.

    Stages run sequentially; each stage feeds context into the next.

    Usage::

        pipeline = MarketAnalysisPipeline(output="./market-reports/")
        result = pipeline.analyze("B2B SaaS project management tools for SMEs")
        for f in result.files:
            print(f)
    """

    def __init__(
        self,
        output: str | Path = ".",
        model: str = "auto",
        verbose: bool = True,
    ) -> None:
        self.model = model
        self.verbose = verbose
        self.output_dir = Path(output).expanduser()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"->  {msg}")

    def _today(self) -> str:
        return date.today().isoformat()

    def _build_system_prompt(self) -> str:
        return _SYSTEM_PROMPT.format(today=self._today())

    def _safe_filename(self, stage: str, request: str) -> str:
        """Derive a filesystem-safe filename from the stage name + request."""
        import re
        slug = re.sub(r"[^\w\s-]", "", request)
        slug = re.sub(r"[\s-]+", "_", slug).strip("_")[:40].lower()
        return f"market_{stage}_{slug}.md"

    def _validate_content(self, content: str) -> None:
        """Validate content before writing; raise ValueError on blocking errors.

        This enforces the schema contract (E001–E007) so that files with
        validation violations cannot silently reach disk.
        """
        from akf.validator import validate
        from akf.validation_error import Severity

        errors = validate(content)
        blocking = [e for e in errors if e.severity == Severity.ERROR]
        if blocking:
            codes = ", ".join(e.code for e in blocking)
            raise ValueError(f"Market pipeline output failed validation: {codes}")

    def _write(self, content: str, filename: str) -> Path:
        """Write content to output_dir, avoiding overwrites."""
        from datetime import datetime
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # path traversal guard
        safe_name = Path(filename).name
        fp = self.output_dir / safe_name
        if fp.exists():
            ts = datetime.now().strftime("%H%M%S")
            fp = self.output_dir / f"{fp.stem}_{ts}.md"
        fp.write_text(content, encoding="utf-8")
        return fp

    def _call_llm(self, user_prompt: str) -> str:
        """Call the configured LLM provider."""
        from llm_providers import get_provider
        provider = get_provider(self.model)
        system = self._build_system_prompt()
        return provider.generate(user_prompt, system)

    # ── Stage methods ──────────────────────────────────────────────────────────

    def analyze_market(self, request: str) -> StageResult:
        """Stage 1 — market analysis (size, trends, segments, drivers)."""
        self._log(f"Stage 1/3 — Market Analysis: {request[:60]}...")
        t0 = time.monotonic()
        try:
            prompt = _MARKET_ANALYSIS_PROMPT.format(request=request)
            content = self._call_llm(prompt)
            self._validate_content(content)
            fp = self._write(content, self._safe_filename("analysis", request))
            duration_ms = int((time.monotonic() - t0) * 1000)
            self._log(f"  Saved: {fp.name} ({duration_ms} ms)")
            return StageResult(
                success=True, content=content, file_path=fp,
                stage="market_analysis", duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - t0) * 1000)
            self._log(f"  Stage 1 failed: {exc}")
            return StageResult(
                success=False, content="", stage="market_analysis",
                duration_ms=duration_ms, error=str(exc),
            )

    def analyze_competitors(
        self,
        request: str,
        market_context: str,
    ) -> StageResult:
        """Stage 2 — competitor comparison using Stage 1 context."""
        self._log("Stage 2/3 — Competitor Analysis...")
        t0 = time.monotonic()
        try:
            prompt = _COMPETITOR_ANALYSIS_PROMPT.format(
                request=request,
                market_context=market_context,
            )
            content = self._call_llm(prompt)
            self._validate_content(content)
            fp = self._write(content, self._safe_filename("competitors", request))
            duration_ms = int((time.monotonic() - t0) * 1000)
            self._log(f"  Saved: {fp.name} ({duration_ms} ms)")
            return StageResult(
                success=True, content=content, file_path=fp,
                stage="competitor_analysis", duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - t0) * 1000)
            self._log(f"  Stage 2 failed: {exc}")
            return StageResult(
                success=False, content="", stage="competitor_analysis",
                duration_ms=duration_ms, error=str(exc),
            )

    def determine_positioning(
        self,
        request: str,
        market_context: str,
        competitor_context: str,
    ) -> StageResult:
        """Stage 3 — positioning strategy using Stage 1 + 2 context.

        Only meaningful when a concrete market request is present.
        Requires both market_context and competitor_context to be non-empty.
        """
        self._log("Stage 3/3 — Positioning Determination...")
        if not market_context.strip():
            return StageResult(
                success=False, content="", stage="positioning",
                error="market_context is empty — run Stage 1 first",
            )
        if not competitor_context.strip():
            return StageResult(
                success=False, content="", stage="positioning",
                error="competitor_context is empty — run Stage 2 first",
            )

        t0 = time.monotonic()
        try:
            prompt = _POSITIONING_PROMPT.format(
                request=request,
                market_context=market_context,
                competitor_context=competitor_context,
            )
            content = self._call_llm(prompt)
            self._validate_content(content)
            fp = self._write(content, self._safe_filename("positioning", request))
            duration_ms = int((time.monotonic() - t0) * 1000)
            self._log(f"  Saved: {fp.name} ({duration_ms} ms)")
            return StageResult(
                success=True, content=content, file_path=fp,
                stage="positioning", duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - t0) * 1000)
            self._log(f"  Stage 3 failed: {exc}")
            return StageResult(
                success=False, content="", stage="positioning",
                duration_ms=duration_ms, error=str(exc),
            )

    # ── Full pipeline ──────────────────────────────────────────────────────────

    def analyze(self, request: str) -> MarketPipelineResult:
        """Run the full three-stage market analysis pipeline.

        Each stage feeds its output as context into the next stage.
        Stages 2 and 3 are skipped (with error recorded) if a prior stage fails.

        Args:
            request: Natural-language market request, e.g.
                     "B2B SaaS project management tools for SMEs".

        Returns:
            MarketPipelineResult with results for all three stages.
        """
        if not request or not request.strip():
            return MarketPipelineResult(
                success=False,
                request=request,
                market_analysis=StageResult(
                    False, "", stage="market_analysis",
                    error="market request must not be empty",
                ),
            )

        t_start = time.monotonic()
        self._log(f"Starting market analysis pipeline for: {request[:80]}")
        self._log(f"Output directory: {self.output_dir}")

        # Stage 1
        stage1 = self.analyze_market(request)

        # Stage 2 — requires Stage 1 content
        if stage1.success:
            stage2 = self.analyze_competitors(request, stage1.content)
        else:
            stage2 = StageResult(
                success=False, content="", stage="competitor_analysis",
                error="skipped — Stage 1 (market analysis) failed",
            )

        # Stage 3 — requires Stage 1 + 2 content
        if stage1.success and stage2.success:
            stage3 = self.determine_positioning(
                request, stage1.content, stage2.content
            )
        else:
            stage3 = StageResult(
                success=False, content="", stage="positioning",
                error="skipped — prior stage failed",
            )

        total_ms = int((time.monotonic() - t_start) * 1000)
        overall_success = stage1.success and stage2.success and stage3.success

        if overall_success:
            self._log(f"Pipeline complete — 3/3 stages succeeded ({total_ms} ms)")
        else:
            failed = [
                s.stage for s in (stage1, stage2, stage3) if not s.success
            ]
            self._log(f"Pipeline finished with failures: {failed}")

        return MarketPipelineResult(
            success=overall_success,
            request=request,
            market_analysis=stage1,
            competitor_analysis=stage2,
            positioning=stage3,
            total_duration_ms=total_ms,
            output_dir=self.output_dir,
        )
