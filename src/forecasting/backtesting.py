from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {"date", "arrivals"}


def prepare_monthly_series(frame: pd.DataFrame) -> pd.Series:
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = frame.loc[:, ["date", "arrivals"]].copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["arrivals"] = pd.to_numeric(data["arrivals"], errors="raise")

    if data["date"].duplicated().any():
        raise ValueError("Monthly series contains duplicate dates")
    if (data["arrivals"] < 0).any():
        raise ValueError("Arrivals must be nonnegative")

    data = data.sort_values("date").set_index("date")
    expected = pd.date_range(data.index.min(), data.index.max(), freq="MS")
    if not data.index.equals(expected):
        raise ValueError("Monthly series must be contiguous at month-start frequency")

    return data["arrivals"].astype(float)


def naive_forecast(train: pd.Series, horizon: int) -> np.ndarray:
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if train.empty:
        raise ValueError("train must contain at least one observation")
    return np.repeat(float(train.iloc[-1]), horizon)


def seasonal_naive_forecast(
    train: pd.Series,
    horizon: int,
    season_length: int = 12,
) -> np.ndarray:
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if season_length < 1:
        raise ValueError("season_length must be at least 1")
    if len(train) < season_length:
        raise ValueError("train must contain at least one full season")

    seasonal_values = train.iloc[-season_length:].to_numpy(dtype=float)
    return np.array(
        [seasonal_values[i % season_length] for i in range(horizon)],
        dtype=float,
    )


def rolling_origin_backtest(
    series: pd.Series,
    min_train: int = 24,
    max_horizon: int = 3,
    season_length: int = 12,
) -> pd.DataFrame:
    if min_train < season_length:
        raise ValueError("min_train must be at least season_length")
    if max_horizon < 1:
        raise ValueError("max_horizon must be at least 1")
    if len(series) < min_train + 1:
        raise ValueError("series is too short for the requested backtest")

    rows = []
    model_functions = {
        "naive": lambda train, h: naive_forecast(train, h),
        "seasonal_naive": lambda train, h: seasonal_naive_forecast(
            train, h, season_length
        ),
    }

    for origin in range(min_train, len(series)):
        available_horizon = min(max_horizon, len(series) - origin)
        if available_horizon < 1:
            continue

        train = series.iloc[:origin]
        actual = series.iloc[origin : origin + available_horizon]

        for model_name, model_function in model_functions.items():
            predictions = model_function(train, available_horizon)

            for step, (date, actual_value, predicted_value) in enumerate(
                zip(actual.index, actual.to_numpy(dtype=float), predictions),
                start=1,
            ):
                rows.append(
                    {
                        "model": model_name,
                        "origin_date": train.index[-1],
                        "forecast_date": date,
                        "horizon": step,
                        "actual": actual_value,
                        "prediction": max(0.0, float(predicted_value)),
                    }
                )

    result = pd.DataFrame(rows)
    result["error"] = result["actual"] - result["prediction"]
    result["absolute_error"] = result["error"].abs()
    result["squared_error"] = result["error"] ** 2
    return result


def summarize_backtest(results: pd.DataFrame) -> pd.DataFrame:
    required = {"model", "horizon", "actual", "prediction", "absolute_error", "squared_error"}
    missing = required.difference(results.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if results.empty:
        raise ValueError("results must not be empty")

    summary_rows = []
    for (model, horizon), group in results.groupby(["model", "horizon"], sort=True):
        denominator = group["actual"].abs().sum()
        smape_denominator = group["actual"].abs() + group["prediction"].abs()
        smape_terms = np.where(
            smape_denominator.to_numpy() == 0,
            0.0,
            2.0
            * group["absolute_error"].to_numpy()
            / smape_denominator.to_numpy(),
        )

        summary_rows.append(
            {
                "model": model,
                "horizon": int(horizon),
                "n_forecasts": int(len(group)),
                "mae": float(group["absolute_error"].mean()),
                "rmse": float(np.sqrt(group["squared_error"].mean())),
                "wape": float(group["absolute_error"].sum() / denominator)
                if denominator > 0
                else np.nan,
                "smape": float(np.mean(smape_terms)),
            }
        )

    return pd.DataFrame(summary_rows).sort_values(
        ["horizon", "mae", "model"]
    ).reset_index(drop=True)
