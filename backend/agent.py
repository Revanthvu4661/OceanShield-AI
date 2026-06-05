from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timezone
from typing import Any

from prediction_service import predict_ocean_state
from schemas import OceanInput
from settings import DEFAULT_GEMINI_MODEL, GEMINI_API_KEY


AGENT_SYSTEM_PROMPT = (
    "You are OceanShield's agentic maritime intelligence core. Use tools whenever the user asks about "
    "routes, safety, vessel movement, marine conditions, or risk assessment.\n\n"
    "Reason step-by-step with tools, but do not reveal hidden chain-of-thought. If the user asks whether a "
    "shipping route is safe, first inspect relevant locations or waypoints, then run risk prediction, and if "
    "risk is elevated or high, call suggest_alternative_route before answering.\n\n"
    "Return the final response in this structure:\n"
    "ANSWER: [clear operational answer, including a compact route comparison table when route advice is relevant]\n"
    "KEY POINTS:\n- point 1\n- point 2\n- point 3\n"
    "RISK FACTORS: [comma-separated list of notable risk factors]\n"
    "Keep answers concise, factual, and focused on maritime safety."
)

PORT_DIRECTORY: dict[str, tuple[float, float]] = {
    "mumbai": (18.9388, 72.8354),
    "aden": (12.7855, 45.0187),
    "colombo": (6.9271, 79.8612),
    "muscat": (23.5880, 58.3829),
    "salalah": (17.0190, 54.0924),
    "djibouti": (11.8251, 42.5903),
    "mombasa": (-4.0435, 39.6682),
    "kochi": (9.9312, 76.2673),
    "karachi": (24.8607, 67.0011),
    "dubai": (25.2048, 55.2708),
    "singapore": (1.3521, 103.8198),
    "suez": (30.0444, 31.2357),
    "perth": (-31.9505, 115.8605),
    "durban": (-29.8587, 31.0218),
    "hobart": (-42.8821, 147.3272),
    "cape town": (-33.9249, 18.4241),
}


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", value.lower())).strip()


def _hash_seed(*parts: Any) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:12], 16)


def _resolve_port(place: str) -> tuple[str, float, float]:
    normalized = _normalize_name(place)
    if normalized in PORT_DIRECTORY:
        lat, lon = PORT_DIRECTORY[normalized]
        return place.strip(), lat, lon

    for name, coords in PORT_DIRECTORY.items():
        if normalized in name or name in normalized:
            lat, lon = coords
            return name.title(), lat, lon

    coord_match = re.search(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", place)
    if coord_match:
        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))
        return place.strip(), lat, lon

    raise ValueError(
        f"Unknown route endpoint '{place}'. Use a known port name such as Mumbai, Aden, Colombo, Muscat, or coordinates."
    )


def _is_route_endpoint(place: str) -> bool:
    normalized = _normalize_name(place)
    if re.fullmatch(r"-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?", place.strip()):
        return True
    return normalized in PORT_DIRECTORY


def _moon_phase_from_illumination(illumination: float) -> str:
    if illumination < 12:
        return "New Moon"
    if illumination < 35:
        return "Waxing Crescent"
    if illumination < 48:
        return "First Quarter"
    if illumination < 70:
        return "Waxing Gibbous"
    if illumination < 88:
        return "Full Moon"
    if illumination < 97:
        return "Waning Gibbous"
    return "Last Quarter"


