from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog


def build_state_shares(
    state_month: pd.DataFrame,
    fiscal_year: int | None = None,
) -> pd.DataFrame:
    required = {"state", "fiscal_year", "arrivals"}
    missing = required.difference(state_month.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if state_month.empty:
        raise ValueError("state_month must not be empty")

    frame = state_month.loc[:, ["state", "fiscal_year", "arrivals"]].copy()
    frame["fiscal_year"] = pd.to_numeric(frame["fiscal_year"], errors="raise")
    frame["arrivals"] = pd.to_numeric(frame["arrivals"], errors="raise")

    if (frame["arrivals"] < 0).any():
        raise ValueError("Arrivals must be nonnegative")

    selected_year = (
        int(frame["fiscal_year"].max())
        if fiscal_year is None
        else int(fiscal_year)
    )
    frame = frame[frame["fiscal_year"] == selected_year]
    if frame.empty:
        raise ValueError(f"No state-month rows found for fiscal year {selected_year}")

    totals = (
        frame.groupby("state", as_index=False)["arrivals"]
        .sum()
        .rename(columns={"arrivals": "historical_arrivals"})
    )
    grand_total = float(totals["historical_arrivals"].sum())
    if grand_total <= 0:
        raise ValueError("Selected fiscal year has no positive arrivals")

    totals["historical_share"] = totals["historical_arrivals"] / grand_total
    totals["share_fiscal_year"] = selected_year

    return totals.sort_values(
        ["historical_share", "state"],
        ascending=[False, True],
    ).reset_index(drop=True)


def allocate_scenario_demand_to_states(
    scenarios: pd.DataFrame,
    state_shares: pd.DataFrame,
) -> pd.DataFrame:
    scenario_required = {"scenario", "date", "scenario_demand"}
    share_required = {"state", "historical_share", "share_fiscal_year"}

    missing_scenarios = scenario_required.difference(scenarios.columns)
    missing_shares = share_required.difference(state_shares.columns)
    if missing_scenarios:
        raise ValueError(
            f"Missing scenario columns: {sorted(missing_scenarios)}"
        )
    if missing_shares:
        raise ValueError(f"Missing share columns: {sorted(missing_shares)}")
    if scenarios.empty or state_shares.empty:
        raise ValueError("scenarios and state_shares must not be empty")

    scenario_frame = scenarios.loc[
        :, ["scenario", "date", "scenario_demand"]
    ].copy()
    scenario_frame["date"] = pd.to_datetime(
        scenario_frame["date"], errors="raise"
    )
    scenario_frame["scenario_demand"] = pd.to_numeric(
        scenario_frame["scenario_demand"], errors="raise"
    )

    share_frame = state_shares.loc[
        :, ["state", "historical_share", "share_fiscal_year"]
    ].copy()
    share_frame["historical_share"] = pd.to_numeric(
        share_frame["historical_share"], errors="raise"
    )

    if (scenario_frame["scenario_demand"] < 0).any():
        raise ValueError("Scenario demand must be nonnegative")
    if (share_frame["historical_share"] < 0).any():
        raise ValueError("Historical shares must be nonnegative")

    share_total = float(share_frame["historical_share"].sum())
    if not np.isclose(share_total, 1.0, atol=1e-8):
        raise ValueError("Historical shares must sum to 1")

    scenario_frame["_key"] = 1
    share_frame["_key"] = 1
    result = scenario_frame.merge(share_frame, on="_key").drop(columns="_key")
    result["state_demand"] = (
        result["scenario_demand"] * result["historical_share"]
    )

    return result.sort_values(
        ["scenario", "date", "state"]
    ).reset_index(drop=True)


def optimize_fair_capacity(
    state_demand: pd.DataFrame,
    total_fte: float = 8.0,
    monthly_caseload_per_fte: float = 30.0,
    utilization_rate: float = 0.85,
) -> pd.DataFrame:
    required = {"state", "state_demand"}
    missing = required.difference(state_demand.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if state_demand.empty:
        raise ValueError("state_demand must not be empty")

    parameters = [total_fte, monthly_caseload_per_fte, utilization_rate]
    if not all(np.isfinite(value) for value in parameters):
        raise ValueError("Optimization assumptions must be finite")
    if total_fte < 0 or monthly_caseload_per_fte < 0:
        raise ValueError("FTE and caseload assumptions must be nonnegative")
    if utilization_rate < 0 or utilization_rate > 1:
        raise ValueError("utilization_rate must be between 0 and 1")

    frame = state_demand.loc[:, ["state", "state_demand"]].copy()
    frame["state_demand"] = pd.to_numeric(
        frame["state_demand"], errors="raise"
    )
    if (frame["state_demand"] < 0).any():
        raise ValueError("State demand must be nonnegative")

    demand = frame["state_demand"].to_numpy(dtype=float)
    capacity_per_fte = monthly_caseload_per_fte * utilization_rate
    total_capacity = total_fte * capacity_per_fte
    n = len(frame)

    if demand.sum() == 0:
        frame["served_demand"] = 0.0
        frame["unmet_demand"] = 0.0
        frame["allocated_fte"] = 0.0
        frame["coverage_rate"] = 1.0
        frame["minimum_coverage"] = 1.0
        return frame

    c = np.zeros(n + 1)
    c[-1] = -1.0

    a_ub = []
    b_ub = []
    for i, value in enumerate(demand):
        row = np.zeros(n + 1)
        row[i] = -1.0
        row[-1] = value
        a_ub.append(row)
        b_ub.append(0.0)

    capacity_row = np.zeros(n + 1)
    capacity_row[:n] = 1.0
    a_ub.append(capacity_row)
    b_ub.append(total_capacity)

    bounds = [(0.0, float(value)) for value in demand] + [(0.0, 1.0)]

    stage_one = linprog(
        c,
        A_ub=np.asarray(a_ub),
        b_ub=np.asarray(b_ub),
        bounds=bounds,
        method="highs",
    )
    if not stage_one.success:
        raise RuntimeError(f"Coverage optimization failed: {stage_one.message}")

    minimum_coverage = float(stage_one.x[-1])

    second_c = np.zeros(n + 1)
    second_c[:n] = -1.0

    stage_two_a = list(a_ub)
    stage_two_b = list(b_ub)
    coverage_floor = np.zeros(n + 1)
    coverage_floor[-1] = -1.0
    stage_two_a.append(coverage_floor)
    stage_two_b.append(-(minimum_coverage - 1e-9))

    stage_two = linprog(
        second_c,
        A_ub=np.asarray(stage_two_a),
        b_ub=np.asarray(stage_two_b),
        bounds=bounds,
        method="highs",
    )
    if not stage_two.success:
        raise RuntimeError(f"Service optimization failed: {stage_two.message}")

    served = stage_two.x[:n]
    frame["served_demand"] = served
    frame["unmet_demand"] = np.maximum(demand - served, 0.0)
    frame["allocated_fte"] = np.where(
        capacity_per_fte > 0,
        served / capacity_per_fte,
        0.0,
    )
    frame["coverage_rate"] = np.where(
        demand > 0,
        served / demand,
        1.0,
    )
    frame["minimum_coverage"] = minimum_coverage

    return frame


def optimize_all_scenarios(
    state_scenarios: pd.DataFrame,
    total_fte: float = 8.0,
    monthly_caseload_per_fte: float = 30.0,
    utilization_rate: float = 0.85,
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
        optimized = optimize_fair_capacity(
            group,
            total_fte=total_fte,
            monthly_caseload_per_fte=monthly_caseload_per_fte,
            utilization_rate=utilization_rate,
        )
        optimized["scenario"] = scenario
        optimized["date"] = date
        optimized["historical_share"] = group["historical_share"].to_numpy()
        optimized["share_fiscal_year"] = group["share_fiscal_year"].to_numpy()
        rows.append(optimized)

    return pd.concat(rows, ignore_index=True).sort_values(
        ["scenario", "date", "state"]
    ).reset_index(drop=True)


def summarize_optimization(results: pd.DataFrame) -> pd.DataFrame:
    required = {
        "scenario",
        "date",
        "state_demand",
        "served_demand",
        "unmet_demand",
        "allocated_fte",
        "minimum_coverage",
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
            minimum_coverage=("minimum_coverage", "min"),
        )
        .sort_values("total_demand")
        .reset_index(drop=True)
    )
    summary["service_coverage_rate"] = np.where(
        summary["total_demand"] > 0,
        summary["served_demand"] / summary["total_demand"],
        1.0,
    )
    return summary
