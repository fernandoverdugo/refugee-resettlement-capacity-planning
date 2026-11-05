# Decision-support API

## Purpose

The FastAPI layer exposes the forecasting, scenario, capacity, and optimization pipeline without duplicating modeling logic. It powers both the interactive planner and external programmatic access.

## Run locally

```bash
python -m pip install -r requirements.txt
uvicorn src.api.app:app --reload
```

The application then provides:

- `/` — interactive planner
- `/docs` — OpenAPI documentation
- `/health` — service health

## Endpoints

### `GET /health`

Returns service status and API version.

### `GET /v1/defaults`

Returns application defaults derived from committed validated data, including the latest national monthly arrival value and latest reconciled state-share fiscal year.

### `GET /v1/forecast/benchmark`

Returns the committed rolling-origin forecast benchmark summary.

### `GET /v1/scenarios`

Returns the default lower, baseline, and higher demand scenario summary.

### `GET /v1/capacity`

Returns the default fixed-capacity evaluation.

### `GET /v1/optimization`

Returns the default constrained-optimization summary.

### `POST /v1/plan`

Runs the planning pipeline with user-specified assumptions.

Example:

```json
{
  "reference_monthly_demand": 193,
  "horizon_months": 6,
  "lower_multiplier": 0.5,
  "higher_multiplier": 1.5,
  "total_fte": 8,
  "monthly_caseload_per_fte": 30,
  "utilization_rate": 0.85,
  "monthly_cost_per_fte": 7500,
  "monthly_budget": 60000,
  "ceiling_multiplier": 1.5,
  "minimum_state_fte": 0.1,
  "minimum_coverage": 0
}
```

The response includes submitted assumptions, planning dates, the state-share fiscal year, and scenario-level optimization results.

## Data-driven defaults

`reference_monthly_demand` is optional. When omitted, the API uses the latest validated value in `data/processed/rpc_national_month.csv`.

State shares are selected from the latest fiscal year present in the validated state-month panel rather than hard-coded in the API.

## Design principles

- API routes orchestrate existing analytical modules.
- Pydantic validates input bounds.
- Infeasible optimization requests return HTTP 422.
- Analytical outputs remain reproducible through repository scripts.
- The API describes service-resource planning, not refugee-placement recommendations.

The deployed web interface uses `POST /v1/plan` to compare coverage, unmet demand, staffing use, cost, and binding constraints across user-defined scenarios.
