import numpy as np
import pandas as pd
import pytest

from src.optimization.allocation import (
    allocate_scenario_demand_to_states,
    build_state_shares,
    optimize_fair_capacity,
    summarize_optimization,
)


def test_build_state_shares_sums_to_one():
    frame = pd.DataFrame(
        {
            "state": ["A", "A", "B", "B"],
            "fiscal_year": [2024, 2024, 2024, 2024],
            "arrivals": [30, 20, 25, 25],
        }
    )

    shares = build_state_shares(frame, fiscal_year=2024)

    assert np.isclose(shares["historical_share"].sum(), 1.0)
    assert shares.set_index("state").loc["A", "historical_share"] == 0.5


def test_allocate_scenario_demand_preserves_total():
    scenarios = pd.DataFrame(
        {
            "scenario": ["baseline"],
            "date": ["2025-10-01"],
            "scenario_demand": [200.0],
        }
    )
    shares = pd.DataFrame(
        {
            "state": ["A", "B"],
            "historical_share": [0.75, 0.25],
            "share_fiscal_year": [2024, 2024],
        }
    )

    result = allocate_scenario_demand_to_states(scenarios, shares)

    assert result["state_demand"].sum() == 200.0
    assert result.set_index("state").loc["A", "state_demand"] == 150.0


def test_optimizer_equalizes_coverage_when_capacity_is_limited():
    demand = pd.DataFrame(
        {
            "state": ["A", "B"],
            "state_demand": [75.0, 25.0],
        }
    )

    result = optimize_fair_capacity(
        demand,
        total_fte=2.0,
        monthly_caseload_per_fte=25.0,
        utilization_rate=1.0,
    )

    assert np.allclose(result["coverage_rate"], 0.5, atol=1e-7)
    assert np.isclose(result["served_demand"].sum(), 50.0)
    assert np.isclose(result["allocated_fte"].sum(), 2.0)


def test_optimizer_fully_serves_demand_when_capacity_is_sufficient():
    demand = pd.DataFrame(
        {
            "state": ["A", "B"],
            "state_demand": [20.0, 30.0],
        }
    )

    result = optimize_fair_capacity(
        demand,
        total_fte=4.0,
        monthly_caseload_per_fte=25.0,
        utilization_rate=1.0,
    )

    assert np.allclose(result["coverage_rate"], 1.0)
    assert np.isclose(result["unmet_demand"].sum(), 0.0)
    assert np.isclose(result["allocated_fte"].sum(), 2.0)


def test_optimizer_rejects_invalid_utilization():
    demand = pd.DataFrame(
        {
            "state": ["A"],
            "state_demand": [10.0],
        }
    )

    with pytest.raises(ValueError, match="between 0 and 1"):
        optimize_fair_capacity(
            demand,
            total_fte=1.0,
            monthly_caseload_per_fte=25.0,
            utilization_rate=1.1,
        )


def test_summarize_optimization_returns_coverage():
    results = pd.DataFrame(
        {
            "scenario": ["higher", "higher"],
            "date": ["2025-10-01", "2025-10-01"],
            "state_demand": [75.0, 25.0],
            "served_demand": [37.5, 12.5],
            "unmet_demand": [37.5, 12.5],
            "allocated_fte": [1.5, 0.5],
            "minimum_coverage": [0.5, 0.5],
        }
    )

    summary = summarize_optimization(results)

    row = summary.iloc[0]
    assert row["total_demand"] == 100.0
    assert row["served_demand"] == 50.0
    assert row["unmet_demand"] == 50.0
    assert row["service_coverage_rate"] == 0.5
    assert row["minimum_coverage"] == 0.5
