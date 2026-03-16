from __future__ import annotations
import re, os, time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

@dataclass
class GenerateResult:
    success: bool
    content: str
    file_path: object = None
    attempts: int = 0
    errors: list = field(default_factory=list)
    generation_id: str = ""
    duration_ms: int = 0
    def __repr__(self):
        s = "VALID" if self.success else "INVALID"
        return f"GenerateResult({s}, attempts={self.attempts}, errors={len(self.errors)})"

@dataclass
class ValidateResult:
    valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    filepath: object = None
    def __repr__(self):
        s = "VALID" if self.valid else "INVALID"
        return f"ValidateResult({s}, errors={len(self.errors)}, warnings={len(self.warnings)})"




@dataclass
class EnrichResult:
    """Result of enriching a single Markdown file."""
    success: bool
    path: Path
    status: str          # "enriched" | "skipped" | "failed" | "warning"
    skip_reason: str = ""
    attempts: int = 0
    existing_fields: list[str] = field(default_factory=list)
    generated_fields: list[str] = field(default_factory=list)
    generation_id: str = ""
    errors: list = field(default_factory=list)


def _patch_dates(content: str, today: str) -> str:
    """Overwrite created/updated in YAML frontmatter with today's date.

    Prevents LLM from copying stale dates out of examples or training data.
    Only modifies lines inside the opening --- block.
    """
    import re
    lines = content.splitlines(keepends=True)
    in_front = False
    result = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if i == 0 and stripped == "---":
            in_front = True
            result.append(line)
            continue
        if in_front and stripped == "---":
            in_front = False
            result.append(line)
            continue
        if in_front and re.match(r"^(created|updated)\s*:", stripped):
            key = stripped.split(":")[0]
            result.append(f"{key}: {today}\n")
            continue
        result.append(line)
    return "".join(result)


def _try_retrieve(query: str, top_k: int = 3) -> str:
    """Attempt RAG retrieval; return formatted context string or '' on failure."""
    try:
        import rag.retriever as _retriever
        if _retriever is None:
            return ""
        result = _retriever.retrieve(query, top_k=top_k)
        if not result.hits:
            return ""
        parts = []
        for hit in result.hits:
            filename = hit.metadata.get("filename", "")
            parts.append(f"[{filename}]\n{hit.content}")
        return "\n\n---\n\n".join(parts)
    except (ImportError, Exception):
        return ""


