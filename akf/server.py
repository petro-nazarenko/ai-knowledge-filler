from __future__ import annotations

import os
import threading
import time
import uuid
from pathlib import Path
from typing import Optional, Generator

from fastapi import FastAPI, Depends, HTTPException, Request, Security, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from logger import get_logger
from akf.pipeline import Pipeline, GenerateResult, ValidateResult

# ─── AUTH ─────────────────────────────────────────────────────────────────────

_LOG_LEVEL = os.getenv("AKF_LOG_LEVEL", "INFO")
_JSON_LOGS = os.getenv("AKF_LOG_JSON", "true").strip().lower() not in {"0", "false", "no"}
_MAX_REQUEST_BYTES = int(os.getenv("AKF_MAX_REQUEST_BYTES", str(1_048_576)))
_MAX_CONCURRENCY = int(os.getenv("AKF_MAX_CONCURRENCY", "8"))
_DEFAULT_RATE_LIMIT = os.getenv("AKF_RATE_LIMIT_DEFAULT", "60/minute")
_RATE_LIMIT_GENERATE = os.getenv("AKF_RATE_LIMIT_GENERATE", "10/minute")
_RATE_LIMIT_VALIDATE = os.getenv("AKF_RATE_LIMIT_VALIDATE", "30/minute")
_RATE_LIMIT_BATCH = os.getenv("AKF_RATE_LIMIT_BATCH", "3/minute")
_RATE_LIMIT_ASK = os.getenv("AKF_RATE_LIMIT_ASK", "10/minute")
_OUTPUT_BASE = Path(os.getenv("AKF_OUTPUT_DIR", "./output")).expanduser().resolve()

_security = HTTPBearer(auto_error=False)
_logger = get_logger("akf.server", level=_LOG_LEVEL, json_output=_JSON_LOGS)


def _api_key() -> str:
    return os.getenv("AKF_API_KEY", "").strip()


def _env() -> str:
    return os.getenv("AKF_ENV", "dev").strip().lower()


def _is_prod() -> bool:
    return _env() == "prod"


def verify_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_security),
) -> None:
    """Require bearer token in prod; optional in dev unless key is configured."""
    key = _api_key()
    if not _is_prod() and not key:
        return
    if not key:
        raise HTTPException(status_code=503, detail="AKF_API_KEY must be configured")
    if credentials is None or credentials.credentials != key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ─── RATE LIMITING ────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=[_DEFAULT_RATE_LIMIT])

# ─── APP ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="AKF API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.state.ready = False
app.state.concurrency_semaphore = threading.BoundedSemaphore(_MAX_CONCURRENCY)
app.state.metrics_lock = threading.Lock()
app.state.metrics = {
    "started_at": int(time.time()),
    "requests_total": 0,
    "requests_by_path": {},
    "status_codes": {},
    "latency_ms_sum": 0,
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("AKF_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

_pipeline = None
_telemetry_writer = None


def _safe_output_path(output: Optional[str]) -> Optional[str]:
    if not output:
        return None
    candidate = Path(output).expanduser()
    resolved = (_OUTPUT_BASE / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if resolved != _OUTPUT_BASE and _OUTPUT_BASE not in resolved.parents:
        raise HTTPException(status_code=400, detail="Output path must stay inside AKF_OUTPUT_DIR")
    return str(resolved)


def _update_metrics(path: str, status_code: int, latency_ms: int) -> None:
    with app.state.metrics_lock:
        app.state.metrics["requests_total"] += 1
        app.state.metrics["latency_ms_sum"] += latency_ms
        by_path = app.state.metrics["requests_by_path"]
        by_path[path] = by_path.get(path, 0) + 1
        codes = app.state.metrics["status_codes"]
        code_key = str(status_code)
        codes[code_key] = codes.get(code_key, 0) + 1


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.monotonic()

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > _MAX_REQUEST_BYTES:
        response = Response(status_code=413, content="Request body too large")
        response.headers["X-Request-ID"] = request_id
        _update_metrics(request.url.path, response.status_code, 0)
        return response

    response = await call_next(request)
    latency_ms = int((time.monotonic() - start) * 1000)
    _update_metrics(request.url.path, response.status_code, latency_ms)
    response.headers["X-Request-ID"] = request_id
    _logger.info(
        "request_complete",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms,
        },
    )
    return response


def _acquire_concurrency_slot() -> Generator[None, None, None]:
    sem = app.state.concurrency_semaphore
    if not sem.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Server is busy, try again later")
    try:
        yield
    finally:
        sem.release()


@app.on_event("startup")
def _startup_checks() -> None:
    if _is_prod() and not _api_key():
        raise RuntimeError("AKF_API_KEY is required when AKF_ENV=prod")
    origins = os.getenv("AKF_CORS_ORIGINS", "http://localhost:3000").split(",")
    if _is_prod() and "*" in [o.strip() for o in origins]:
        raise RuntimeError("Wildcard CORS is not allowed when AKF_ENV=prod")
    get_pipeline()
    app.state.ready = True


@app.on_event("shutdown")
def _shutdown_cleanup() -> None:
    global _pipeline, _telemetry_writer
    app.state.ready = False
    _pipeline = None
    _telemetry_writer = None


def get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline(
            output=os.getenv("AKF_OUTPUT_DIR", "./output"),
            verbose=False,
        )
    return _pipeline


def get_telemetry_writer():
    global _telemetry_writer
    if _telemetry_writer is None:
        from akf.telemetry import TelemetryWriter

        path = Path(os.getenv("AKF_TELEMETRY_PATH", "telemetry/events.jsonl"))
        _telemetry_writer = TelemetryWriter(path=path)
    return _telemetry_writer


def _extract_tenant_id(request: Request) -> str:
    """Resolve tenant id from headers for usage analytics/billing prep."""
    return (
        request.headers.get("X-AKF-Tenant-ID")
        or request.headers.get("X-Tenant-ID")
        or os.getenv("AKF_DEFAULT_TENANT", "default")
    )


# ─── SCHEMAS ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    output: Optional[str] = None
    model: Optional[str] = None


class GenerateResponse(BaseModel):
    success: bool
    path: Optional[str]
    content: Optional[str]
    attempts: int
    errors: list[str]
    generation_id: str
    duration_ms: int


class ValidateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100_000)
    strict: bool = False


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]


