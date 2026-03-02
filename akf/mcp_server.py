"""
akf/mcp_server.py — AKF MCP Server (v0.6.0)

Four MCP tools: akf_generate, akf_validate, akf_enrich, akf_batch
Start via: akf serve --mcp
"""

from __future__ import annotations

from pathlib import Path

# Top-level imports so unittest.mock.patch can find them by name
from akf.pipeline import Pipeline
from akf.validator import validate


# ─── akf_generate ────────────────────────────────────────────────────────────


def akf_generate(
    prompt: str,
    output: str = "./vault",
    domain: str | None = None,
    type: str | None = None,
    model: str = "auto",
) -> dict:
    """Generate a validated Markdown knowledge file via the AKF pipeline."""
    pipeline = Pipeline(output=output)
    hints: dict[str, str] = {}
    if domain:
        hints["domain"] = domain
    if type:
        hints["type"] = type

    result = pipeline.generate(prompt, model=model, hints=hints)

    return {
        "success": result.success,
        "file_path": str(result.file_path) if result.file_path else None,
        "attempts": result.attempts,
        "generation_id": result.generation_id,
        "errors": [str(e) for e in result.errors],
    }


# ─── akf_validate ────────────────────────────────────────────────────────────


def akf_validate(path: str, strict: bool = False) -> dict:
    """Validate YAML frontmatter of a Markdown file or all .md files in a directory."""
    from akf.validation_error import Severity

    p = Path(path)

    if p.is_file():
        all_errors = validate(p.read_text(encoding="utf-8"))
        if strict:
            errors = [str(e) for e in all_errors]
        else:
            errors = [str(e) for e in all_errors if e.severity == Severity.ERROR]
        return {"is_valid": len(errors) == 0, "errors": errors}

    if p.is_dir():
        results: list[dict] = []
        for f in sorted(p.rglob("*.md")):
            all_errors = validate(f.read_text(encoding="utf-8"))
            if strict:
                errors = [str(e) for e in all_errors]
            else:
                errors = [str(e) for e in all_errors if e.severity == Severity.ERROR]
            results.append({"file": str(f), "is_valid": len(errors) == 0, "errors": errors})
        total = len(results)
        ok = sum(1 for r in results if r["is_valid"])
        return {"total": total, "ok": ok, "failed": total - ok, "results": results}

    return {"error": f"Path not found: {path}"}


# ─── akf_enrich ──────────────────────────────────────────────────────────────


def akf_enrich(
    path: str,
    force: bool = False,
    dry_run: bool = False,
    model: str = "auto",
) -> dict:
    """Add or update YAML frontmatter on existing Markdown files."""
    from akf.pipeline import EnrichResult

    target = Path(path)
    pipeline = Pipeline(model=model)

    if target.is_file():
        md_files = [target]
    elif target.is_dir():
        md_files = sorted(target.rglob("*.md"))
    else:
        return {"error": f"Path not found: {path}"}

    raw_results: list[EnrichResult] = []
    for f in md_files:
        try:
            r = pipeline.enrich(path=f, force=force, dry_run=dry_run, model=model)
        except Exception as exc:
            r = EnrichResult(success=False, path=f, status="failed", skip_reason=str(exc))
        raw_results.append(r)

    return {
        "total": len(raw_results),
        "enriched": sum(1 for r in raw_results if r.status == "enriched"),
        "skipped": sum(1 for r in raw_results if r.status == "skipped"),
        "failed": sum(1 for r in raw_results if r.status == "failed"),
        "results": [{"file": str(r.path), "status": r.status} for r in raw_results],
    }


# ─── akf_batch ───────────────────────────────────────────────────────────────


def akf_batch(
    plan: list,
    output: str = "./vault",
    model: str = "auto",
) -> dict:
    """Generate multiple validated knowledge files from a structured plan."""
    if not plan:
        return {"total": 0, "ok": 0, "failed": 0, "results": []}

    pipeline = Pipeline(output=output)
    results = pipeline.batch_generate(plan, output=output, model=model)

    ok = sum(1 for r in results if r.success)
    return {
        "total": len(results),
        "ok": ok,
        "failed": len(results) - ok,
        "results": [
            {
                "prompt": str(plan[i].get("prompt", ""))[:50],
                "success": r.success,
                "file_path": str(r.file_path) if r.file_path else None,
                "attempts": r.attempts,
            }
            for i, r in enumerate(results)
        ],
    }


# ─── entry point ─────────────────────────────────────────────────────────────


def run() -> None:
    """Start the MCP server. Called from cli.py via: akf serve --mcp"""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise ImportError(
            "mcp package not installed. Run: pip install ai-knowledge-filler[mcp]"
        ) from exc

    mcp = FastMCP("akf")
    mcp.tool()(akf_generate)
    mcp.tool()(akf_validate)
    mcp.tool()(akf_enrich)
    mcp.tool()(akf_batch)
    mcp.run()
