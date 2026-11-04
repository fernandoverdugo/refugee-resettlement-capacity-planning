import numpy as np
import pandas as pd
import pytest

from src.scenarios.demand import (
    build_demand_scenarios,
    build_naive_reference,
    summarize_scenarios,
    validate_reference_forecast,
)


def test_validate_reference_forecast_sorts_dates():
    frame = pd.DataFrame(
        {
            "date": ["2025-12-01", "2025-10-01", "2025-11-01"],
            "forecast": [30, 10, 20],
        }
    )

    result = validate_reference_forecast(frame)

    assert result["forecast"].tolist() == [10, 20, 30]


def test_validate_reference_forecast_rejects_month_gaps():
    frame = pd.DataFrame(
        {
            "date": ["2025-10-01", "2025-12-01"],
            "forecast": [10, 30],
        }
    )

    with pytest.raises(ValueError, match="contiguous"):
        validate_reference_forecast(frame)


def test_build_demand_scenarios_applies_multipliers():
    reference = pd.DataFrame(
        {
            "date": pd.date_range("2025-10-01", periods=2, freq="MS"),
            "forecast": [100.0, 200.0],
        }
    )

    result = build_demand_scenarios(
        reference,
        {"lower": 0.5, "baseline": 1.0, "higher": 1.5},
    )

    totals = result.groupby("scenario")["scenario_demand"].sum().to_dict()

    assert totals == {
        "baseline": 300.0,
        "higher": 450.0,
        "lower": 150.0,
    }


def test_build_naive_reference_extends_last_observation():
    index = pd.date_range("2025-07-01", periods=3, freq="MS")
    history = pd.Series([100.0, 120.0, 140.0], index=index)

    result = build_naive_reference(history, horizon=3)

    assert result["date"].tolist() == list(pd.date_range("2025-10-01", periods=3, freq="MS"))
    np.testing.assert_array_equal(result["forecast"].to_numpy(), np.array([140.0, 140.0, 140.0]))


def test_summarize_scenarios_returns_planning_totals():
    reference = pd.DataFrame(
        {
            "date": pd.date_range("2025-10-01", periods=2, freq="MS"),
            "forecast": [100.0, 100.0],
        }
    )
    scenarios = build_demand_scenarios(reference)

    summary = summarize_scenarios(scenarios)

    baseline = summary[summary["scenario"] == "baseline"].iloc[0]
    assert baseline["months"] == 2
    assert baseline["total_demand"] == 200.0
    assert baseline["average_monthly_demand"] == 100.0
    assert baseline["peak_monthly_demand"] == 100.0