class BatchRequest(BaseModel):
    prompts: list[str] = Field(..., max_length=20)
    output: Optional[str] = None
    model: Optional[str] = None


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    model: str = Field(default="auto")
    no_llm: bool = False
    max_distance: Optional[float] = Field(default=None, ge=0)


class AskHit(BaseModel):
    chunk_id: str
    content: str
    metadata: dict
    distance: float


class AskResponse(BaseModel):
    mode: str
    query: str
    top_k: int
    answer: Optional[str] = None
    sources: list[str] = Field(default_factory=list)
    hits_used: int = 0
    hits: list[AskHit] = Field(default_factory=list)
    model: str
    insufficient_context: bool = False


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0", "env": _env()}


@app.get("/ready")
def ready():
    if not app.state.ready:
        try:
            get_pipeline()
            app.state.ready = True
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Service is not ready: {exc}") from exc
    return {"status": "ready"}


@app.get("/metrics")
def metrics():
    with app.state.metrics_lock:
        requests_total = app.state.metrics["requests_total"]
        latency_sum = app.state.metrics["latency_ms_sum"]
        avg_latency = int(latency_sum / requests_total) if requests_total else 0
        return {
            "started_at": app.state.metrics["started_at"],
            "requests_total": requests_total,
            "requests_by_path": dict(app.state.metrics["requests_by_path"]),
            "status_codes": dict(app.state.metrics["status_codes"]),
            "latency_ms_avg": avg_latency,
            "max_request_bytes": _MAX_REQUEST_BYTES,
            "max_concurrency": _MAX_CONCURRENCY,
        }


@app.get("/v1/models", dependencies=[Depends(verify_key)])
def models():
    from llm_providers import list_providers
    return {"providers": list_providers()}


@app.post("/v1/generate", response_model=GenerateResponse, dependencies=[Depends(verify_key)])
@limiter.limit(_RATE_LIMIT_GENERATE)
def generate(request: Request, req: GenerateRequest, _: None = Depends(_acquire_concurrency_slot)):
    safe_output = _safe_output_path(req.output)
    result = get_pipeline().generate(
        prompt=req.prompt,
        output=safe_output,
        model=req.model,
    )
    return GenerateResponse(
        success=result.success,
        path=str(result.file_path) if result.file_path else None,
        content=result.content,
        attempts=result.attempts,
        errors=[str(e) for e in result.errors],
        generation_id=result.generation_id,
        duration_ms=result.duration_ms,
    )


