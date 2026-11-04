# Refugee Resettlement Capacity & Resource Planning

A reproducible decision-support platform for forecasting refugee-arrival demand, testing service-capacity scenarios, and allocating hypothetical service resources under transparent constraints.

> **Scope:** This project does not recommend refugee placement or make individual-level decisions. Forecasts and optimization outputs are planning inputs for staffing, funding, and service-capacity analysis.

## What the project does

- Ingests and validates U.S. Refugee Processing Center arrival reports across changing XLS, XLSX, and PDF formats.
- Maintains a validated national monthly arrival series for FY2021–FY2025 and a reconciled FY2024 state-month panel.
- Benchmarks naive, seasonal-naive, exponential-smoothing, SARIMA, and gradient-boosting forecasts with leakage-safe rolling-origin validation.
- Converts a reference forecast into explicit lower, baseline, and higher demand scenarios.
- Evaluates staffing capacity, service coverage, surplus capacity, and unmet demand.
- Allocates a limited staffing pool across state planning units with max-min fair linear programming.
- Adds budget, FTE, state-ceiling, and minimum-coverage constraints.
- Exposes the pipeline through FastAPI and an interactive browser-based planning interface.
- Packages the application with Docker and validates the production image in GitHub Actions.

## Key findings

The national monthly series contains major policy-driven regime shifts, especially the sharp FY2025 decline. Added model complexity does not consistently outperform a strong adaptive baseline.

| Model | 1-month MAE | 2-month MAE | 3-month MAE |
| --- | ---: | ---: | ---: |
| **Naive** | **1,680** | 2,466 | **2,576** |
| Simple exponential smoothing | 1,927 | **2,462** | 2,646 |
| SARIMA | 1,931 | 2,665 | 2,765 |
| Gradient boosting | 2,012 | 2,729 | 2,821 |
| Seasonal naive | 4,238 | 4,309 | 4,418 |

That result motivates the project design: keep the empirical forecast as a benchmark, then represent policy-sensitive uncertainty through explicit scenarios instead of forcing historical models to predict regime changes.

Under the default hypothetical service assumptions — 8 FTE, 30 cases per FTE per month, 85% utilization, and a $60,000 monthly staffing budget — the six-month higher-demand scenario produces 513 cases of unmet demand and about 70.5% service coverage.

## Data and planning grain

### Refugee Processing Center

The ingestion layer handles:

- **FY2012–FY2020:** state-level fiscal-year totals from legacy Excel files.
- **FY2021–present:** monthly information from PDF reports where the source can be reconciled reliably.

Current validated analytical grains include:

```text
state × fiscal year
national × calendar month
state × calendar month (FY2024 fully reconciled)
```

The forecasting benchmark is currently **national**, not state-level. State planning demand is produced by applying the latest validated state arrival shares — currently FY2024 — to national scenario demand. This is an explicit planning assumption, not a state-level forecast.

### Census ACS

The repository includes ACS variable definitions, ingestion code, tests, and a secret-backed refresh workflow for contextual housing, labor-market, demographic, and language indicators.

A validated `data/processed/acs_state_capacity.csv` is not currently committed, so ACS measures are intentionally **not** used as optimization weights or constraints yet.

## Modeling pipeline

```text
RPC source reports
      ↓
ingestion + reconciliation
      ↓
validated analytical panels
      ↓
forecast benchmarking
      ↓
explicit demand scenarios
      ↓
service-capacity evaluation
      ↓
constrained fair allocation
      ↓
FastAPI
      ↓
interactive planning interface
```

### Forecasting

Rolling-origin backtesting uses expanding training windows and 1–3 month forecast horizons. Metrics include MAE, RMSE, WAPE, and sMAPE.

See `docs/FORECASTING.md`.

### Scenario and capacity modeling

Default scenarios apply configurable multipliers to the reference forecast:

- lower: 0.5×
- baseline: 1.0×
- higher: 1.5×

Capacity assumptions are kept separate from demand assumptions.

See `docs/SCENARIOS.md` and `docs/CAPACITY.md`.

### Optimization

The optimizer first maximizes the minimum state service-coverage rate, then maximizes total served demand while preserving that fairness level.

The constrained formulation supports:

- total FTE limits
- monthly budget limits
- state-specific FTE ceilings
- per-FTE costs
- optional minimum coverage requirements

Scenario summaries also identify how many months the budget or FTE constraint is binding.

See `docs/OPTIMIZATION.md` and `docs/CONSTRAINED_OPTIMIZATION.md`.

## Application

Run locally:

```bash
python -m pip install -r requirements.txt
uvicorn src.api.app:app --reload
```

Then open:

- `/` — interactive planner
- `/docs` — FastAPI/OpenAPI interface
- `/health` — health endpoint

The application loads its default reference demand from the latest validated national monthly observation and uses the latest reconciled state-share year available in the processed state-month panel.

See `docs/API.md` and `docs/APP.md`.

## Deployment

The production image uses a reduced runtime dependency set and includes only the application code, processed data, and committed analytical outputs required at request time.

```bash
docker build -t refugee-capacity-planner .
docker run --rm -p 10000:10000 refugee-capacity-planner
```

The repository includes:

- a Docker health check
- a Render deployment blueprint
- container-build CI
- separate analytical and production dependency sets

See `docs/DEPLOYMENT.md`.

## Repository structure

```text
analysis/             validated analytical outputs
data/
  raw/                source manifests / source snapshots
  processed/          normalized analytical datasets
docs/                 methodology and deployment documentation
scripts/              reproducible pipeline runners
src/
  api/                FastAPI + interactive interface
  forecasting/        forecasting and backtesting
  ingestion/          RPC and ACS ingestion
  optimization/       fair and constrained allocation
  scenarios/          demand and capacity scenarios
tests/                automated tests
.github/workflows/    CI, validation, refresh, and diagnostics
```

## Project status

| Layer | Status |
| --- | --- |
| RPC ingestion and reconciliation | ✅ Operational |
| National forecast benchmark | ✅ Implemented |
| Demand scenarios and capacity model | ✅ Implemented |
| Fair and constrained optimization | ✅ Implemented |
| FastAPI + interactive planner | ✅ Implemented |
| Docker deployment package | ✅ Implemented |
| Live public deployment | ⏳ Pending |
| ACS contextual optimization | ⏳ Deferred until validated processed ACS output is available |

## Technical principles

- baseline-first model comparison
- time-aware validation
- explicit source provenance
- transparent planning assumptions
- separation of prediction from policy judgment
- auditable optimization constraints
- automated testing and container validation

## Technologies

Python · pandas · NumPy · scikit-learn · statsmodels · SciPy · FastAPI · Docker · pytest · GitHub Actions

## License

MIT
