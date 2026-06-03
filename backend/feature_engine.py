from __future__ import annotations

import math
from typing import Any

from schemas import OceanInput


PERIOD_MEDIAN = 8.0
GUST_MEDIAN = 20.0
PRESSURE_MEAN = 1013.25


def _angle_gap(a: float, b: float) -> float:
    return abs(((a - b + 180.0) % 360.0) - 180.0)


def engineer_single(payload: OceanInput) -> dict[str, Any]:
    temperature = (payload.maxtemp + payload.mintemp) / 2.0
    direction_gap = _angle_gap(payload.winddirdegree, payload.swelldir)
    tide_midpoint = (payload.tide_height_max + payload.tide_height_min) / 2.0
    tide_range = payload.tide_height_range if payload.tide_height_range else 1.0

    engineered = {
        "windspeed": payload.windspeed,
        "winddirdegree": payload.winddirdegree,
        "precipitation": payload.precipitation,
        "humidity": payload.humidity,
        "pressure": payload.pressure,
        "cloudcover": payload.cloudcover,
        "dewpoint": payload.dewpoint,
        "windgust": payload.windgust,
        "sigheight": payload.sigheight,
        "swellheight": payload.swellheight,
        "swelldir": payload.swelldir,
        "period": payload.period,
        "watertemp": payload.watertemp,
        "moon_illumination": payload.moon_illumination,
        "moon_phase": payload.moon_phase,
        "maxtemp": payload.maxtemp,
        "mintemp": payload.mintemp,
        "tide_events": payload.tide_events,
        "tide_height_mean": payload.tide_height_mean,
        "tide_height_max": payload.tide_height_max,
        "tide_height_min": payload.tide_height_min,
        "tide_height_range": payload.tide_height_range,
        "high_tide_count": payload.high_tide_count,
        "low_tide_count": payload.low_tide_count,
        "idbeach": str(payload.idbeach),
        "hour": payload.hour,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "temperature": temperature,
        "hour_sin": math.sin(2 * math.pi * payload.hour / 24.0),
        "hour_cos": math.cos(2 * math.pi * payload.hour / 24.0),
        "daylight_flag": 1 if 6 <= payload.hour <= 18 else 0,
        "daily_temp_range": payload.maxtemp - payload.mintemp,
        "temperature_vs_daily_max": payload.maxtemp - temperature,
        "temperature_vs_daily_min": temperature - payload.mintemp,
        "dewpoint_depression": temperature - payload.dewpoint,
        "precipitation_log": math.log1p(max(payload.precipitation, 0.0)),
        "cloud_humidity_interaction": (payload.cloudcover / 100.0) * (payload.humidity / 100.0),
        "wind_vector_x": math.cos(math.radians(payload.winddirdegree)) * payload.windspeed,
        "wind_vector_y": math.sin(math.radians(payload.winddirdegree)) * payload.windspeed,
        "swell_vector_x": math.cos(math.radians(payload.swelldir)) * payload.swellheight,
        "swell_vector_y": math.sin(math.radians(payload.swelldir)) * payload.swellheight,
        "directional_misalignment": direction_gap / 180.0,
        "wind_alignment": math.cos(math.radians(direction_gap)),
        "gust_factor": 0.0 if payload.windspeed == 0 else payload.windgust / payload.windspeed,
        "gust_delta": payload.windgust - payload.windspeed,
        "wind_intensity": 0.7 * payload.windspeed + 0.3 * payload.windgust,
        "wave_energy": (payload.sigheight**2) * payload.period,
        "wave_steepness": 0.0 if payload.period == 0 else payload.sigheight / payload.period,
        "wave_power_index": payload.sigheight * payload.swellheight * payload.period,
        "swell_ratio": 0.0 if payload.sigheight == 0 else payload.swellheight / payload.sigheight,
        "swell_energy": (payload.swellheight**2) * payload.period,
        "wave_severity": (
            0.40 * payload.sigheight
            + 0.25 * payload.swellheight
            + 0.20 * (payload.period / PERIOD_MEDIAN)
            + 0.15 * (payload.windgust / GUST_MEDIAN)
        ),
        "wave_wind_interaction": payload.sigheight * (0.7 * payload.windspeed + 0.3 * payload.windgust),
        "pressure_anomaly": payload.pressure - PRESSURE_MEAN,
        "pressure_drop_flag": 1 if (payload.pressure - PRESSURE_MEAN) <= -2 else 0,
        "lunar_energy_proxy": payload.moon_illumination / 100.0,
        "tide_height_normalized": 0.0 if tide_range == 0 else (payload.tide_height_mean - tide_midpoint) / tide_range,
        "tide_extreme_imbalance": payload.high_tide_count - payload.low_tide_count,
        "marine_risk_index": (
            0.28 * ((payload.sigheight**2) * payload.period)
            + 0.20 * (payload.sigheight * payload.swellheight * payload.period)
            + 0.15 * (0.7 * payload.windspeed + 0.3 * payload.windgust)
            + 0.12 * (0.0 if payload.windspeed == 0 else payload.windgust / payload.windspeed)
            + 0.10 * (direction_gap / 180.0)
            + 0.10 * payload.tide_height_range
            - 0.05 * (payload.pressure - PRESSURE_MEAN)
        ),
    }
    return engineered

