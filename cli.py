#!/usr/bin/env python3
"""
AKF CLI — AI Knowledge Filler (Multi-LLM Edition)
"""

import sys
import os
import re
import argparse
import time
from datetime import datetime
from pathlib import Path

# BUG-1: When cli.py is run as a script from the repo directory, Python prepends
# the script's parent directory to sys.path[0], causing the local akf/ package
# directory to shadow the installed package. Moving it to the end ensures the
# installed package is resolved first while still allowing llm_providers, etc.
# to be found from the same directory.
_here = str(Path(__file__).parent.absolute())
if sys.path and sys.path[0] == _here:
    sys.path.append(sys.path.pop(0))

from llm_providers import get_provider, list_providers, PROVIDERS

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.absolute()
OUTPUT_DIR = Path(os.getenv("AKF_OUTPUT_DIR", "."))
SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"

# Telemetry writer path (repo, not vault — ADR-001 Decision 9)
TELEMETRY_PATH = Path(os.getenv("AKF_TELEMETRY_PATH", "telemetry/events.jsonl"))


CLI_EXCLUDE_PATTERNS = [
    ".github",
    "README.md",
    "08-TEMPLATES",  # Obsidian Templater files — not knowledge documents
]

# ─── COLORS ───────────────────────────────────────────────────────────────────

GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


def ok(msg: str) -> None:
    print(f"{GREEN}✅ {msg}{NC}")


def info(msg: str) -> None:
    print(f"{BLUE}→  {msg}{NC}")


def warn(msg: str) -> None:
    print(f"{YELLOW}⚠  {msg}{NC}")


def err(msg: str) -> None:
    print(f"{RED}❌ {msg}{NC}")


# ─── VALIDATE ─────────────────────────────────────────────────────────────────

from akf.validator import validate as _akf_validate
from akf.validation_error import Severity


def _validate_file_impl(filepath: str, strict: bool = False) -> tuple[list[str], list[str]]:
    """Adapter: wraps akf.validator.validate() to match cli expected signature."""
    with open(filepath, encoding="utf-8") as _f:
        content = _f.read()
    all_errors = _akf_validate(content)
    if strict:
        error_msgs = [str(e) for e in all_errors]
        warning_msgs: list[str] = []
    else:
        error_msgs = [str(e) for e in all_errors if e.severity == Severity.ERROR]
        warning_msgs = [str(e) for e in all_errors if e.severity == Severity.WARNING]
    return error_msgs, warning_msgs


def validate_file(filepath: str, strict: bool = False) -> tuple[list[str], list[str]]:
    """Validate a Markdown file using akf.validator (full E001-E007 enforcement)."""
    return _validate_file_impl(filepath, strict=strict)


def cmd_validate(args: argparse.Namespace) -> None:
    import glob

    # Resolve file list
    if args.file:
        files = [args.file]
    elif args.path:
        base = Path(args.path)
        files = [str(p) for p in base.rglob("*.md")]
    else:
        files = glob.glob("**/*.md", recursive=True)

    files = [f for f in files if not any(x in f for x in CLI_EXCLUDE_PATTERNS)]

    strict = getattr(args, "strict", False)
    mode = " [STRICT]" if strict else ""
    info(f"Checking {len(files)} files{mode}...")

    total = valid = warned = failed = 0
    for filepath in sorted(files):
        total += 1
        errors, warnings = validate_file(filepath, strict=strict)
        rel = filepath
        if errors:
            failed += 1
            print(f"{RED}❌ {rel}{NC}")
            for e in errors:
                print(f"   {RED}{e}{NC}")
        elif warnings:
            warned += 1
            print(f"{YELLOW}⚠  {rel}{NC}")
            for w in warnings:
                print(f"   {YELLOW}{w}{NC}")
        else:
            valid += 1
            print(f"{GREEN}✅ {rel}{NC}")

    print()
    info(f"Total: {total} | OK: {valid} | Warnings: {warned} | Errors: {failed}")
    if failed > 0:
        sys.exit(1)


# ─── INIT ─────────────────────────────────────────────────────────────────────


def cmd_init(args: argparse.Namespace) -> None:
    """
    Generate akf.yaml in the target directory.

    Copies the bundled default config to the vault root (or --path).
    If akf.yaml already exists, aborts unless --force is passed.
    """
    import shutil

    target_dir = Path(args.path) if args.path else Path.cwd()
    target = target_dir / "akf.yaml"

    # Find bundled default
    try:
        import akf

        default_config = Path(akf.__file__).parent / "defaults" / "akf.yaml"
    except Exception:
        default_config = Path(__file__).parent / "akf" / "defaults" / "akf.yaml"

    if not default_config.exists():
        err(f"Bundled default config not found: {default_config}")
        sys.exit(1)

    if target.exists() and not args.force:
        warn(f"akf.yaml already exists: {target}")
        warn("Use --force to overwrite.")
        sys.exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)
    if target.exists() and args.force:
        backup = target.with_suffix(".yaml.bak")
        shutil.copy(target, backup)
        warn(f"Backup created: {backup}")
    shutil.copy(default_config, target)
    ok(f"Created: {target}")
    info("")
    info("Next steps:")
    info("  1. Edit akf.yaml — set vault_path and add your domains under taxonomy.domains")
    info("  2. Set your LLM API key:")
    info("       export ANTHROPIC_API_KEY='sk-ant-...'   # Claude (recommended)")
    info("       export GOOGLE_API_KEY='AIza...'         # Gemini")
    info("       export OPENAI_API_KEY='sk-...'          # GPT-4")
    info("       export GROQ_API_KEY='gsk_...'           # Groq (fast + free tier)")
    info("       # or run Ollama locally — no key needed")
    info("  3. Generate your first file:")
    info('       akf generate "Create a concept about [topic] for the [domain] domain"')
    info("")
    info("Docs: https://github.com/petrnzrnk-creator/ai-knowledge-filler")


