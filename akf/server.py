from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from akf.pipeline import Pipeline, GenerateResult, ValidateResult

# ─── AUTH ─────────────────────────────────────────────────────────────────────

_AKF_API_KEY = os.getenv("AKF_API_KEY")
_security = HTTPBearer(auto_error=False)


def verify_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_security),
) -> None:
    """Require Bearer token if AKF_API_KEY is set. Skip auth if key not configured."""
    if not _AKF_API_KEY:
        return  # auth disabled — local/dev mode
    if credentials is None or credentials.credentials != _AKF_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ─── RATE LIMITING ────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# ─── APP ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="AKF API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("AKF_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

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
    return {"status": "ok", "version": "1.0.0"}


@app.get("/v1/models", dependencies=[Depends(verify_key)])
def models():
    from llm_providers import list_providers
    return {"providers": list_providers()}


@app.post("/v1/generate", response_model=GenerateResponse, dependencies=[Depends(verify_key)])
@limiter.limit("10/minute")
def generate(request: Request, req: GenerateRequest):
    result = get_pipeline().generate(
        prompt=req.prompt,
        output=req.output,
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
@limiter.limit("30/minute")
def validate(request: Request, req: ValidateRequest):
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
@limiter.limit("3/minute")
def batch(request: Request, req: BatchRequest):
    results = get_pipeline().batch_generate(
        prompts=req.prompts,
        output=req.output,
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
@limiter.limit("10/minute")
def ask(request: Request, req: AskRequest):
    """RAG question answering endpoint.

    Modes:
      - no_llm=False (default): retrieve + synthesize answer with LLM
      - no_llm=True: retrieval-only, returns top-k hits without LLM
    """
    t_start = time.monotonic()
    mode = "retrieval-only" if req.no_llm else "synthesis"

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
