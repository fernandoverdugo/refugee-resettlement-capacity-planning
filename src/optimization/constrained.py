from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog


def build_planning_constraints(
    state_shares: pd.DataFrame,
    total_fte: float = 8.0,
    monthly_cost_per_fte: float = 7500.0,
    ceiling_multiplier: float = 1.5,
    minimum_state_fte: float = 0.10,
) -> pd.DataFrame:
    required = {"state", "historical_share"}
    missing = required.difference(state_shares.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if state_shares.empty:
        raise ValueError("state_shares must not be empty")

    values = [
        total_fte,
        monthly_cost_per_fte,
        ceiling_multiplier,
        minimum_state_fte,
    ]
    if not all(np.isfinite(value) for value in values):
        raise ValueError("Constraint assumptions must be finite")
    if any(value < 0 for value in values):
        raise ValueError("Constraint assumptions must be nonnegative")

    frame = state_shares.loc[:, ["state", "historical_share"]].copy()
    frame["historical_share"] = pd.to_numeric(
        frame["historical_share"], errors="raise"
    )
    if (frame["historical_share"] < 0).any():
        raise ValueError("Historical shares must be nonnegative")

    frame["cost_per_fte"] = float(monthly_cost_per_fte)
    proportional_fte = total_fte * frame["historical_share"]
    frame["max_fte"] = np.maximum(
        proportional_fte * ceiling_multiplier,
        minimum_state_fte,
    )

    return frame.sort_values("state").reset_index(drop=True)


def optimize_constrained_capacity(
    state_demand: pd.DataFrame,
    state_constraints: pd.DataFrame,
    monthly_budget: float = 60000.0,
    total_fte: float = 8.0,
    monthly_caseload_per_fte: float = 30.0,
    utilization_rate: float = 0.85,
    minimum_coverage: float = 0.0,
) -> pd.DataFrame:
    demand_required = {"state", "state_demand"}
    constraint_required = {"state", "cost_per_fte", "max_fte"}

    missing_demand = demand_required.difference(state_demand.columns)
    missing_constraints = constraint_required.difference(state_constraints.columns)
    if missing_demand:
        raise ValueError(f"Missing demand columns: {sorted(missing_demand)}")
    if missing_constraints:
        raise ValueError(
            f"Missing constraint columns: {sorted(missing_constraints)}"
        )
    if state_demand.empty or state_constraints.empty:
        raise ValueError("Demand and constraints must not be empty")

    parameters = [
        monthly_budget,
        total_fte,
        monthly_caseload_per_fte,
        utilization_rate,
        minimum_coverage,
    ]
    if not all(np.isfinite(value) for value in parameters):
        raise ValueError("Optimization assumptions must be finite")
    if monthly_budget < 0 or total_fte < 0 or monthly_caseload_per_fte < 0:
        raise ValueError("Budget, FTE, and caseload assumptions must be nonnegative")
    if utilization_rate < 0 or utilization_rate > 1:
        raise ValueError("utilization_rate must be between 0 and 1")
    if minimum_coverage < 0 or minimum_coverage > 1:
        raise ValueError("minimum_coverage must be between 0 and 1")

    frame = state_demand.loc[:, ["state", "state_demand"]].merge(
        state_constraints.loc[:, ["state", "cost_per_fte", "max_fte"]],
        on="state",
        how="left",
        validate="one_to_one",
    )
    if frame[["cost_per_fte", "max_fte"]].isna().any().any():
        raise ValueError("Every demand state must have matching constraints")

    for column in ["state_demand", "cost_per_fte", "max_fte"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if (frame[column] < 0).any():
            raise ValueError(f"{column} must be nonnegative")

    capacity_per_fte = monthly_caseload_per_fte * utilization_rate
    demand = frame["state_demand"].to_numpy(dtype=float)
    cost = frame["cost_per_fte"].to_numpy(dtype=float)
    max_fte = frame["max_fte"].to_numpy(dtype=float)
    n = len(frame)

    if demand.sum() == 0:
        frame["served_demand"] = 0.0
        frame["unmet_demand"] = 0.0
        frame["allocated_fte"] = 0.0
        frame["monthly_cost"] = 0.0
        frame["coverage_rate"] = 1.0
        frame["minimum_coverage_achieved"] = 1.0
        frame["monthly_budget_limit"] = float(monthly_budget)
        frame["total_fte_limit"] = float(total_fte)
        frame["budget_binding"] = False
        frame["fte_binding"] = False
        frame["at_fte_ceiling"] = False
        return frame

    if capacity_per_fte <= 0 and demand.sum() > 0:
        raise ValueError("Positive demand requires positive capacity per FTE")

    c = np.zeros(n + 1)
    c[-1] = -1.0

    a_ub = []
    b_ub = []

    for i, value in enumerate(demand):
        coverage_row = np.zeros(n + 1)
        coverage_row[i] = -1.0
        coverage_row[-1] = value
        a_ub.append(coverage_row)
        b_ub.append(0.0)

        floor_row = np.zeros(n + 1)
        floor_row[i] = -1.0
        a_ub.append(floor_row)
        b_ub.append(-minimum_coverage * value)

    fte_row = np.zeros(n + 1)
    fte_row[:n] = 1.0 / capacity_per_fte
    a_ub.append(fte_row)
    b_ub.append(total_fte)

    budget_row = np.zeros(n + 1)
    budget_row[:n] = cost / capacity_per_fte
    a_ub.append(budget_row)
    b_ub.append(monthly_budget)

    bounds = [
        (0.0, min(float(demand[i]), float(max_fte[i] * capacity_per_fte)))
        for i in range(n)
    ] + [(minimum_coverage, 1.0)]

    stage_one = linprog(
        c,
        A_ub=np.asarray(a_ub),
        b_ub=np.asarray(b_ub),
        bounds=bounds,
        method="highs",
    )
    if not stage_one.success:
        raise RuntimeError(
            f"Constrained coverage optimization failed: {stage_one.message}"
        )

    achieved = float(stage_one.x[-1])

    second_c = np.zeros(n + 1)
    second_c[:n] = -1.0

    stage_two_a = list(a_ub)
    stage_two_b = list(b_ub)
    achieved_floor = np.zeros(n + 1)
    achieved_floor[-1] = -1.0
    stage_two_a.append(achieved_floor)
    stage_two_b.append(-(achieved - 1e-9))

    stage_two = linprog(
        second_c,
        A_ub=np.asarray(stage_two_a),
        b_ub=np.asarray(stage_two_b),
        bounds=bounds,
        method="highs",
    )
    if not stage_two.success:
        raise RuntimeError(
            f"Constrained service optimization failed: {stage_two.message}"
        )

    served = stage_two.x[:n]
    allocated_fte = served / capacity_per_fte

    frame["served_demand"] = served
    frame["unmet_demand"] = np.maximum(demand - served, 0.0)
    frame["allocated_fte"] = allocated_fte
    frame["monthly_cost"] = allocated_fte * cost
    frame["coverage_rate"] = np.where(
        demand > 0,
        served / demand,
        1.0,
    )
    frame["minimum_coverage_achieved"] = achieved
    frame["monthly_budget_limit"] = float(monthly_budget)
    frame["total_fte_limit"] = float(total_fte)
    frame["budget_binding"] = bool(
        np.isclose(frame["monthly_cost"].sum(), monthly_budget, atol=1e-7)
    )
    frame["fte_binding"] = bool(
        np.isclose(frame["allocated_fte"].sum(), total_fte, atol=1e-7)
    )
    frame["at_fte_ceiling"] = np.isclose(
        frame["allocated_fte"].to_numpy(dtype=float),
        max_fte,
        atol=1e-7,
    )

    return frame



def optimize_all_constrained_scenarios(
    state_scenarios: pd.DataFrame,
    state_constraints: pd.DataFrame,
    monthly_budget: float = 60000.0,
    total_fte: float = 8.0,
    monthly_caseload_per_fte: float = 30.0,
    utilization_rate: float = 0.85,
    minimum_coverage: float = 0.0,
) -> pd.DataFrame:
    required = {
        "scenario",
        "date",
        "state",
        "state_demand",
        "historical_share",
        "share_fiscal_year",
    }
    missing = required.difference(state_scenarios.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    rows = []
    for (scenario, date), group in state_scenarios.groupby(
        ["scenario", "date"], sort=True
    ):
        optimized = optimize_constrained_capacity(
            group,
            state_constraints,
            monthly_budget=monthly_budget,
            total_fte=total_fte,
            monthly_caseload_per_fte=monthly_caseload_per_fte,
            utilization_rate=utilization_rate,
            minimum_coverage=minimum_coverage,
        )
        optimized["scenario"] = scenario
        optimized["date"] = date
        optimized["historical_share"] = group["historical_share"].to_numpy()
        optimized["share_fiscal_year"] = group["share_fiscal_year"].to_numpy()
        rows.append(optimized)

    return pd.concat(rows, ignore_index=True).sort_values(
        ["scenario", "date", "state"]
    ).reset_index(drop=True)


def summarize_constrained_optimization(results: pd.DataFrame) -> pd.DataFrame:
    required = {
        "scenario", "date", "state_demand", "served_demand", "unmet_demand",
        "allocated_fte", "monthly_cost", "minimum_coverage_achieved",
        "budget_binding", "fte_binding", "at_fte_ceiling",
    }
    missing = required.difference(results.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if results.empty:
        raise ValueError("results must not be empty")

    summary = (
        results.groupby("scenario", as_index=False)
        .agg(
            months=("date", "nunique"),
            total_demand=("state_demand", "sum"),
            served_demand=("served_demand", "sum"),
            unmet_demand=("unmet_demand", "sum"),
            allocated_fte_months=("allocated_fte", "sum"),
            total_cost=("monthly_cost", "sum"),
            minimum_coverage=("minimum_coverage_achieved", "min"),
        )
        .sort_values("total_demand")
        .reset_index(drop=True)
    )
    summary["service_coverage_rate"] = np.where(
        summary["total_demand"] > 0,
        summary["served_demand"] / summary["total_demand"],
        1.0,
    )

    monthly = (
        results.groupby(["scenario", "date"], as_index=False)
        .agg(
            budget_binding=("budget_binding", "max"),
            fte_binding=("fte_binding", "max"),
            states_at_fte_ceiling=("at_fte_ceiling", "sum"),
        )
    )
    diagnostics = (
        monthly.groupby("scenario", as_index=False)
        .agg(
            budget_binding_months=("budget_binding", "sum"),
            fte_binding_months=("fte_binding", "sum"),
            max_states_at_fte_ceiling=("states_at_fte_ceiling", "max"),
        )
    )
    return summary.merge(diagnostics, on="scenario", how="left")
