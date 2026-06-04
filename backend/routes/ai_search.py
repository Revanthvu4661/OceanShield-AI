from __future__ import annotations

from fastapi import APIRouter, HTTPException

from agent import run_agentic_research
from schemas import AISearchRequest, AISearchResponse


router = APIRouter()


@router.post("/ai-search", response_model=AISearchResponse)
def ai_search(payload: AISearchRequest) -> dict:
    try:
        result = run_agentic_research(payload.query)
        result["query"] = payload.query
        return result
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": "Gemini API error", "detail": str(exc)})
