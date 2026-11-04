import numpy as np
import pandas as pd
import pytest

from src.optimization.constrained import (
    build_planning_constraints,
    optimize_constrained_capacity,
    summarize_constrained_optimization,
)


def test_build_planning_constraints_adds_costs_and_ceilings():
    shares = pd.DataFrame(
        {
            "state": ["A", "B"],
            "historical_share": [0.75, 0.25],
        }
    )

    result = build_planning_constraints(
        shares,
        total_fte=4.0,
        monthly_cost_per_fte=5000.0,
        ceiling_multiplier=1.5,
        minimum_state_fte=0.1,
    )

    indexed = result.set_index("state")
    assert indexed.loc["A", "max_fte"] == 4.5
    assert indexed.loc["B", "max_fte"] == 1.5
    assert (result["cost_per_fte"] == 5000.0).all()


def test_constrained_optimizer_respects_budget():
    demand = pd.DataFrame(
        {
            "state": ["A", "B"],
            "state_demand": [50.0, 50.0],
        }
    )
    constraints = pd.DataFrame(
        {
            "state": ["A", "B"],
            "cost_per_fte": [10000.0, 10000.0],
            "max_fte": [5.0, 5.0],
        }
    )

    result = optimize_constrained_capacity(
        demand,
        constraints,
        monthly_budget=20000.0,
        total_fte=10.0,
        monthly_caseload_per_fte=25.0,
        utilization_rate=1.0,
    )

    assert np.isclose(result["monthly_cost"].sum(), 20000.0)
    assert np.isclose(result["served_demand"].sum(), 50.0)
    assert np.allclose(result["coverage_rate"], 0.5, atol=1e-7)
    assert result["budget_binding"].all()
    assert not result["fte_binding"].any()


def test_constrained_optimizer_respects_state_ceiling():
    demand = pd.DataFrame(
        {
            "state": ["A", "B"],
            "state_demand": [100.0, 100.0],
        }
    )
    constraints = pd.DataFrame(
        {
            "state": ["A", "B"],
            "cost_per_fte": [1000.0, 1000.0],
            "max_fte": [1.0, 10.0],
        }
    )

    result = optimize_constrained_capacity(
        demand,
        constraints,
        monthly_budget=100000.0,
        total_fte=10.0,
        monthly_caseload_per_fte=25.0,
        utilization_rate=1.0,
    )

    indexed = result.set_index("state")
    assert indexed.loc["A", "allocated_fte"] <= 1.0 + 1e-9
    assert np.isclose(indexed.loc["A", "coverage_rate"], 0.25)
    assert np.isclose(result["minimum_coverage_achieved"].iloc[0], 0.25)
    assert bool(indexed.loc["A", "at_fte_ceiling"])


def test_constrained_optimizer_rejects_infeasible_minimum_coverage():
    demand = pd.DataFrame(
        {
            "state": ["A"],
            "state_demand": [100.0],
        }
    )
    constraints = pd.DataFrame(
        {
            "state": ["A"],
            "cost_per_fte": [1000.0],
            "max_fte": [1.0],
        }
    )

    with pytest.raises(RuntimeError, match="failed"):
        optimize_constrained_capacity(
            demand,
            constraints,
            monthly_budget=100000.0,
            total_fte=10.0,
            monthly_caseload_per_fte=25.0,
            utilization_rate=1.0,
            minimum_coverage=0.5,
        )


def test_summarize_constrained_optimization_reports_cost():
    results = pd.DataFrame(
        {
            "scenario": ["higher", "higher"],
            "date": ["2025-10-01", "2025-10-01"],
            "state_demand": [50.0, 50.0],
            "served_demand": [25.0, 25.0],
            "unmet_demand": [25.0, 25.0],
            "allocated_fte": [1.0, 1.0],
            "monthly_cost": [10000.0, 10000.0],
            "minimum_coverage_achieved": [0.5, 0.5],
            "budget_binding": [True, True],
            "fte_binding": [False, False],
            "at_fte_ceiling": [True, False],
        }
    )

    summary = summarize_constrained_optimization(results)

    row = summary.iloc[0]
    assert row["total_cost"] == 20000.0
    assert row["service_coverage_rate"] == 0.5
    assert row["minimum_coverage"] == 0.5
    assert row["budget_binding_months"] == 1
    assert row["fte_binding_months"] == 0
    assert row["max_states_at_fte_ceiling"] == 1
