from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


DEFAULT_SCENARIOS = {
    "lower": 0.50,
    "baseline": 1.00,
    "higher": 1.50,
}


def validate_reference_forecast(reference: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "forecast"}
    missing = required.difference(reference.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    frame = reference.loc[:, ["date", "forecast"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["forecast"] = pd.to_numeric(frame["forecast"], errors="raise")

    if frame["date"].duplicated().any():
        raise ValueError("Reference forecast contains duplicate dates")
    if (frame["forecast"] < 0).any():
        raise ValueError("Reference forecast must be nonnegative")

    frame = frame.sort_values("date").reset_index(drop=True)
    if len(frame) > 1:
        expected = pd.date_range(frame["date"].min(), frame["date"].max(), freq="MS")
        if not frame["date"].equals(pd.Series(expected, name="date")):
            raise ValueError("Reference forecast must be contiguous at month-start frequency")

    return frame


def build_demand_scenarios(
    reference: pd.DataFrame,
    multipliers: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    frame = validate_reference_forecast(reference)
    scenario_multipliers = dict(DEFAULT_SCENARIOS if multipliers is None else multipliers)

    if not scenario_multipliers:
        raise ValueError("At least one scenario is required")

    rows = []
    for scenario, multiplier in scenario_multipliers.items():
        if not scenario:
            raise ValueError("Scenario names must be nonempty")
        if not np.isfinite(multiplier) or multiplier < 0:
            raise ValueError("Scenario multipliers must be finite and nonnegative")

        for row in frame.itertuples(index=False):
            demand = max(0.0, float(row.forecast) * float(multiplier))
            rows.append(
                {
                    "scenario": scenario,
                    "date": row.date,
                    "reference_forecast": float(row.forecast),
                    "multiplier": float(multiplier),
                    "scenario_demand": demand,
                }
            )

    return pd.DataFrame(rows).sort_values(
        ["date", "multiplier", "scenario"]
    ).reset_index(drop=True)


def build_naive_reference(
    history: pd.Series,
    horizon: int = 6,
) -> pd.DataFrame:
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if history.empty:
        raise ValueError("history must contain at least one observation")
    if not isinstance(history.index, pd.DatetimeIndex):
        raise ValueError("history must use a DatetimeIndex")

    history = history.sort_index()
    if history.index.duplicated().any():
        raise ValueError("history contains duplicate dates")
    if (history < 0).any():
        raise ValueError("history must be nonnegative")

    last_date = history.index[-1]
    future_dates = pd.date_range(
        last_date + pd.offsets.MonthBegin(1),
        periods=horizon,
        freq="MS",
    )
    last_value = float(history.iloc[-1])

    return pd.DataFrame(
        {
            "date": future_dates,
            "forecast": np.repeat(last_value, horizon),
        }
    )


def summarize_scenarios(scenarios: pd.DataFrame) -> pd.DataFrame:
    required = {"scenario", "scenario_demand"}
    missing = required.difference(scenarios.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if scenarios.empty:
        raise ValueError("scenarios must not be empty")

    summary = (
        scenarios.groupby("scenario", as_index=False)
        .agg(
            months=("scenario_demand", "size"),
            total_demand=("scenario_demand", "sum"),
            average_monthly_demand=("scenario_demand", "mean"),
            peak_monthly_demand=("scenario_demand", "max"),
        )
        .sort_values("total_demand")
        .reset_index(drop=True)
    )
    return summary