# ─── GENERATE ─────────────────────────────────────────────────────────────────


def _cmd_generate_batch(args: argparse.Namespace) -> None:
    """Execute batch generation from a JSON plan file.

    Each plan item may have: prompt (required), domain, type.
    Exits 0 if all succeed, 1 if any fail.
    """
    import json
    from akf.pipeline import Pipeline

    batch_path = Path(args.batch)
    if not batch_path.exists():
        err(f"Batch file not found: {batch_path}")
        sys.exit(1)

    try:
        raw = batch_path.read_text(encoding="utf-8")
        plan = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as e:
        err(f"Invalid JSON in batch file: {e}")
        sys.exit(1)

    if not isinstance(plan, list):
        err("Batch file must contain a JSON array.")
        sys.exit(1)

    if len(plan) == 0:
        info("Batch plan is empty — nothing to generate.")
        print()
        info("Total: 0 | OK: 0 | Failed: 0")
        sys.exit(0)

    out_dir = Path(args.output) if getattr(args, "output", None) else OUTPUT_DIR
    model = getattr(args, "model", "auto") or "auto"

    rag_enabled = not bool(getattr(args, "no_rag", False))
    pipeline = Pipeline(
        output=str(out_dir),
        model=model,
        telemetry_path=TELEMETRY_PATH,
        verbose=False,
        rag_enabled=rag_enabled,
    )

    info(f"Running batch of {len(plan)} item(s) via {model}...")
    print()

    results = pipeline.batch_generate(plan, output=str(out_dir), model=model)

    ok_count = 0
    fail_count = 0
    for item, result in zip(plan, results):
        prompt_text = item.get("prompt", str(item)) if isinstance(item, dict) else str(item)
        filename = Path(result.file_path).name if result.file_path else prompt_text[:40]
        attempts = result.attempts or 1
        attempt_label = f"{attempts} attempt{'s' if attempts != 1 else ''}"
        if result.success:
            ok_count += 1
            print(f"{GREEN}→ {filename} ✅ ({attempt_label}){NC}")
        else:
            fail_count += 1
            print(f"{RED}→ {filename} ❌ ({attempt_label}, failed){NC}")

    print()
    info(f"Total: {len(plan)} | OK: {ok_count} | Failed: {fail_count}")
    sys.exit(0 if fail_count == 0 else 1)


def load_system_prompt() -> str:
    """Load system prompt exclusively from installed package.

    Raises a clear error if not found — no CWD fallback to avoid
    accidentally picking up repo's system_prompt.md when running
    from the repo directory.
    """
    try:
        import akf

        pkg_path = Path(akf.__file__).parent / "system_prompt.md"
        info(f"[system_prompt] Loading from: {pkg_path}")
        if pkg_path.exists():
            return pkg_path.read_text(encoding="utf-8")
        err(f"system_prompt.md not found in installed package: {pkg_path}")
    except ImportError:
        err("akf package not found. Install with: pip install ai-knowledge-filler")
    sys.exit(1)


def extract_filename(content: str, prompt: str) -> str:
    match = re.search(r'title:\s*["\']?(.+?)["\']?\s*\n', content)
    if match:
        title = match.group(1).strip().strip("\"'")
        name = re.sub(r"[\s-]+", "_", re.sub(r"[^\w\s-]", "", title))
        return f"{name}.md"
    return "_".join(re.sub(r"[^\w\s]", "", prompt).split()[:4]).lower() + ".md"


_WINDOWS_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)", re.IGNORECASE)


def sanitize_filename(filename: str, output_dir: Path) -> Path:
    """Prevent path traversal (SEC-M2) and Windows reserved names (SEC-L3)."""
    safe_name = Path(filename).name
    if not safe_name.endswith(".md"):
        safe_name = safe_name + ".md"
    stem = Path(safe_name).stem
    if _WINDOWS_RESERVED.match(stem):
        raise ValueError(f"Windows reserved filename not allowed: {filename!r}")
    resolved = (output_dir / safe_name).resolve()
    if not resolved.is_relative_to(output_dir.resolve()):
        raise ValueError(f"Path traversal detected: {filename!r}")
    return resolved


