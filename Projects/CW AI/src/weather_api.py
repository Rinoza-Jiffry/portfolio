from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import pandas as pd

try:
    from .config import APIS, PATHS
except ImportError:
    from config import APIS, PATHS

log = logging.getLogger(__name__)

def get_current_and_forecast_weather() -> Dict[str, float]:
    try:
        import openmeteo_requests
        import requests_cache
        from retry_requests import retry

        cache_session  = requests_cache.CachedSession(
            str(PATHS["cache"]), expire_after=APIS["cache_ttl_sec"]
        )
        retry_session  = retry(
            cache_session,
            retries=APIS["max_retries"],
            backoff_factor=APIS["backoff_factor"],
        )
        client = openmeteo_requests.Client(session=retry_session)

        params = {
            "latitude":     APIS["colombo_lat"],
            "longitude":    APIS["colombo_lon"],
            "current":      ["precipitation"],
            "hourly":       ["precipitation"],
            "timezone":     APIS["timezone"],
            "forecast_days": 1,
        }

        responses = client.weather_api(APIS["openmeteo_base"], params=params)
        resp      = responses[0]

        current_rain = float(resp.Current().Variables(0).Value())
        hourly       = resp.Hourly()
        forecast     = float(hourly.Variables(0).ValuesAsNumpy()[1])

        log.info(
            "[WEATHER] Live: current=%.2f mm, forecast_1h=%.2f mm",
            current_rain, forecast,
        )
        return {
            "current_rainfall_mm": current_rain,
            "forecast_1h_mm":      forecast,
            "source":              "api",
        }

    except Exception as exc:
        log.warning("[WEATHER] API call failed (%s) — using historical fallback.", exc)
        return _historical_fallback()

def _historical_fallback() -> Dict[str, float]:
    try:
        now  = datetime.now(timezone.utc)
        path = Path(str(PATHS["weather_clean"]))
        df   = pd.read_csv(path, parse_dates=["datetime"])

        mask = (df["month"] == now.month) & (df["hour"] == now.hour)
        sub  = df[mask]
        if sub.empty:
            sub = df

        sample = sub.sample(1, random_state=now.day).iloc[0]
        current_rain = float(sample.get("rainfall_mm", 0.0))
        forecast     = float(sample.get("rainfall_mm", 0.0))

        log.info(
            "[WEATHER] Historical fallback: current=%.2f mm (month=%d, hour=%d)",
            current_rain, now.month, now.hour,
        )
        return {
            "current_rainfall_mm": current_rain,
            "forecast_1h_mm":      forecast,
            "source":              "historical_fallback",
        }
    except Exception as exc:
        log.error("[WEATHER] Historical fallback also failed: %s", exc)
        return {
            "current_rainfall_mm": 0.0,
            "forecast_1h_mm":      0.0,
            "source":              "default",
        }

def weather_from_scenario(scenario_weather: dict) -> Dict[str, float]:
    return {
        "current_rainfall_mm": float(scenario_weather.get("current_rainfall_mm", 0.0)),
        "forecast_1h_mm":      float(scenario_weather.get("forecast_1h_mm", 0.0)),
        "source":              "scenario",
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    weather = get_current_and_forecast_weather()
    print(f"Current rainfall : {weather['current_rainfall_mm']:.1f} mm")
    print(f"1-hour forecast  : {weather['forecast_1h_mm']:.1f} mm")
    print(f"Source           : {weather['source']}")
