# app/tools/forecaster.py

import logging
import json
import re
import numpy as np
import pandas as pd
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def extract_time_series(text: str) -> list[dict]:
    """
    Find year→value patterns in text.
    Returns list of {label, years, values, unit, context}.
    """
    # Pattern: year followed by a value with optional unit
    year_value_pattern = re.compile(
        r"(?:in\s+|by\s+|for\s+)?(20\d{2}|19\d{2})"
        r"[,:\s]+(?:was|is|were|reached|stood\s+at|valued\s+at|estimated\s+at)?\s*"
        r"(?:USD\s*|INR\s*|Rs\.?\s*|\$)?"
        r"(\d+\.?\d*)\s*"
        r"(billion|million|trillion|thousand|%|percent|GW|MW|Mt|kWh|crore|lakh)?",
        re.IGNORECASE,
    )

    matches = []
    for m in year_value_pattern.finditer(text):
        year = int(m.group(1))
        try:
            value = float(m.group(2))
        except ValueError:
            continue
        unit = m.group(3) or ""
        start = max(0, m.start() - 80)
        end = min(len(text), m.end() + 80)
        context = text[start:end].replace("\n", " ").strip()

        matches.append({
            "year": year,
            "value": value,
            "unit": unit,
            "context": context,
        })

    # Group by unit (same unit likely = same time series)
    grouped: dict[str, list] = {}
    for m in matches:
        key = m["unit"].lower() or "value"
        grouped.setdefault(key, []).append(m)

    series_list = []
    for unit, points in grouped.items():
        if len(points) < 3:  # Need at least 3 data points to forecast
            continue
        points_sorted = sorted(points, key=lambda x: x["year"])

        # Deduplicate years
        seen_years: set = set()
        deduped = []
        for p in points_sorted:
            if p["year"] not in seen_years:
                seen_years.add(p["year"])
                deduped.append(p)

        if len(deduped) < 3:
            continue

        series_list.append({
            "label": f"{unit.capitalize()} trend",
            "years": [p["year"] for p in deduped],
            "values": [p["value"] for p in deduped],
            "unit": unit,
            "source_context": deduped[0]["context"],
        })

    return series_list[:settings.MAX_TIMESERIES_TO_MODEL]


def run_prophet_forecast(
    years: list[int], values: list[float], forecast_years: int = 5
) -> Optional[dict]:
    """
    Run Facebook Prophet forecast.
    Returns dict with forecast + metrics + scenario bands.
    """
    try:
        from prophet import Prophet

        df = pd.DataFrame({
            "ds": pd.to_datetime([f"{y}-01-01" for y in years]),
            "y": values,
        })

        model = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=0.3,
            interval_width=0.80,
        )
        model.fit(df)

        last_year = max(years)
        future_dates = pd.date_range(
            start=f"{last_year + 1}-01-01",
            periods=forecast_years,
            freq="YS",
        )
        future_df = pd.DataFrame({"ds": future_dates})
        forecast = model.predict(future_df)

        # Compute MAPE on training data
        train_forecast = model.predict(df[["ds"]])
        mape = _compute_mape(values, train_forecast["yhat"].tolist())

        base = forecast["yhat"].tolist()
        upper = forecast["yhat_upper"].tolist()
        lower = forecast["yhat_lower"].tolist()
        future_years = [d.year for d in future_dates]

        return {
            "model_used": "prophet",
            "future_years": future_years,
            "base_values": [round(v, 2) for v in base],
            "bull_values": [round(v, 2) for v in upper],
            "bear_values": [round(v, 2) for v in lower],
            "mape": round(mape, 2),
            "rmse": round(_compute_rmse(values, train_forecast["yhat"].tolist()), 2),
        }

    except Exception as e:
        logger.warning(f"Prophet failed: {e}, falling back to ARIMA")
        return run_arima_forecast(years, values, forecast_years)


def run_arima_forecast(
    years: list[int], values: list[float], forecast_years: int = 5
) -> Optional[dict]:
    """
    ARIMA fallback when Prophet fails or data is too small.
    """
    try:
        from statsmodels.tsa.arima.model import ARIMA

        model = ARIMA(values, order=(1, 1, 1))
        fitted = model.fit()
        forecast = fitted.forecast(steps=forecast_years)

        last_year = max(years)
        future_years = list(range(last_year + 1, last_year + 1 + forecast_years))
        base = forecast.tolist()

        # Create simple confidence bands (±15% bear/bull)
        bull = [v * 1.15 for v in base]
        bear = [v * 0.85 for v in base]

        return {
            "model_used": "arima",
            "future_years": future_years,
            "base_values": [round(v, 2) for v in base],
            "bull_values": [round(v, 2) for v in bull],
            "bear_values": [round(v, 2) for v in bear],
            "mape": None,
            "rmse": None,
        }
    except Exception as e:
        logger.error(f"ARIMA also failed: {e}")
        return None


def forecast_time_series(series: dict) -> Optional[dict]:
    """
    Main entry point. Runs Prophet first, falls back to ARIMA.
    Enriches the series dict with forecast results.
    """
    years = series.get("years", [])
    values = series.get("values", [])

    if len(years) < 3:
        return None

    result = run_prophet_forecast(years, values, settings.FORECAST_YEARS)
    if not result:
        return None

    return {
        **series,
        **result,
        "historical_years": years,
        "historical_values": values,
    }


def _compute_mape(actual: list, predicted: list) -> float:
    actual = np.array(actual)
    predicted = np.array(predicted)
    mask = actual != 0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def _compute_rmse(actual: list, predicted: list) -> float:
    actual = np.array(actual)
    predicted = np.array(predicted)
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))