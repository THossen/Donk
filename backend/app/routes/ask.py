"""Ask endpoint: question validation, SSE streaming, model health."""
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import context as ctx
from ..llm_service import ModelService
from ..services.investigate import _ask_event_stream

router = APIRouter()


class AskBody(BaseModel):
    question: str


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.post("/api/ask")
def ask(body: AskBody):
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="question too long")
    ctx.store.record_question(question, ctx.settings.repo_path)
    return StreamingResponse(
        (_sse(e) for e in _ask_event_stream(question)),
        media_type="text/event-stream",
    )


@router.get("/api/history")
def get_history(limit: int = 20):
    limit = max(1, min(limit, 100))
    return {"questions": ctx.store.list_questions(limit)}


@router.delete("/api/history/{qid}")
def delete_history_item(qid: int):
    if not ctx.store.delete_question(qid):
        raise HTTPException(status_code=404, detail="unknown question")
    return {"deleted": qid}


@router.delete("/api/history")
def clear_history():
    return {"deleted": ctx.store.clear_questions()}


@router.get("/api/health/model")
def model_health():
    if not ctx.settings.model_configured:
        raise HTTPException(status_code=503, detail="model not configured")
    try:
        return ModelService(ctx.settings).health_check()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"model request failed: {str(e)[:200]}")
