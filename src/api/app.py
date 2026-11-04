from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
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

app = FastAPI(
    title="Refugee Resettlement Capacity Planning API",
    version="0.1.0",
    description=(
        "Decision-support API for refugee-arrival forecasting benchmarks, "
        "planning scenarios, service capacity, and resource optimization."
    ),
)


class PlanningRequest(BaseModel):
    reference_monthly_demand: float = Field(default=193.0, ge=0)
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


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "refugee-resettlement-capacity-planning",
        "version": app.version,
    }


@app.get("/v1/forecast/benchmark")
def forecast_benchmark() -> dict:
    frame = _read_csv(ANALYSIS_DIR / "forecast_backtest_summary.csv")
    return {"results": _records(frame)}


@app.get("/v1/scenarios")
def scenario_summary() -> dict:
    frame = _read_csv(ANALYSIS_DIR / "demand_scenario_summary.csv")
    return {"results": _records(frame)}


@app.get("/v1/capacity")
def capacity_summary() -> dict:
    frame = _read_csv(ANALYSIS_DIR / "capacity_summary.csv")
    return {"results": _records(frame)}


@app.get("/v1/optimization")
def optimization_summary() -> dict:
    frame = _read_csv(ANALYSIS_DIR / "constrained_optimization_summary.csv")
    return {"results": _records(frame)}


@app.post("/v1/plan")
def create_plan(request: PlanningRequest) -> dict:
    national = _read_csv(NATIONAL_MONTH_PATH)
    state_month = _read_csv(STATE_MONTH_PATH)

    latest_date = pd.to_datetime(national["date"], errors="raise").max()
    future_dates = pd.date_range(
        latest_date + pd.offsets.MonthBegin(1),
        periods=request.horizon_months,
        freq="MS",
    )
    reference = pd.DataFrame(
        {
            "date": future_dates,
            "forecast": request.reference_monthly_demand,
        }
    )

    scenarios = build_demand_scenarios(
        reference,
        {
            "lower": request.lower_multiplier,
            "baseline": 1.0,
            "higher": request.higher_multiplier,
        },
    )
    state_shares = build_state_shares(state_month, fiscal_year=2024)
    state_scenarios = allocate_scenario_demand_to_states(
        scenarios,
        state_shares,
    )
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

    summary = summarize_constrained_optimization(optimized)

    return {
        "assumptions": request.model_dump(),
        "reference_start_date": future_dates[0].strftime("%Y-%m-%d"),
        "reference_end_date": future_dates[-1].strftime("%Y-%m-%d"),
        "scenario_summary": _records(summary),
    }
