from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException

from settings import DEFAULT_GEMINI_MODEL
from schemas import AISearchRequest, AISearchResponse


router = APIRouter()
SYSTEM_PROMPT = (
    "You are OceanShield AI's maritime research assistant. You specialise in rogue wave science, "
    "oceanographic risk, maritime safety, and shipping route hazards. Answer the user's question clearly "
    "and factually. Structure your response as:\n"
    "ANSWER: [2-3 paragraph answer]\n"
    "KEY POINTS:\n- point 1\n- point 2\n- point 3\n"
    "RISK FACTORS: [comma-separated list of any ocean risk factors mentioned]\n\n"
    "Keep answers focused on maritime safety and oceanographic science."
)


def _parse_gemini_response(text: str) -> dict[str, Any]:
    answer = text.strip()
    key_points: list[str] = []
    risk_factors: list[str] = []

    answer_match = re.search(r"ANSWER:\s*(.*?)(?:\nKEY POINTS:|\nRISK FACTORS:|$)", text, re.S | re.I)
    if answer_match:
        answer = answer_match.group(1).strip()

    key_points_match = re.search(r"KEY POINTS:\s*(.*?)(?:\nRISK FACTORS:|$)", text, re.S | re.I)
    if key_points_match:
        raw_points = key_points_match.group(1)
        key_points = [line.strip("-• \t") for line in raw_points.splitlines() if line.strip()]

    risk_match = re.search(r"RISK FACTORS:\s*(.*)$", text, re.S | re.I)
    if risk_match:
        risk_factors = [item.strip() for item in re.split(r",|\n", risk_match.group(1)) if item.strip()]

    return {
        "answer": answer,
        "key_points": key_points[:5],
        "risk_factors": risk_factors[:8],
        "sources_note": "Based on oceanographic research and maritime safety literature",
    }


@router.post("/ai-search", response_model=AISearchResponse)
def ai_search(payload: AISearchRequest) -> dict:
    try:
        import google.generativeai as genai

        genai.configure(api_key=payload.gemini_api_key)
        model = genai.GenerativeModel(DEFAULT_GEMINI_MODEL)
        response = model.generate_content(
            f"{SYSTEM_PROMPT}\n\nUser question: {payload.query}",
            generation_config={"temperature": 0.3, "max_output_tokens": 600},
        )
        text = getattr(response, "text", None) or ""
        if not text.strip():
            text = str(response)
        parsed = _parse_gemini_response(text)
        parsed["query"] = payload.query
        return parsed
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": "Gemini API error", "detail": str(exc)})

