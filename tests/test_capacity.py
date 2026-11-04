import numpy as np
import pandas as pd
import pytest

from src.scenarios.capacity import (
    calculate_monthly_capacity,
    evaluate_capacity,
    summarize_capacity,
)


def test_calculate_monthly_capacity_applies_utilization():
    capacity = calculate_monthly_capacity(
        staff_fte=8,
        monthly_caseload_per_fte=30,
        utilization_rate=0.85,
    )

    assert capacity == 204.0


def test_calculate_monthly_capacity_rejects_invalid_utilization():
    with pytest.raises(ValueError, match="between 0 and 1"):
        calculate_monthly_capacity(8, 30, 1.2)


def test_evaluate_capacity_calculates_unmet_and_surplus():
    scenarios = pd.DataFrame(
        {
            "scenario": ["lower", "higher"],
            "date": ["2025-10-01", "2025-10-01"],
            "scenario_demand": [100.0, 250.0],
        }
    )

    result = evaluate_capacity(
        scenarios,
        {
            "staff_fte": 8,
            "monthly_caseload_per_fte": 30,
            "utilization_rate": 0.85,
        },
    )

    lower = result[result["scenario"] == "lower"].iloc[0]
    higher = result[result["scenario"] == "higher"].iloc[0]

    assert lower["monthly_capacity"] == 204.0
    assert lower["unmet_demand"] == 0.0
    assert lower["surplus_capacity"] == 104.0

    assert higher["served_demand"] == 204.0
    assert higher["unmet_demand"] == 46.0
    assert higher["surplus_capacity"] == 0.0


def test_evaluate_capacity_handles_zero_capacity():
    scenarios = pd.DataFrame(
        {
            "scenario": ["baseline"],
            "date": ["2025-10-01"],
            "scenario_demand": [100.0],
        }
    )

    result = evaluate_capacity(
        scenarios,
        {
            "staff_fte": 0,
            "monthly_caseload_per_fte": 30,
            "utilization_rate": 0.85,
        },
    )

    assert np.isnan(result.iloc[0]["capacity_utilization"])
    assert result.iloc[0]["unmet_demand"] == 100.0


def test_summarize_capacity_returns_coverage():
    scenarios = pd.DataFrame(
        {
            "scenario": ["baseline", "baseline"],
            "date": ["2025-10-01", "2025-11-01"],
            "scenario_demand": [100.0, 300.0],
        }
    )

    results = evaluate_capacity(
        scenarios,
        {
            "staff_fte": 8,
            "monthly_caseload_per_fte": 30,
            "utilization_rate": 0.85,
        },
    )
    summary = summarize_capacity(results)

    row = summary.iloc[0]
    assert row["total_demand"] == 400.0
    assert row["total_capacity"] == 408.0
    assert row["served_demand"] == 304.0
    assert row["unmet_demand"] == 96.0
    assert row["service_coverage_rate"] == 0.76