class Pipeline:
    def __init__(self, output=None, model="auto", telemetry_path=None, verbose=True, writer=None, config=None, rag_enabled: bool = True):
        self.model = model
        self.verbose = verbose
        self.rag_enabled = rag_enabled
        self.output_dir = Path(output).expanduser() if output else Path(os.getenv("AKF_OUTPUT_DIR", "."))
        self.telemetry_path = Path(telemetry_path).expanduser() if telemetry_path else Path(os.getenv("AKF_TELEMETRY_PATH", "telemetry/events.jsonl"))
        self._system_prompt = None
        self.writer = writer
        self._config = config
        self.model_name = model

    def _log(self, msg):
        if self.verbose:
            print(f"->  {msg}")

    def _load_system_prompt(self):
        if self._system_prompt:
            return self._system_prompt
        try:
            import akf as _pkg
            p = Path(_pkg.__file__).parent / "system_prompt.md"
            if p.exists():
                self._system_prompt = p.read_text(encoding="utf-8")
                return self._system_prompt
        except Exception:
            pass
        local = Path(__file__).parent / "system_prompt.md"
        if local.exists():
            self._system_prompt = local.read_text(encoding="utf-8")
            return self._system_prompt
        raise FileNotFoundError("system_prompt.md not found")

    @staticmethod
    def _extract_filename(content, prompt):
        import re
        match = re.search(r'title:\s*["\'\']?(.+?)["\'\']?\s*\n', content)
        if match:
            title = match.group(1).strip().strip("\"'")
            name = re.sub(r"[\s-]+", "_", re.sub(r"[^\w\s-]", "", title))
            return f"{name}.md"
        return "_".join(re.sub(r"[^\w\s]", "", prompt).split()[:4]).lower() + ".md"

    def _resolve_path(self, content, prompt, out_dir):
        out_dir.mkdir(parents=True, exist_ok=True)
        fp = out_dir / self._extract_filename(content, prompt)
        if fp.exists():
            ts = datetime.now().strftime("%H%M%S")
            fp = out_dir / f"{fp.stem}_{ts}.md"
        return fp

    def generate(self, prompt, output=None, model=None, hints=None):
        from llm_providers import get_provider
        from akf.telemetry import TelemetryWriter, new_generation_id
        from akf.retry_controller import run_retry_loop
        from akf.commit_gate import commit as akf_commit
        from akf.validator import validate
        from akf.validation_error import Severity
        try:
            provider = get_provider(model or self.model)
        except Exception as e:
            return GenerateResult(success=False, content="", errors=[str(e)])
        system_prompt = self._load_system_prompt()
        if self.rag_enabled:
            rag_context = _try_retrieve(prompt, top_k=3)
            if rag_context:
                system_prompt += "\n\n## RELEVANT CORPUS CONTEXT\n\n" + rag_context
        if hints:
            context_lines = []
            if hints.get("domain"):
                context_lines.append(f"domain: {hints['domain']}")
            if hints.get("type"):
                context_lines.append(f"type: {hints['type']}")
            if context_lines:
                system_prompt += "\n\nContext for this generation:\n" + "\n".join(context_lines)
        self._log(f"Generating via {provider.display_name}...")
        generation_id = new_generation_id()
        writer = self.writer if self.writer is not None else TelemetryWriter(path=self.telemetry_path)
        t_start = time.monotonic()
        try:
            prompt = f"Create a complete Markdown knowledge file about: {prompt}"
            content = provider.generate(prompt, system_prompt)
        except Exception as e:
            return GenerateResult(success=False, content="", errors=[str(e)], generation_id=generation_id)
        content = _patch_dates(content, datetime.now().strftime("%Y-%m-%d"))
        out_dir = Path(output).expanduser() if output else self.output_dir
        output_path = self._resolve_path(content, prompt, out_dir)
        document_id = output_path.stem
        try:
            initial_errors = validate(content)
        except Exception:
            initial_errors = []
        blocking = [e for e in initial_errors if e.severity == Severity.ERROR]
        rejected_candidates = []
        total_attempts = 1
        if blocking:
            def generate_fn(doc, retry_prompt):
                return provider.generate(retry_prompt, system_prompt)
            def validate_fn(doc):
                try:
                    return validate(doc)
                except Exception:
                    return []
            retry_result = run_retry_loop(
                document=content, errors=blocking,
                generate_fn=generate_fn, validate_fn=validate_fn,
                generation_id=generation_id, document_id=document_id,
                schema_version="1.0.0", model=provider.model_name,
                temperature=0, top_p=1, writer=writer,
            )
            content = retry_result.document
            total_attempts = retry_result.attempts
            for e in retry_result.errors:
                if e.field == "domain" and e.received:
                    rejected_candidates.append(str(e.received))
        total_duration_ms = int((time.monotonic() - t_start) * 1000)
        try:
            final_errors = validate(content)
        except Exception:
            final_errors = []
        commit_result = akf_commit(
            document=content, output_path=output_path, errors=final_errors,
            generation_id=generation_id, document_id=document_id,
            schema_version="1.0.0", total_attempts=total_attempts,
            rejected_candidates=rejected_candidates, model=provider.model_name,
            temperature=0, total_duration_ms=total_duration_ms, writer=writer,
        )
        if commit_result.committed:
            self._log(f"Saved: {commit_result.path}")
            return GenerateResult(success=True, content=content, file_path=commit_result.path,
                attempts=total_attempts, generation_id=generation_id, duration_ms=total_duration_ms)
        else:
            output_path.write_text(content, encoding="utf-8")
            return GenerateResult(success=False, content=content, file_path=output_path,
                attempts=total_attempts, errors=commit_result.blocking_errors,
                generation_id=generation_id, duration_ms=total_duration_ms)

    def validate(self, filepath, strict=False):
        from akf.validator import validate as _validate
        from akf.validation_error import Severity
        fp = Path(filepath).expanduser()
        if not fp.exists():
            return ValidateResult(valid=False, errors=[f"File not found: {fp}"], filepath=fp)
        all_errors = _validate(fp.read_text(encoding="utf-8"))
        if strict:
            errors = [str(e) for e in all_errors]
            warnings = []
        else:
            errors = [str(e) for e in all_errors if e.severity == Severity.ERROR]
            warnings = [str(e) for e in all_errors if e.severity == Severity.WARNING]
        return ValidateResult(valid=len(errors) == 0, errors=errors, warnings=warnings, filepath=fp)

    def batch_generate(self, prompts, output=None, model=None):
        """Generate multiple documents sequentially.

        prompts: list of str or list of dict with keys:
            - prompt (required): the generation prompt
            - domain (optional): injected into system prompt context
            - type (optional): injected into system prompt context
        """
        results = []
        for i, item in enumerate(prompts, 1):
            if isinstance(item, dict):
                prompt_text = item.get("prompt", "")
                hints = {k: v for k, v in item.items() if k != "prompt"} or None
            else:
                prompt_text = item
                hints = None
            self._log(f"[{i}/{len(prompts)}] {prompt_text[:60]}...")
            results.append(self.generate(prompt_text, output=output, model=model, hints=hints))
        return results

    def enrich(
        self,
        path: "str | Path",
        force: bool = False,
        dry_run: bool = False,
        output: "str | Path | None" = None,
        model: "str | None" = None,
    ) -> "EnrichResult":
        """Enrich a single Markdown file with YAML frontmatter."""
        import re as _re
        import warnings
        import yaml
        from datetime import date
        from llm_providers import get_provider
        from akf.validator import validate
        from akf.retry_controller import run_retry_loop
        from akf.config import get_config
        from akf.telemetry import TelemetryWriter, EnrichEvent, new_generation_id
        if self.writer is None and self.telemetry_path is not None:
            self.writer = TelemetryWriter(path=self.telemetry_path)
        from akf.enricher import (
            REQUIRED_FIELDS, build_prompt, derive_title,
            extract_missing_fields, merge_yaml, read_file,
            write_back, _assemble,
        )

        file_path = Path(path)
        today = date.today().isoformat()
        generation_id = new_generation_id()

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            existing, body = read_file(file_path)

        existing_field_names = list(existing.keys())

        if not body.strip() and not existing:
            return EnrichResult(
                success=True, path=file_path, status="warning",
                skip_reason="empty_file", generation_id=generation_id,
            )

        if file_path.suffix.lower() != ".md":
            return EnrichResult(
                success=True, path=file_path, status="skipped",
                skip_reason="non_markdown", generation_id=generation_id,
            )

        if "title" not in existing or not existing.get("title"):
            existing["title"] = derive_title(file_path)

        missing = extract_missing_fields(existing, REQUIRED_FIELDS)

        if not missing and not force:
            if not dry_run and self.writer is not None:
                self.writer.write(EnrichEvent(
                    generation_id=generation_id, file=str(file_path),
                    schema_version="1.0.0", existing_fields=existing_field_names,
                    generated_fields=[], attempts=0, converged=True,
                    skipped=True, skip_reason="valid_frontmatter",
                    model=model or self.model_name, temperature=0.0,
                ))
            return EnrichResult(
                success=True, path=file_path, status="skipped",
                skip_reason="valid_frontmatter", existing_fields=existing_field_names,
                generation_id=generation_id,
            )

        cfg = self._config if self._config is not None else get_config()
        prompt = build_prompt(
            body=body,
            existing=existing,
            missing=missing if not force else REQUIRED_FIELDS,
            taxonomy_domains=cfg.domains,
            today=today,
        )
        try:
            provider = get_provider(model or self.model_name)
        except Exception as exc:
            return EnrichResult(
                success=False, path=file_path, status="failed",
                skip_reason=str(exc), generation_id=generation_id,
                existing_fields=existing_field_names,
            )
        raw_generated = provider.generate(prompt, "")

        try:
            generated = yaml.safe_load(raw_generated) or {}
            if not isinstance(generated, dict):
                generated = {}
        except Exception:
            generated = {}

        merged = merge_yaml(existing, generated, force=force, today=today)
        document = _assemble(merged, body)

        try:
            initial_errors = validate(document)
        except Exception:
            initial_errors = []

        blocking = [e for e in initial_errors if e.severity.value == "error"]
        total_attempts = 1
        converged = not blocking

        if blocking:
            def _gen_fn(doc: str, retry_prompt: str) -> str:
                return provider.generate(retry_prompt, "")

            def _val_fn(doc: str) -> list:
                try:
                    return validate(doc)
                except Exception:
                    return []

            retry_result = run_retry_loop(
                document=document, errors=blocking,
                generate_fn=_gen_fn, validate_fn=_val_fn,
                generation_id=generation_id, document_id=file_path.stem,
                schema_version="1.0.0", model=provider.model_name,
                temperature=0, top_p=1, writer=self.writer,
            )
            document = retry_result.document
            total_attempts = retry_result.attempts
            converged = retry_result.success
            blocking = [e for e in retry_result.errors if e.severity.value == "error"]

        yaml_match = _re.match(r"^---\n(.*?)---\n", document, _re.DOTALL)
        if yaml_match:
            try:
                final_merged = yaml.safe_load(yaml_match.group(1)) or merged
            except Exception:
                final_merged = merged
        else:
            final_merged = merged

        generated_field_names = [k for k in final_merged if k not in existing_field_names]

        if dry_run:
            print("---")
            print(yaml.dump(final_merged, default_flow_style=False, allow_unicode=True), end="")
            print("---")
            return EnrichResult(
                success=not blocking, path=file_path,
                status="enriched" if not blocking else "failed",
                attempts=total_attempts, existing_fields=existing_field_names,
                generated_fields=generated_field_names,
                generation_id=generation_id, errors=blocking,
            )

        write_target = (Path(output) / file_path.name) if output else file_path
        if output:
            Path(output).mkdir(parents=True, exist_ok=True)

        status = "failed"
        if converged or not blocking:
            write_back(write_target, final_merged, body)
            status = "enriched"

        if not dry_run and self.writer is not None:
            self.writer.write(EnrichEvent(
                generation_id=generation_id, file=str(file_path),
                schema_version="1.0.0", existing_fields=existing_field_names,
                generated_fields=generated_field_names, attempts=total_attempts,
                converged=converged, skipped=False, skip_reason="",
                model=provider.model_name, temperature=0.0,
            ))

        return EnrichResult(
            success=(status == "enriched"), path=file_path, status=status,
            attempts=total_attempts, existing_fields=existing_field_names,
            generated_fields=generated_field_names,
            generation_id=generation_id, errors=blocking,
        )

    def enrich_dir(
        self,
        path: "str | Path",
        force: bool = False,
        dry_run: bool = False,
        output: "str | Path | None" = None,
        model: "str | None" = None,
    ) -> "list[EnrichResult]":
        """Enrich all .md files in directory recursively."""
        return [
            self.enrich(path=f, force=force, dry_run=dry_run, output=output, model=model)
            for f in sorted(Path(path).rglob("*.md"))
        ]