def _synthetic_conditions(lat: float, lon: float, reference_hour: int | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    hour = int(reference_hour if reference_hour is not None else now.hour)
    day_of_year = now.timetuple().tm_yday
    seed = _hash_seed(lat, lon, hour, day_of_year)
    seed_mod = (seed % 1000) / 1000.0
    lat_abs = abs(lat)
    lon_abs = abs(lon)
    day_wave = math.sin(2 * math.pi * day_of_year / 365.25)
    hour_wave = math.sin(2 * math.pi * hour / 24.0)
    geo_pressure = 1016.5 - lat_abs * 0.12 - seed_mod * 1.8 + day_wave * 1.3
    sigheight = max(0.3, 0.6 + lat_abs / 34.0 + seed_mod * 0.9 + abs(hour_wave) * 0.25)
    swellheight = max(0.25, sigheight * (0.78 + seed_mod * 0.18))
    windspeed = max(3.0, 7.5 + lat_abs / 5.5 + seed_mod * 12.0 + abs(hour_wave) * 2.5)
    windgust = windspeed + 4.0 + seed_mod * 8.0
    winddirdegree = float((lon_abs * 4.0 + hour * 14.0 + seed_mod * 180.0) % 360.0)
    swelldir = float((winddirdegree + 45 + seed_mod * 50.0) % 360.0)
    pressure = round(geo_pressure, 1)
    humidity = max(35.0, min(98.0, 68.0 + seed_mod * 22.0 - lat_abs * 0.15))
    cloudcover = max(5.0, min(100.0, 38.0 + seed_mod * 38.0 + abs(day_wave) * 18.0))
    precipitation = max(0.0, round(seed_mod * 1.8 + max(0.0, (humidity - 80.0) / 28.0), 1))
    maxtemp = max(-5.0, 29.0 - lat_abs * 0.22 + day_wave * 3.0)
    mintemp = max(-10.0, maxtemp - 5.5 - seed_mod * 3.5)
    watertemp = max(0.0, maxtemp - 4.0 + seed_mod * 2.2)
    dewpoint = max(-10.0, maxtemp - (100.0 - humidity) / 5.0)
    tide_height_mean = round(0.4 + seed_mod * 0.7 + abs(day_wave) * 0.2, 2)
    tide_height_max = round(tide_height_mean + 0.55 + seed_mod * 0.45, 2)
    tide_height_min = round(tide_height_mean - 0.55 - seed_mod * 0.35, 2)
    tide_height_range = round(tide_height_max - tide_height_min, 2)
    tide_events = 4 + int(seed_mod * 2)
    high_tide_count = max(1, int(round(2 + seed_mod * 2)))
    low_tide_count = max(1, int(round(2 + (1 - seed_mod) * 1.5)))
    moon_illumination = round(40.0 + seed_mod * 55.0)

    return {
        "windspeed": round(windspeed, 1),
        "winddirdegree": round(winddirdegree, 1),
        "precipitation": precipitation,
        "humidity": round(humidity, 1),
        "pressure": pressure,
        "cloudcover": round(cloudcover, 1),
        "dewpoint": round(dewpoint, 1),
        "windgust": round(windgust, 1),
        "sigheight": round(sigheight, 2),
        "swellheight": round(swellheight, 2),
        "swelldir": round(swelldir, 1),
        "period": round(max(4.0, 6.0 + sigheight * 1.7 + seed_mod * 3.5), 1),
        "watertemp": round(watertemp, 1),
        "moon_illumination": moon_illumination,
        "moon_phase": _moon_phase_from_illumination(moon_illumination),
        "maxtemp": round(maxtemp, 1),
        "mintemp": round(mintemp, 1),
        "tide_events": tide_events,
        "tide_height_mean": tide_height_mean,
        "tide_height_max": tide_height_max,
        "tide_height_min": tide_height_min,
        "tide_height_range": tide_height_range,
        "high_tide_count": high_tide_count,
        "low_tide_count": low_tide_count,
        "idbeach": str(1000 + int(abs(lat) * 10) + int(abs(lon) * 10)),
        "hour": hour,
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "conditions_source": "synthetic marine estimate",
        "estimate_confidence": round(max(0.5, 0.88 - seed_mod * 0.12), 2),
    }


def get_current_conditions(lat: float, lon: float, reference_hour: int | None = None) -> dict[str, Any]:
    """Estimate marine conditions at a geographic point for the agent loop."""
    return _synthetic_conditions(lat, lon, reference_hour=reference_hour)


def run_risk_prediction(conditions: OceanInput | dict[str, Any]) -> dict[str, Any]:
    """Wrap the trained XGBoost model and return a normalized risk assessment."""
    payload = conditions if isinstance(conditions, OceanInput) else OceanInput.model_validate(conditions)
    result = predict_ocean_state(payload)
    return {
        key: value
        for key, value in result.items()
        if key in {"risk_score", "risk_label", "risk_level", "probability", "top_factors", "latitude", "longitude"}
    } | {
        "top_factors": [factor.model_dump() for factor in result["top_factors"]],
    }


def _interpolate_waypoints(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    samples: int = 5,
    arc_offset: float = 0.0,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for idx in range(samples):
        t = idx / max(samples - 1, 1)
        lat = start_lat + (end_lat - start_lat) * t
        lon = start_lon + (end_lon - start_lon) * t
        if arc_offset:
            bend = math.sin(math.pi * t) * arc_offset
            lat += bend
            lon += math.cos(math.pi * t) * arc_offset * 0.3
        points.append((round(lat, 4), round(lon, 4)))
    return points


def _evaluate_route(route_name: str, waypoints: list[tuple[float, float]], risk_threshold: float) -> dict[str, Any]:
    evaluations: list[dict[str, Any]] = []
    for index, (lat, lon) in enumerate(waypoints, start=1):
        conditions = get_current_conditions(lat, lon)
        prediction = run_risk_prediction(conditions)
        evaluations.append(
            {
                "waypoint": f"{route_name} #{index}",
                "latitude": lat,
                "longitude": lon,
                "risk_score": prediction["risk_score"],
                "risk_level": prediction["risk_level"],
                "probability": prediction["probability"],
                "top_factor": prediction["top_factors"][0].feature if prediction["top_factors"] else "n/a",
            }
        )

    average_risk = sum(item["risk_score"] for item in evaluations) / len(evaluations)
    peak_risk = max(item["risk_score"] for item in evaluations)
    high_risk_waypoints = sum(1 for item in evaluations if item["risk_score"] >= risk_threshold)

    return {
        "route_name": route_name,
        "average_risk_score": round(average_risk, 2),
        "peak_risk_score": round(peak_risk, 2),
        "high_risk_waypoints": high_risk_waypoints,
        "status": "HIGH RISK" if peak_risk >= risk_threshold else "CAUTION" if average_risk >= 35 else "SAFE",
        "waypoints": evaluations,
    }


def suggest_alternative_route(start: str, end: str, risk_threshold: float = 65.0) -> dict[str, Any]:
    """Evaluate the requested route and recommend safer alternatives."""
    start_name, start_lat, start_lon = _resolve_port(start)
    end_name, end_lat, end_lon = _resolve_port(end)

    deltas = [
        ("Direct route", 0.0),
        ("Northern detour", 4.0),
        ("Southern detour", -4.0),
    ]
    alternatives = [
        _evaluate_route(
            route_name,
            _interpolate_waypoints(start_lat, start_lon, end_lat, end_lon, samples=5, arc_offset=offset),
            risk_threshold,
        )
        for route_name, offset in deltas
    ]
    recommended = min(alternatives, key=lambda item: (item["peak_risk_score"], item["average_risk_score"]))

    comparison_table = [
        {
            "route": item["route_name"],
            "average_risk_score": item["average_risk_score"],
            "peak_risk_score": item["peak_risk_score"],
            "high_risk_waypoints": item["high_risk_waypoints"],
            "status": item["status"],
        }
        for item in alternatives
    ]

    return {
        "start": start_name,
        "end": end_name,
        "risk_threshold": risk_threshold,
        "recommended_route": recommended["route_name"],
        "comparison_table": comparison_table,
        "alternatives": alternatives,
        "route_summary": (
            f"Recommended route: {recommended['route_name']} because it has the lowest peak risk "
            f"({recommended['peak_risk_score']:.2f}) and average risk ({recommended['average_risk_score']:.2f})."
        ),
    }


def _extract_route_pair(query: str) -> tuple[str, str] | None:
    patterns = [
        r"(?:route|route\s+advice|route\s+check|voyage|sailing|passage|shipping\s+lane)\s+(.+?)\s+to\s+(.+?)(?:\?|$)",
        r"from\s+(.+?)\s+to\s+(.+?)(?:\s+safe|\s+dangerous|\s+this\s+week|\?|$)",
        r"(.+?)\s+to\s+(.+?)(?:\s+safe|\s+dangerous|\s+this\s+week|\?|$)",
    ]
    for pattern in patterns:
        route_match = re.search(pattern, query, re.I)
        if not route_match:
            continue
        start = route_match.group(1).strip(" ,.?")
        end = route_match.group(2).strip(" ,.?")
        if _is_route_endpoint(start) and _is_route_endpoint(end):
            return start, end

    normalized_query = _normalize_name(query)
    if " to " in normalized_query:
        port_hits: list[tuple[int, str]] = []
        for port_name in PORT_DIRECTORY:
            match = re.search(rf"\b{re.escape(port_name)}\b", normalized_query)
            if match:
                port_hits.append((match.start(), port_name.title()))
        port_hits.sort(key=lambda item: item[0])
        if len(port_hits) >= 2:
            start = port_hits[0][1]
            end = port_hits[1][1]
            return start, end

    return None


def _parse_agent_text(text: str) -> dict[str, Any]:
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
        "sources_note": "Based on oceanographic reasoning, route evaluation tools, and the trained risk model",
    }


def _format_route_advice(start: str, end: str) -> dict[str, Any]:
    advice = suggest_alternative_route(start, end)
    return advice


def _dispatch_tool(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "get_current_conditions":
        return get_current_conditions(**args)
    if tool_name == "run_risk_prediction":
        return run_risk_prediction(args.get("conditions", args))
    if tool_name == "suggest_alternative_route":
        return suggest_alternative_route(**args)
    raise ValueError(f"Unknown tool requested by Gemini: {tool_name}")


def run_agentic_research(query: str, gemini_api_key: str | None = None, model_name: str = DEFAULT_GEMINI_MODEL) -> dict[str, Any]:
    """Execute the Gemini tool loop until a final, grounded answer is produced."""
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "The Gemini agent loop requires the `google-genai` package. Install backend requirements before using AI search."
        ) from exc

    api_key = (gemini_api_key or GEMINI_API_KEY).strip()
    if not api_key:
        raise RuntimeError(
            "Gemini API key is not configured. Set GEMINI_API_KEY in the backend environment."
        )

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=AGENT_SYSTEM_PROMPT,
        tools=[get_current_conditions, run_risk_prediction, suggest_alternative_route],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.2,
        max_output_tokens=900,
    )

    history: list[Any] = [types.Content(role="user", parts=[types.Part(text=query)])]
    tool_trace: list[dict[str, Any]] = []
    route_pair = _extract_route_pair(query)

    for _ in range(8):
        response = client.models.generate_content(model=model_name, contents=history, config=config)
        if not response.candidates:
            break

        content = response.candidates[0].content
        function_calls = [part.function_call for part in content.parts if getattr(part, "function_call", None)]
        if not function_calls:
            parsed = _parse_agent_text(response.text or "")
            parsed["query"] = query
            parsed["tool_trace"] = tool_trace
            if route_pair:
                parsed["route_request"] = {"start": route_pair[0], "end": route_pair[1]}
                route_advice = _format_route_advice(route_pair[0], route_pair[1])
                parsed["route_advice"] = route_advice
                parsed["answer"] = f"{parsed['answer']}\n\n{route_advice['route_summary']}"
            return parsed

        history.append(content)
        for function_call in function_calls:
            args = dict(function_call.args or {})
            if function_call.name == "suggest_alternative_route" and route_pair:
                args.setdefault("start", route_pair[0])
                args.setdefault("end", route_pair[1])
            result = _dispatch_tool(function_call.name, args)
            tool_trace.append(
                {
                    "tool_name": function_call.name,
                    "arguments": args,
                    "result": result,
                }
            )
            history.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=function_call.name,
                            response=result,
                        )
                    ],
                )
            )

    raise RuntimeError("Gemini agent loop exceeded the maximum number of tool turns.")
