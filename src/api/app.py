from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.optimization.allocation import (
    allocate_scenario_demand_to_states,
    build_state_shares,
)
from src.optimization.constrained import (
    build_planning_constraints,
    optimize_all_constrained_scenarios,
    summarize_constrained_optimization,
)
from src.scenarios.demand import build_demand_scenarios


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_DIR = ROOT / "analysis"
STATE_MONTH_PATH = ROOT / "data" / "processed" / "rpc_state_month.csv"
NATIONAL_MONTH_PATH = ROOT / "data" / "processed" / "rpc_national_month.csv"
WEB_APP_PATH = Path(__file__).resolve().parent / "static" / "index.html"

app = FastAPI(
    title="Refugee Resettlement Capacity Planning API",
    version="0.1.0",
    description=(
        "Decision-support API for refugee-arrival forecasting benchmarks, "
        "planning scenarios, service capacity, and resource optimization."
    ),
)


class PlanningRequest(BaseModel):
    reference_monthly_demand: float | None = Field(default=None, ge=0)
    horizon_months: int = Field(default=6, ge=1, le=24)
    lower_multiplier: float = Field(default=0.5, ge=0)
    higher_multiplier: float = Field(default=1.5, ge=0)
    total_fte: float = Field(default=8.0, ge=0)
    monthly_caseload_per_fte: float = Field(default=30.0, ge=0)
    utilization_rate: float = Field(default=0.85, ge=0, le=1)
    monthly_cost_per_fte: float = Field(default=7500.0, ge=0)
    monthly_budget: float = Field(default=60000.0, ge=0)
    ceiling_multiplier: float = Field(default=1.5, ge=0)
    minimum_state_fte: float = Field(default=0.10, ge=0)
    minimum_coverage: float = Field(default=0.0, ge=0, le=1)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Required analytical output is unavailable: {path.name}",
        )
    return pd.read_csv(path)


def _records(frame: pd.DataFrame) -> list[dict]:
    clean = frame.copy()
    for column in clean.columns:
        if pd.api.types.is_datetime64_any_dtype(clean[column]):
            clean[column] = clean[column].dt.strftime("%Y-%m-%d")
    return clean.where(pd.notna(clean), None).to_dict(orient="records")


def _latest_reference(national: pd.DataFrame) -> tuple[pd.Timestamp, float]:
    dates = pd.to_datetime(national["date"], errors="raise")
    arrivals = pd.to_numeric(national["arrivals"], errors="raise")
    latest_index = dates.idxmax()
    return dates.loc[latest_index], float(arrivals.loc[latest_index])


def _planning_basis() -> tuple[pd.Timestamp, float, pd.DataFrame, int]:
    national = _read_csv(NATIONAL_MONTH_PATH)
    state_month = _read_csv(STATE_MONTH_PATH)
    latest_date, latest_arrivals = _latest_reference(national)
    state_shares = build_state_shares(state_month)
    share_year = int(state_shares["share_fiscal_year"].iloc[0])
    return latest_date, latest_arrivals, state_shares, share_year


def _summarize_states(results: pd.DataFrame) -> pd.DataFrame:
    summary = (
        results.groupby(["scenario", "state"], as_index=False)
        .agg(
            total_demand=("state_demand", "sum"),
            served_demand=("served_demand", "sum"),
            unmet_demand=("unmet_demand", "sum"),
            allocated_fte_months=("allocated_fte", "sum"),
            total_cost=("monthly_cost", "sum"),
        )
    )
    summary["service_coverage_rate"] = summary["served_demand"].div(
        summary["total_demand"].where(summary["total_demand"] > 0, 1.0)
    )
    summary.loc[summary["total_demand"] <= 0, "service_coverage_rate"] = 1.0
    return summary.sort_values(
        ["scenario", "unmet_demand", "total_demand"],
        ascending=[True, False, False],
    ).reset_index(drop=True)


@app.get("/", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse(WEB_APP_PATH)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "refugee-resettlement-capacity-planning",
        "version": app.version,
    }


@app.get("/v1/defaults")
def planning_defaults() -> dict:
    latest_date, latest_arrivals, _, share_year = _planning_basis()
    return {
        "reference_monthly_demand": latest_arrivals,
        "reference_observation_date": latest_date.strftime("%Y-%m-%d"),
        "state_share_fiscal_year": share_year,
        "horizon_months": 6,
        "lower_multiplier": 0.5,
        "higher_multiplier": 1.5,
        "total_fte": 8.0,
        "monthly_caseload_per_fte": 30.0,
        "utilization_rate": 0.85,
        "monthly_cost_per_fte": 7500.0,
        "monthly_budget": 60000.0,
        "ceiling_multiplier": 1.5,
        "minimum_state_fte": 0.10,
        "minimum_coverage": 0.0,
    }


@app.get("/v1/forecast/benchmark")
def forecast_benchmark() -> dict:
    return {"results": _records(_read_csv(ANALYSIS_DIR / "forecast_backtest_summary.csv"))}


@app.get("/v1/scenarios")
def scenario_summary() -> dict:
    return {"results": _records(_read_csv(ANALYSIS_DIR / "demand_scenario_summary.csv"))}


@app.get("/v1/capacity")
def capacity_summary() -> dict:
    return {"results": _records(_read_csv(ANALYSIS_DIR / "capacity_summary.csv"))}


@app.get("/v1/optimization")
def optimization_summary() -> dict:
    return {"results": _records(_read_csv(ANALYSIS_DIR / "constrained_optimization_summary.csv"))}


@app.post("/v1/plan")
def create_plan(request: PlanningRequest) -> dict:
    latest_date, latest_arrivals, state_shares, share_year = _planning_basis()
    reference_monthly_demand = (
        latest_arrivals
        if request.reference_monthly_demand is None
        else request.reference_monthly_demand
    )
    future_dates = pd.date_range(
        latest_date + pd.offsets.MonthBegin(1),
        periods=request.horizon_months,
        freq="MS",
    )
    reference = pd.DataFrame(
        {"date": future_dates, "forecast": reference_monthly_demand}
    )
    scenarios = build_demand_scenarios(
        reference,
        {
            "lower": request.lower_multiplier,
            "baseline": 1.0,
            "higher": request.higher_multiplier,
        },
    )
    state_scenarios = allocate_scenario_demand_to_states(scenarios, state_shares)
    constraints = build_planning_constraints(
        state_shares,
        total_fte=request.total_fte,
        monthly_cost_per_fte=request.monthly_cost_per_fte,
        ceiling_multiplier=request.ceiling_multiplier,
        minimum_state_fte=request.minimum_state_fte,
    )

    try:
        optimized = optimize_all_constrained_scenarios(
            state_scenarios,
            constraints,
            monthly_budget=request.monthly_budget,
            total_fte=request.total_fte,
            monthly_caseload_per_fte=request.monthly_caseload_per_fte,
            utilization_rate=request.utilization_rate,
            minimum_coverage=request.minimum_coverage,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    assumptions = request.model_dump()
    assumptions["reference_monthly_demand"] = reference_monthly_demand

    return {
        "assumptions": assumptions,
        "reference_observation_date": latest_date.strftime("%Y-%m-%d"),
        "reference_start_date": future_dates[0].strftime("%Y-%m-%d"),
        "reference_end_date": future_dates[-1].strftime("%Y-%m-%d"),
        "state_share_fiscal_year": share_year,
        "scenario_summary": _records(summarize_constrained_optimization(optimized)),
        "state_summary": _records(_summarize_states(optimized)),
    }
