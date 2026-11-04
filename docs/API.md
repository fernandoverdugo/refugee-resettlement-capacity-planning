# Decision-support API

## Purpose

The API exposes the analytical pipeline without duplicating its modeling logic. Forecasting, scenario, capacity, and optimization functions remain in their existing modules; FastAPI provides a small interface for applications and external clients.

## Run locally

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the service:

```bash
uvicorn src.api.app:app --reload
```

FastAPI then provides interactive OpenAPI documentation at:

```text
/docs
```

## Endpoints

### `GET /health`

Returns service status and API version.

### `GET /v1/defaults`

Returns application defaults derived from committed validated data, including the latest national monthly arrival value and the latest reconciled state-share fiscal year.

### `GET /v1/forecast/benchmark`

Returns the committed rolling-origin forecast benchmark table.

### `GET /v1/scenarios`

Returns the default lower, baseline, and higher demand scenario summary.

### `GET /v1/capacity`

Returns the default service-capacity evaluation.

### `GET /v1/optimization`

Returns the default constrained-optimization summary.

### `POST /v1/plan`

Runs the planning pipeline with user-specified assumptions.

Example request:

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

The response includes the submitted assumptions, planning horizon, and scenario-level optimization results.

## Design principles

- API routes orchestrate existing analytical modules rather than reimplementing them.
- Input bounds are validated with Pydantic.
- Infeasible optimization requests return an HTTP 422 response.
- Analytical output files remain reproducible through the repository scripts.
- The API describes hypothetical service-resource planning, not refugee placement recommendations.

## Next step

The API is intended to support the interactive decision-support interface. The front end can use `POST /v1/plan` to let users adjust assumptions and immediately compare coverage, unmet demand, staffing use, and cost across scenarios.


## Data-driven defaults

`reference_monthly_demand` is optional in `POST /v1/plan`. When omitted, the API uses the latest validated value in `data/processed/rpc_national_month.csv`.

The state-share year is selected from the latest fiscal year present in the validated state-month panel rather than being hard-coded in the route.
