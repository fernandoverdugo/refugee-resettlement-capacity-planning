import numpy as np
import pandas as pd
import pytest

from src.forecasting.backtesting import (
    naive_forecast,
    prepare_monthly_series,
    rolling_origin_backtest,
    seasonal_naive_forecast,
    summarize_backtest,
)


def test_prepare_monthly_series_sorts_and_validates_months():
    frame = pd.DataFrame(
        {
            "date": ["2024-03-01", "2024-01-01", "2024-02-01"],
            "arrivals": [30, 10, 20],
        }
    )

    series = prepare_monthly_series(frame)

    assert series.index.tolist() == list(pd.date_range("2024-01-01", periods=3, freq="MS"))
    assert series.tolist() == [10.0, 20.0, 30.0]


def test_prepare_monthly_series_rejects_gaps():
    frame = pd.DataFrame(
        {
            "date": ["2024-01-01", "2024-03-01"],
            "arrivals": [10, 30],
        }
    )

    with pytest.raises(ValueError, match="contiguous"):
        prepare_monthly_series(frame)


def test_naive_forecast_repeats_last_value():
    series = pd.Series([10.0, 15.0, 25.0])

    forecast = naive_forecast(series, 3)

    np.testing.assert_array_equal(forecast, np.array([25.0, 25.0, 25.0]))


def test_seasonal_naive_forecast_repeats_last_season():
    series = pd.Series(np.arange(1, 25, dtype=float))

    forecast = seasonal_naive_forecast(series, 4, season_length=12)

    np.testing.assert_array_equal(forecast, np.array([13.0, 14.0, 15.0, 16.0]))


def test_rolling_origin_backtest_uses_only_prior_observations():
    index = pd.date_range("2020-01-01", periods=30, freq="MS")
    series = pd.Series(np.arange(1, 31, dtype=float), index=index)

    results = rolling_origin_backtest(
        series,
        min_train=24,
        max_horizon=2,
        season_length=12,
    )

    first_naive = results[
        (results["model"] == "naive")
        & (results["origin_date"] == pd.Timestamp("2021-12-01"))
        & (results["horizon"] == 1)
    ].iloc[0]

    assert first_naive["forecast_date"] == pd.Timestamp("2022-01-01")
    assert first_naive["prediction"] == 24.0
    assert first_naive["actual"] == 25.0


def test_summarize_backtest_returns_metrics_by_model_and_horizon():
    index = pd.date_range("2020-01-01", periods=36, freq="MS")
    series = pd.Series(np.arange(1, 37, dtype=float), index=index)

    results = rolling_origin_backtest(series, min_train=24, max_horizon=3)
    summary = summarize_backtest(results)

    assert set(summary["model"]) == {"naive", "seasonal_naive"}
    assert set(summary["horizon"]) == {1, 2, 3}
    assert (summary["n_forecasts"] > 0).all()
    assert (summary["mae"] >= 0).all()
    assert (summary["rmse"] >= 0).all()