def save_file(content: str, filename: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = sanitize_filename(filename, output_dir)
    if filepath.exists():
        ts = datetime.now().strftime("%H%M%S")
        filepath = output_dir / f"{filepath.stem}_{ts}.md"
    filepath.write_text(content, encoding="utf-8")
    return filepath


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate knowledge file using selected LLM provider.

    Pipeline (Phase 2.3):
      1. Generate initial content via LLM
      2. Validate → run_retry_loop if errors
      3. commit() → atomic write
      4. Telemetry emitted by RetryController + CommitGate automatically
    """
    # ── Batch mode ────────────────────────────────────────────────────────────
    if getattr(args, "batch", None):
        _cmd_generate_batch(args)
        return

    if not args.prompt:
        err("prompt is required (or use --batch <plan.json>)")
        sys.exit(1)

    from akf.telemetry import TelemetryWriter, new_generation_id
    from akf.retry_controller import run_retry_loop
    from akf.commit_gate import commit as akf_commit
    from akf.validator import validate

    # Get provider
    try:
        provider = get_provider(args.model)
    except ValueError as e:
        err(str(e))
        sys.exit(1)
    except Exception as e:
        # Catch ProviderUnavailableError (and subclasses) without hard import
        if "ProviderUnavailableError" in type(e).__name__ or "unavailable" in str(e).lower():
            err("No LLM provider available.")
            info("Set one of these environment variables and retry:")
            info("  export ANTHROPIC_API_KEY='sk-ant-...'")
            info("  export GOOGLE_API_KEY='AIza...'")
            info("  export OPENAI_API_KEY='sk-...'")
            info("  export GROQ_API_KEY='gsk_...'")
            info("Or run Ollama locally (no key needed): https://ollama.com")
        else:
            err(f"Provider error: {e}")
        sys.exit(1)

    system_prompt = load_system_prompt()
    info(f"Generating via {provider.display_name}...")

    # ── Telemetry setup ───────────────────────────────────────────────────────
    generation_id = new_generation_id()
    writer = TelemetryWriter(path=TELEMETRY_PATH)
    t_start = time.monotonic()

    # ── Initial generation ────────────────────────────────────────────────────
    from akf.pipeline import _strip_yaml_codeblock, _patch_dates

    try:
        t0 = time.monotonic()
        content = provider.generate(args.prompt, system_prompt)
        initial_duration_ms = int((time.monotonic() - t0) * 1000)
    except Exception as e:
        err(f"Generation error: {e}")
        sys.exit(1)

    content = _strip_yaml_codeblock(content)
    content = _patch_dates(content, datetime.now().strftime("%Y-%m-%d"))

    # ── Determine output path ─────────────────────────────────────────────────
    out_dir = Path(args.output) if args.output else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = extract_filename(content, args.prompt)
    output_path = sanitize_filename(filename, out_dir)
    if output_path.exists():
        ts = datetime.now().strftime("%H%M%S")
        output_path = out_dir / f"{output_path.stem}_{ts}.md"

    document_id = output_path.stem

    # ── Initial validation ────────────────────────────────────────────────────
    try:
        initial_errors = validate(content)
    except Exception:
        initial_errors = []

    blocking = [e for e in initial_errors if e.severity.value == "error"]

    # ── Retry loop (if needed) ────────────────────────────────────────────────
    rejected_candidates: list[str] = []
    total_attempts = 0

    if blocking:

        def generate_fn(doc: str, retry_prompt: str) -> str:
            combined = (
                f"Original request: {args.prompt}\n\n"
                f"Current document to repair:\n{doc}\n\n"
                f"{retry_prompt}"
            )
            return provider.generate(combined, system_prompt)

        def validate_fn(doc: str) -> list:
            try:
                return validate(doc)
            except Exception:
                return []

        retry_result = run_retry_loop(
            document=content,
            errors=blocking,
            generate_fn=generate_fn,
            validate_fn=validate_fn,
            generation_id=generation_id,
            document_id=document_id,
            schema_version="1.0.0",
            model=provider.model_name,
            temperature=0,
            top_p=1,
            writer=writer,
        )
        content = retry_result.document
        total_attempts = retry_result.attempts

        # Collect rejected domain candidates from retry errors
        for verr in retry_result.errors:
            if verr.field == "domain" and verr.received:
                rejected_candidates.append(str(verr.received))
    else:
        total_attempts = 1

    total_duration_ms = int((time.monotonic() - t_start) * 1000)

    # ── Commit ────────────────────────────────────────────────────────────────
    final_errors = []
    try:
        final_errors = validate(content)
    except Exception:
        pass

    commit_result = akf_commit(
        document=content,
        output_path=output_path,
        errors=final_errors,
        generation_id=generation_id,
        document_id=document_id,
        schema_version="1.0.0",
        total_attempts=total_attempts,
        rejected_candidates=rejected_candidates,
        model=provider.model_name,
        temperature=0,
        total_duration_ms=total_duration_ms,
        writer=writer,
    )

    # ── Output ────────────────────────────────────────────────────────────────
    if commit_result.committed:
        ok(f"Saved to: {commit_result.path}")
        ok("Validation passed!")
    else:
        # Fallback: save anyway (pre-Phase 2.3 behaviour) and warn
        saved_path = save_file(content, filename, out_dir)
        ok(f"Saved to: {saved_path}")
        warn(f"Validation found {len(commit_result.blocking_errors)} issues.")


# ─── ENRICH ──────────────────────────────────────────────────────────────────


def cmd_enrich(args: argparse.Namespace) -> None:
    """Add YAML frontmatter to existing Markdown files via the AKF pipeline."""
    from akf.pipeline import Pipeline, EnrichResult

    target = Path(args.path)
    if not target.exists():
        err(f"Path not found: {target}")
        sys.exit(3)

    dry_run: bool = getattr(args, "dry_run", False)
    force: bool = getattr(args, "force", False)
    model: str = getattr(args, "model", "auto")
    output: str | None = getattr(args, "output", None)

    pipeline = Pipeline(
        model=model,
        telemetry_path=TELEMETRY_PATH if not dry_run else None,
        verbose=False,
    )

    if target.is_file():
        md_files = [target]
    elif target.is_dir():
        exclude = CLI_EXCLUDE_PATTERNS + ["10-OVERHEAD"]
        md_files = sorted(f for f in target.rglob("*.md") if not any(x in str(f) for x in exclude))
    else:
        err(f"Not a file or directory: {target}")
        sys.exit(3)

    if not md_files:
        warn("No .md files found.")
        sys.exit(2)

    if dry_run:
        info("DRY RUN — no files will be modified")
    info(f"Enriching {len(md_files)} file(s)...")
    print()

    results: list[EnrichResult] = []
    for md_file in md_files:
        try:
            result = pipeline.enrich(
                path=md_file,
                force=force,
                dry_run=dry_run,
                output=output,
                model=model,
            )
        except Exception as exc:
            from akf.pipeline import EnrichResult

            result = EnrichResult(
                success=False,
                path=md_file,
                status="failed",
                skip_reason=str(exc),
            )
        results.append(result)
        rel = str(md_file)

        if result.status == "enriched":
            n = result.attempts
            note = f"({n} attempt{'s' if n != 1 else ''})"
            if n > 1 and result.errors:
                code = getattr(result.errors[0], "code", "")
                note = f"({n} attempts — {code} retry)"
            print(f"{GREEN}✅ {rel:<50} {note}{NC}")
        elif result.status == "skipped":
            print(f"{BLUE}⏭  {rel:<50} (skipped — {result.skip_reason}){NC}")
        elif result.status == "failed":
            print(f"{RED}❌ {rel:<50} (failed — after {result.attempts} attempts){NC}")
        elif result.status == "warning":
            print(f"{YELLOW}⚠️  {rel:<50} (skipped — {result.skip_reason}){NC}")

    print()
    enriched = sum(1 for r in results if r.status == "enriched")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "failed")
    warned = sum(1 for r in results if r.status == "warning")
    info(f"Results: {enriched} enriched, {skipped} skipped, {failed} failed, {warned} warning(s)")

    sys.exit(1 if failed > 0 else 0)


# ─── MODELS ───────────────────────────────────────────────────────────────────


def cmd_models(args: argparse.Namespace) -> None:
    """List available LLM providers."""
    providers = list_providers()

    info("Available LLM providers:\n")
    for name, available in providers.items():
        provider = PROVIDERS[name]()
        status = f"{GREEN}✅" if available else f"{RED}❌"
        print(f"{status} {name:<10} {provider.display_name}{NC}")
        if available:
            print(f"   Model: {provider.model_name}")
        else:
            # Show what's needed
            if name == "claude":
                print(f"   {YELLOW}Set ANTHROPIC_API_KEY{NC}")
            elif name == "gemini":
                print(f"   {YELLOW}Set GOOGLE_API_KEY{NC}")
            elif name == "gpt4":
                print(f"   {YELLOW}Set OPENAI_API_KEY{NC}")
            elif name == "groq":
                print(f"   {YELLOW}Set GROQ_API_KEY{NC}")
            elif name == "grok":
                print(f"   {YELLOW}Set XAI_API_KEY{NC}")
            elif name == "ollama":
                print(f"   {YELLOW}Run Ollama server{NC}")
        print()


# ─── INDEX (RAG CORPUS) ───────────────────────────────────────────────────────


def cmd_index(args: argparse.Namespace) -> None:
    """Index corpus into local Chroma vector database for RAG retrieval."""
    try:
        from rag.indexer import index_corpus
        from rag.config import load_config, RAGConfig
    except Exception as exc:
        err(f"RAG modules unavailable: {exc}")
        info("Install RAG dependencies: pip install -e .[rag]")
        sys.exit(1)

    cfg = load_config()

    # Override corpus dir if --corpus provided
    if getattr(args, "corpus", None):
        corpus_path = Path(args.corpus).expanduser()
        cfg = RAGConfig(
            corpus_dir=corpus_path,
            persist_directory=cfg.persist_directory,
            collection_name=cfg.collection_name,
            embedding_model=cfg.embedding_model,
            markdown_glob=cfg.markdown_glob,
            batch_size=cfg.batch_size,
        )

    corpus_dir = cfg.corpus_dir
    if not corpus_dir.exists():
        err(f"Corpus directory not found: {corpus_dir}")
        sys.exit(1)

    # Reset collection if --reset requested
    if getattr(args, "reset", False):
        try:
            import chromadb

            cfg.persist_directory.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(cfg.persist_directory))
            try:
                client.delete_collection(cfg.collection_name)
                info(f"Deleted collection '{cfg.collection_name}' (--reset)")
            except Exception:
                pass  # Collection may not exist yet
        except ImportError:
            err("chromadb not installed. Install with: pip install chromadb")
            sys.exit(1)

    info(f"Indexing corpus: {corpus_dir}")
    try:
        stats = index_corpus(cfg)
    except FileNotFoundError as exc:
        err(str(exc))
        sys.exit(1)
    except Exception as exc:
        err(f"Indexing failed: {exc}")
        sys.exit(1)

    ok(
        f"Indexed {stats.files_indexed} files, {stats.chunks_indexed} chunks"
        f" into collection '{cfg.collection_name}'"
    )


# ─── ASK (RAG COPILOT) ──────────────────────────────────────────────────────


def cmd_ask(args: argparse.Namespace) -> None:
    """Answer a question using local RAG retrieval + synthesis."""
    try:
        from rag.copilot import answer_question
        from rag.retriever import retrieve
    except Exception as exc:
        err(f"RAG modules unavailable: {exc}")
        info("Install RAG dependencies: pip install -e .[rag]")
        sys.exit(1)

    query = (args.query or "").strip()
    if not query:
        err("Query must not be empty.")
        sys.exit(1)

    top_k = max(1, int(getattr(args, "top_k", 5) or 5))
    model = getattr(args, "model", "auto") or "auto"
    no_llm = bool(getattr(args, "no_llm", False))

    mode = "retrieval-only" if no_llm else f"model: {model}"
    info(f"RAG Copilot  →  {mode}  |  top-k: {top_k}")

    t_start = time.monotonic()

    if no_llm:
        try:
            retrieval = retrieve(query=query, top_k=top_k)
        except Exception as exc:
            err(f"RAG ask failed: {exc}")
            sys.exit(1)

        try:
            from akf.telemetry import TelemetryWriter, AskQueryEvent, new_generation_id

            TelemetryWriter(path=TELEMETRY_PATH).write(
                AskQueryEvent(
                    generation_id=new_generation_id(),
                    tenant_id="cli",
                    mode="retrieval-only",
                    model="none",
                    top_k=top_k,
                    no_llm=no_llm,
                    max_distance=None,
                    hits_used=len(retrieval.hits),
                    insufficient_context=not bool(retrieval.hits),
                    duration_ms=int((time.monotonic() - t_start) * 1000),
                )
            )
        except Exception:
            pass

        if not retrieval.hits:
            print()
            warn("No relevant chunks found.")
            return

        print()
        print(f"Retrieved {len(retrieval.hits)} chunk(s):")
        for idx, hit in enumerate(retrieval.hits, 1):
            source = hit.metadata.get("source", "unknown")
            section = hit.metadata.get("section", "")
            print(f"{idx}. distance={hit.distance:.4f} source={source} section={section}")
            print(hit.content)
            print()
        return

    try:
        result = answer_question(query=query, top_k=top_k, model=model)
    except Exception as exc:
        err(f"RAG ask failed: {exc}")
        sys.exit(1)

    try:
        from akf.telemetry import TelemetryWriter, AskQueryEvent, new_generation_id

        TelemetryWriter(path=TELEMETRY_PATH).write(
            AskQueryEvent(
                generation_id=new_generation_id(),
                tenant_id="cli",
                mode="synthesis",
                model=getattr(result, "model", model),
                top_k=top_k,
                no_llm=no_llm,
                max_distance=None,
                hits_used=getattr(result, "hits_used", 0),
                insufficient_context=getattr(result, "insufficient_context", False),
                duration_ms=int((time.monotonic() - t_start) * 1000),
            )
        )
    except Exception:
        pass

    print()
    print(result.answer)

    if result.sources:
        print()
        print("Sources:")
        for source in result.sources:
            print(f"- {source}")
    else:
        print()
        warn("No sources returned.")


# ─── MARKET ANALYSIS ──────────────────────────────────────────────────────────


def cmd_market_analysis(args: argparse.Namespace) -> None:
    """Run the three-stage market analysis pipeline.

    Stage 1 — Market Analysis (size, trends, segments)
    Stage 2 — Competitor Comparison (players, SWOT, gaps)
    Stage 3 — Positioning (USP, messaging, strategy)
    """
    from akf.market_pipeline import MarketAnalysisPipeline

    request: str = args.request
    model: str = getattr(args, "model", "auto") or "auto"
    out_dir = Path(args.output) if getattr(args, "output", None) else OUTPUT_DIR / "market-analysis"
    stages_arg: str = getattr(args, "stages", "all") or "all"

    if not request or not request.strip():
        err("Market request is required.")
        sys.exit(1)

    pipeline = MarketAnalysisPipeline(output=str(out_dir), model=model, verbose=True)

    info(f"Market Analysis Pipeline  —  model: {model}")
    info(f"Request : {request[:80]}")
    info(f"Output  : {out_dir}")
    info(f"Stages  : {stages_arg}")
    print()

    if stages_arg == "market":
        stage = pipeline.analyze_market(request)
        if stage.success:
            ok(f"Stage 1 complete → {stage.file_path}")
        else:
            err(f"Stage 1 failed: {stage.error}")
            sys.exit(1)
        return

    if stages_arg == "competitors":
        err("Stage 2 requires market context. Run with --stages all or provide context.")
        sys.exit(1)

    if stages_arg == "positioning":
        err("Stage 3 requires market + competitor context. Run with --stages all.")
        sys.exit(1)

    # Default: full pipeline
    result = pipeline.analyze(request)
    print()

    statuses = [
        ("Stage 1 — Market Analysis", result.market_analysis),
        ("Stage 2 — Competitor Analysis", result.competitor_analysis),
        ("Stage 3 — Positioning", result.positioning),
    ]
    for label, stage in statuses:
        if stage.success:
            ok(f"{label} → {stage.file_path.name if stage.file_path else 'ok'}")
        else:
            err(f"{label} — {stage.error}")

    print()
    total_s = result.total_duration_ms / 1000
    info(f"Total duration: {total_s:.1f}s | Files written: {len(result.files)}")

    if result.files:
        info("Output files:")
        for fp in result.files:
            info(f"  {fp}")

    sys.exit(0 if result.success else 1)


# ─── CANVAS ───────────────────────────────────────────────────────────────────


def cmd_canvas(args: argparse.Namespace) -> None:
    """Generate an Obsidian Canvas JSON file from a validated corpus directory.

    Reads all .md files in *args.input*, parses YAML frontmatter and ``related``
    wiki-links, then writes a ``.canvas`` file compatible with Obsidian Canvas.

    Args:
        args: Parsed CLI arguments with ``input``, ``output``, and
            ``group_by`` attributes.
    """
    from akf.canvas_generator import CanvasGenerator

    input_dir = Path(args.input)
    output_file = Path(args.output)
    group_by: str = getattr(args, "group_by", "domain") or "domain"

    if not input_dir.exists():
        err(f"Input directory not found: {input_dir}")
        sys.exit(1)

    if not input_dir.is_dir():
        err(f"--input must be a directory: {input_dir}")
        sys.exit(1)

    info(f"Canvas  →  input: {input_dir}  |  group-by: {group_by}")

    try:
        canvas = CanvasGenerator().generate(input_dir, output_file, group_by=group_by)
    except Exception as exc:  # pylint: disable=broad-except
        err(f"Canvas generation failed: {exc}")
        sys.exit(1)

    n_nodes = len(canvas.get("nodes", []))
    n_edges = len(canvas.get("edges", []))
    ok(f"Canvas written → {output_file}  ({n_nodes} nodes, {n_edges} edges)")


# ─── GAPS HELPERS ─────────────────────────────────────────────────────────────


def _normalize_link(link: str) -> str:
    """Normalize a WikiLink name for deduplication (spaces→underscores, lowercase)."""
    return link.strip().replace(" ", "_").lower()


_DOMAIN_KEYWORDS: list[tuple[str, frozenset[str]]] = [
    (
        "devops",
        frozenset(
            {
                "docker",
                "kubernetes",
                "ci/cd",
                "ci",
                "cd",
                "github",
                "actions",
                "deploy",
                "deployment",
                "helm",
                "pipeline",
            }
        ),
    ),
    (
        "api-design",
        frozenset(
            {"api", "rest", "graphql", "http", "openapi", "swagger", "endpoint", "endpoints"}
        ),
    ),
    (
        "security",
        frozenset(
            {"jwt", "oauth", "security", "auth", "authentication", "authorization", "ssl", "tls"}
        ),
    ),
    (
        "backend-engineering",
        frozenset(
            {"fastapi", "python", "service", "architecture", "microservice", "database", "backend"}
        ),
    ),
]

_TYPE_KEYWORDS: list[tuple[str, frozenset[str]]] = [
    ("checklist", frozenset({"checklist", "review"})),
    ("guide", frozenset({"guide", "tutorial", "how-to", "howto"})),
    ("concept", frozenset({"patterns", "strategies", "principles", "models", "concepts"})),
]

_DOMAIN_AUDIENCE: dict[str, str] = {
    "devops": "DevOps engineers",
    "api-design": "API developers",
    "security": "security engineers",
    "backend-engineering": "backend engineers",
}


def _infer_domain(link_name: str) -> str:
    """Infer knowledge domain from a WikiLink name using keyword heuristics."""
    words = set(link_name.lower().replace("_", " ").replace("-", " ").split())
    for domain, keywords in _DOMAIN_KEYWORDS:
        if words & keywords:
            return domain
    return "backend-engineering"


def _infer_type(link_name: str) -> str:
    """Infer document type from a WikiLink name using keyword heuristics."""
    words = set(link_name.lower().replace("_", " ").replace("-", " ").split())
    for type_name, keywords in _TYPE_KEYWORDS:
        if words & keywords:
            return type_name
    return "concept"


def _make_suggestion(link: str) -> dict:
    """Build a structured plan.json entry from a missing WikiLink name."""
    topic = link.replace("_", " ")
    domain = _infer_domain(link)
    doc_type = _infer_type(link)
    audience = _DOMAIN_AUDIENCE.get(domain, "engineers")
    return {
        "prompt": f"Create a {doc_type} on {topic} for {audience}",
        "domain": domain,
        "type": doc_type,
    }


# ─── GAPS ─────────────────────────────────────────────────────────────────────


def cmd_gaps(args: argparse.Namespace) -> None:
    """Scan vault for broken WikiLinks in related: fields and suggest plan.json entries.

    Reads all .md files under --path, parses YAML frontmatter, collects
    [[WikiLink]] values from the ``related`` field, then reports which links
    point to files that do not exist in the vault.
    """
    import json
    import yaml

    vault_path = Path(args.path)
    if not vault_path.exists():
        err(f"Path not found: {vault_path}")
        sys.exit(1)
    if not vault_path.is_dir():
        err(f"--path must be a directory: {vault_path}")
        sys.exit(1)

    md_files = list(vault_path.rglob("*.md"))
    existing_stems_normalized = {_normalize_link(f.stem) for f in md_files}

    wikilink_re = re.compile(r"\[\[([^\]|#\n]+?)(?:\|[^\]]*)?\]\]")
    frontmatter_re = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

    # Map normalized key → canonical display name (underscore form), deduplicated
    all_links: dict[str, str] = {}
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        m = frontmatter_re.match(content)
        if not m:
            continue

        try:
            frontmatter = yaml.safe_load(m.group(1))
        except Exception:
            continue

        if not isinstance(frontmatter, dict):
            continue

        related = frontmatter.get("related")
        if not related:
            continue

        if isinstance(related, list):
            related_str = " ".join(str(x) for x in related)
        else:
            related_str = str(related)

        for link in wikilink_re.findall(related_str):
            raw = link.strip()
            norm = _normalize_link(raw)
            if norm not in all_links:
                # Prefer the underscore-normalized display form
                all_links[norm] = raw.replace(" ", "_")

    missing = sorted(
        display for norm, display in all_links.items() if norm not in existing_stems_normalized
    )

    fmt = getattr(args, "format", None)
    output_path = getattr(args, "output", None)

    suggestions = [_make_suggestion(link) for link in missing]

    if fmt == "json":
        print(json.dumps(suggestions, indent=2))
    else:
        if not missing:
            ok("No missing files found. All WikiLinks in related: fields are resolved.")
        else:
            print(f"\nMissing files ({len(missing)}):")
            for name in missing:
                print(f"  - {name}")
            print("\nSuggested plan.json additions:")
            print(json.dumps(suggestions, indent=2))

    if output_path and missing:
        plan_file = Path(output_path)
        existing_plan: list = []
        if plan_file.exists():
            try:
                raw = plan_file.read_text(encoding="utf-8")
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    existing_plan = parsed
            except Exception:
                pass
        existing_plan.extend(suggestions)
        plan_file.write_text(json.dumps(existing_plan, indent=2) + "\n", encoding="utf-8")
        ok(f"Written to {plan_file} ({len(suggestions)} new entries)")


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(prog="akf")
    sub = parser.add_subparsers(dest="command", required=True)

    # Init command
    init = sub.add_parser("init", help="Generate akf.yaml for a new vault")
    init.add_argument("--path", "-p", help="Target directory (default: CWD)")
    init.add_argument("--force", "-f", action="store_true", help="Overwrite existing akf.yaml")

    # Generate command
    gen = sub.add_parser("generate", help="Generate knowledge file")
    gen.add_argument(
        "prompt", nargs="?", default=None, help="Generation prompt (omit when using --batch)"
    )
    gen.add_argument(
        "--batch",
        "-b",
        metavar="PLAN_JSON",
        help="JSON file with batch plan (array of {prompt, domain, type})",
    )
    gen.add_argument(
        "--model",
        "-m",
        choices=["auto", "claude", "gemini", "gpt4", "groq", "grok", "ollama"],
        default="auto",
        help="LLM provider (default: auto-select)",
    )
    gen.add_argument("--output", "-o", help="Custom output path")
    gen.add_argument(
        "--no-rag",
        action="store_true",
        dest="no_rag",
        help="Disable RAG context injection (default: enabled if corpus indexed)",
    )

    # Validate command
    val = sub.add_parser("validate", help="Check Markdown YAML")
    val.add_argument("--file", "-f", help="Validate single file")
    val.add_argument("--path", "-p", help="Validate all .md files in folder")
    val.add_argument("--strict", "-s", action="store_true", help="Promote warnings to errors")

    # Enrich command
    enr = sub.add_parser("enrich", help="Add YAML frontmatter to existing Markdown files")
    enr.add_argument("path", help="File or directory to enrich")
    enr.add_argument("--dry-run", action="store_true", help="Print YAML without writing")
    enr.add_argument("--force", "-f", action="store_true", help="Overwrite valid frontmatter")
    enr.add_argument(
        "--model",
        "-m",
        choices=["auto", "claude", "gemini", "gpt4", "groq", "grok", "ollama"],
        default="auto",
    )
    enr.add_argument("--output", "-o", help="Output directory (copies, no overwrite)")

    # Market Analysis command
    mkt = sub.add_parser(
        "market-analysis",
        help="Run three-stage market analysis pipeline (market → competitors → positioning)",
    )
    mkt.add_argument(
        "request",
        help='Market request, e.g. "B2B SaaS project management tools for SMEs"',
    )
    mkt.add_argument(
        "--model",
        "-m",
        choices=["auto", "claude", "gemini", "gpt4", "groq", "grok", "ollama"],
        default="auto",
        help="LLM provider (default: auto-select)",
    )
    mkt.add_argument(
        "--output",
        "-o",
        help="Output directory (default: ./market-analysis/)",
    )
    mkt.add_argument(
        "--stages",
        choices=["all", "market", "competitors", "positioning"],
        default="all",
        help="Which stages to run (default: all three)",
    )

    # Models command
    sub.add_parser("models", help="List available LLM providers")

    # Index command (RAG corpus indexing)
    idx = sub.add_parser("index", help="Index corpus into local vector database for RAG retrieval")
    idx.add_argument(
        "--corpus",
        help="Corpus directory to index (default: corpus/ or RAG_CORPUS_DIR env)",
    )
    idx.add_argument(
        "--reset",
        action="store_true",
        help="Delete and rebuild the collection from scratch",
    )

    # Ask command (RAG copilot)
    ask = sub.add_parser("ask", help="Ask a question over local RAG index")
    ask.add_argument("query", help="Natural-language question")
    ask.add_argument("--top-k", type=int, default=5, help="Number of retrieved chunks (default: 5)")
    ask.add_argument(
        "--model",
        "-m",
        choices=["auto", "claude", "gemini", "gpt4", "groq", "grok", "ollama"],
        default="auto",
        help="LLM provider for synthesis (default: auto-select)",
    )
    ask.add_argument(
        "--no-llm",
        action="store_true",
        help="Retrieval-only mode: return top-k chunks without synthesis",
    )

    # Canvas command
    cnv = sub.add_parser("canvas", help="Generate Obsidian Canvas JSON from validated corpus")
    cnv.add_argument(
        "--input",
        "-i",
        required=True,
        metavar="INPUT_DIR",
        help="Directory containing validated .md files",
    )
    cnv.add_argument(
        "--output", "-o", required=True, metavar="OUTPUT_FILE", help="Output .canvas file path"
    )
    cnv.add_argument(
        "--group-by",
        default="domain",
        choices=["domain", "type", "level"],
        help="Frontmatter field used to group nodes into columns (default: domain)",
    )

    # Gaps command
    gaps = sub.add_parser(
        "gaps",
        help="Find broken WikiLinks in related: fields and suggest plan.json entries",
    )
    gaps.add_argument(
        "--path",
        "-p",
        required=True,
        help="Vault directory to scan for .md files",
    )
    gaps.add_argument(
        "--output",
        "-o",
        metavar="PLAN_JSON",
        help="Append suggestions to this plan.json file",
    )
    gaps.add_argument(
        "--format",
        choices=["json"],
        help="Output format: 'json' prints only the JSON array",
    )

    # Serve command

    srv = sub.add_parser("serve", help="Start REST API server or MCP server")
    srv.add_argument("--host", default="0.0.0.0")
    srv.add_argument("--port", type=int, default=8000)
    srv.add_argument(
        "--mcp",
        action="store_true",
        help="Run as MCP server instead of REST API (requires: pip install ai-knowledge-filler[mcp])",
    )
    srv.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http"],
        help="MCP transport: stdio (default, for local clients) or streamable-http (for remote)",
    )

    args = parser.parse_args()
    if args.command == "init":
        cmd_init(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "enrich":
        cmd_enrich(args)
    elif args.command == "models":
        cmd_models(args)
    elif args.command == "index":
        cmd_index(args)
    elif args.command == "ask":
        cmd_ask(args)
    elif args.command == "canvas":
        cmd_canvas(args)
    elif args.command == "market-analysis":
        cmd_market_analysis(args)
    elif args.command == "gaps":
        cmd_gaps(args)
    elif args.command == "serve":
        cmd_serve(args)
    return 0


# ─── SERVE ────────────────────────────────────────────────────────────────────


def cmd_serve(args):
    """Start AKF as MCP server (--mcp) or REST API (default)."""
    if getattr(args, "mcp", False):
        try:
            from akf.mcp_server import run as mcp_run
        except ImportError:
            err("MCP dependencies not installed. Run: pip install ai-knowledge-filler[mcp]")
            sys.exit(1)
        from typing import Literal, cast as _cast

        _transport = _cast(Literal["stdio", "sse", "streamable-http"], args.transport)
        info(f"Starting AKF MCP server (transport: {_transport})...")
        mcp_run(transport=_transport)
        return

    # REST API (default)
    try:
        import uvicorn
    except ImportError:
        err("uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)

    host = getattr(args, "host", "0.0.0.0")
    port = getattr(args, "port", 8000)
    info(f"Starting AKF API on http://{host}:{port}")
    info(f"Docs: http://{host}:{port}/docs")
    uvicorn.run("akf.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
