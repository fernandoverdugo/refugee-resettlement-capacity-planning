from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd


DEFAULT_CAPACITY_ASSUMPTIONS = {
    "staff_fte": 8.0,
    "monthly_caseload_per_fte": 30.0,
    "utilization_rate": 0.85,
}


def calculate_monthly_capacity(
    staff_fte: float,
    monthly_caseload_per_fte: float,
    utilization_rate: float = 1.0,
) -> float:
    values = [staff_fte, monthly_caseload_per_fte, utilization_rate]
    if not all(np.isfinite(value) for value in values):
        raise ValueError("Capacity assumptions must be finite")
    if staff_fte < 0 or monthly_caseload_per_fte < 0:
        raise ValueError("Staffing and caseload assumptions must be nonnegative")
    if utilization_rate < 0 or utilization_rate > 1:
        raise ValueError("utilization_rate must be between 0 and 1")

    return float(staff_fte * monthly_caseload_per_fte * utilization_rate)


def evaluate_capacity(
    scenarios: pd.DataFrame,
    assumptions: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    required = {"scenario", "date", "scenario_demand"}
    missing = required.difference(scenarios.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if scenarios.empty:
        raise ValueError("scenarios must not be empty")

    values = dict(DEFAULT_CAPACITY_ASSUMPTIONS if assumptions is None else assumptions)
    required_assumptions = {
        "staff_fte",
        "monthly_caseload_per_fte",
        "utilization_rate",
    }
    missing_assumptions = required_assumptions.difference(values)
    if missing_assumptions:
        raise ValueError(
            f"Missing capacity assumptions: {sorted(missing_assumptions)}"
        )

    capacity = calculate_monthly_capacity(
        float(values["staff_fte"]),
        float(values["monthly_caseload_per_fte"]),
        float(values["utilization_rate"]),
    )

    frame = scenarios.loc[:, ["scenario", "date", "scenario_demand"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["scenario_demand"] = pd.to_numeric(
        frame["scenario_demand"], errors="raise"
    )

    if (frame["scenario_demand"] < 0).any():
        raise ValueError("Scenario demand must be nonnegative")

    frame["staff_fte"] = float(values["staff_fte"])
    frame["monthly_caseload_per_fte"] = float(
        values["monthly_caseload_per_fte"]
    )
    frame["utilization_rate"] = float(values["utilization_rate"])
    frame["monthly_capacity"] = capacity
    frame["served_demand"] = np.minimum(
        frame["scenario_demand"], frame["monthly_capacity"]
    )
    frame["unmet_demand"] = np.maximum(
        frame["scenario_demand"] - frame["monthly_capacity"], 0.0
    )
    frame["surplus_capacity"] = np.maximum(
        frame["monthly_capacity"] - frame["scenario_demand"], 0.0
    )
    frame["capacity_utilization"] = np.where(
        frame["monthly_capacity"] > 0,
        frame["served_demand"] / frame["monthly_capacity"],
        np.where(frame["scenario_demand"] > 0, np.nan, 0.0),
    )

    return frame.sort_values(["date", "scenario"]).reset_index(drop=True)


def summarize_capacity(results: pd.DataFrame) -> pd.DataFrame:
    required = {
        "scenario",
        "scenario_demand",
        "monthly_capacity",
        "served_demand",
        "unmet_demand",
        "surplus_capacity",
    }
    missing = required.difference(results.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if results.empty:
        raise ValueError("results must not be empty")

    summary = (
        results.groupby("scenario", as_index=False)
        .agg(
            months=("scenario_demand", "size"),
            total_demand=("scenario_demand", "sum"),
            total_capacity=("monthly_capacity", "sum"),
            served_demand=("served_demand", "sum"),
            unmet_demand=("unmet_demand", "sum"),
            surplus_capacity=("surplus_capacity", "sum"),
            peak_monthly_demand=("scenario_demand", "max"),
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