@app.post("/v1/validate", response_model=ValidateResponse, dependencies=[Depends(verify_key)])
@limiter.limit(_RATE_LIMIT_VALIDATE)
def validate(request: Request, req: ValidateRequest, _: None = Depends(_acquire_concurrency_slot)):
    from akf.validator import validate as _validate
    from akf.validation_error import Severity
    all_errors = _validate(req.content)
    if req.strict:
        errors = [str(e) for e in all_errors]
        warnings: list[str] = []
    else:
        errors = [str(e) for e in all_errors if e.severity == Severity.ERROR]
        warnings = [str(e) for e in all_errors if e.severity == Severity.WARNING]
    return ValidateResponse(valid=len(errors) == 0, errors=errors, warnings=warnings)


@app.post("/v1/batch", dependencies=[Depends(verify_key)])
@limiter.limit(_RATE_LIMIT_BATCH)
def batch(request: Request, req: BatchRequest, _: None = Depends(_acquire_concurrency_slot)):
    safe_output = _safe_output_path(req.output)
    results = get_pipeline().batch_generate(
        prompts=req.prompts,
        output=safe_output,
        model=req.model,
    )
    return {
        "total": len(results),
        "success": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "results": [
            {
                "success": r.success,
                "path": str(r.file_path) if r.file_path else None,
                "attempts": r.attempts,
                "errors": [str(e) for e in r.errors],
                "generation_id": r.generation_id,
                "duration_ms": r.duration_ms,
            }
            for r in results
        ],
    }


@app.post("/v1/ask", response_model=AskResponse, dependencies=[Depends(verify_key)])
@limiter.limit(_RATE_LIMIT_ASK)
def ask(request: Request, req: AskRequest, _: None = Depends(_acquire_concurrency_slot)):
    """RAG question answering endpoint.

    Modes:
      - no_llm=False (default): retrieve + synthesize answer with LLM
      - no_llm=True: retrieval-only, returns top-k hits without LLM
    """
    t_start = time.monotonic()
    mode = "retrieval-only" if req.no_llm else "synthesis"
    tenant_id = _extract_tenant_id(request)

    try:
        if req.no_llm:
            from rag.retriever import retrieve
            from akf.telemetry import AskQueryEvent, new_generation_id

            retrieval = retrieve(query=req.query, top_k=req.top_k)
            hits_raw = retrieval.hits
            if req.max_distance is not None:
                hits_raw = [hit for hit in hits_raw if hit.distance <= req.max_distance]

            hits = [
                AskHit(
                    chunk_id=h.chunk_id,
                    content=h.content,
                    metadata=h.metadata,
                    distance=h.distance,
                )
                for h in hits_raw
            ]
            response = AskResponse(
                mode="retrieval-only",
                query=retrieval.query,
                top_k=retrieval.top_k,
                hits_used=len(hits),
                hits=hits,
                model="none",
                insufficient_context=(len(hits) == 0),
            )

            try:
                get_telemetry_writer().write(
                    AskQueryEvent(
                        generation_id=new_generation_id(),
                        tenant_id=tenant_id,
                        mode=mode,
                        model="none",
                        top_k=req.top_k,
                        no_llm=req.no_llm,
                        max_distance=req.max_distance,
                        hits_used=response.hits_used,
                        insufficient_context=response.insufficient_context,
                        duration_ms=int((time.monotonic() - t_start) * 1000),
                    )
                )
            except Exception:
                pass

            return response

        from rag.copilot import answer_question
        from akf.telemetry import AskQueryEvent, new_generation_id

        result = answer_question(
            query=req.query,
            top_k=req.top_k,
            model=req.model,
            max_distance=req.max_distance,
        )
        response = AskResponse(
            mode="synthesis",
            query=result.query,
            top_k=result.top_k,
            answer=result.answer,
            sources=result.sources,
            hits_used=result.hits_used,
            model=result.model,
            insufficient_context=result.insufficient_context,
        )

        try:
            get_telemetry_writer().write(
                AskQueryEvent(
                    generation_id=new_generation_id(),
                    tenant_id=tenant_id,
                    mode=mode,
                    model=response.model,
                    top_k=req.top_k,
                    no_llm=req.no_llm,
                    max_distance=req.max_distance,
                    hits_used=response.hits_used,
                    insufficient_context=response.insufficient_context,
                    duration_ms=int((time.monotonic() - t_start) * 1000),
                )
            )
        except Exception:
            pass

        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG ask failed: {exc}") from exc
