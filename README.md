# Refugee Resettlement Capacity & Resource Planning

A forecasting and optimization platform for refugee resettlement demand, service capacity, and resource allocation.

## Project objective

Public-service organizations often need to make staffing, funding, and service-capacity decisions before future demand is fully known. This project develops a reproducible decision-support system that:

1. builds a historical monthly panel of U.S. refugee arrivals,
2. forecasts near-term arrivals at the state level,
3. evaluates forecasts with rolling out-of-sample backtests,
4. combines demand forecasts with transparent capacity indicators,
5. allocates limited resources under configurable operational constraints, and
6. exposes the results through an interactive planning application.

The goal is not to prescribe refugee placement or make individual-level decisions. The optimization layer is designed as a planning exercise for allocating hypothetical service resources after demand assumptions are specified.

## Planned data sources

### Refugee Processing Center

The U.S. Department of State Refugee Processing Center publishes refugee-arrival reports by state and nationality from FY2012 onward. The archived source format changes over time:

- **FY2012–FY2020:** legacy Excel files provide state-level fiscal-year totals.
- **FY2021–present:** PDF reports contain monthly state-level detail that can be normalized into a complete state-month panel.

The ingestion layer therefore produces two analytical datasets:

```text
state × fiscal year   (FY2012–present)
state × calendar month (FY2021–present)
```

The monthly panel is the primary forecasting dataset. The longer annual panel is retained for historical trend analysis, capacity context, and scenario design.

### U.S. Census Bureau American Community Survey

ACS data will provide state-level socioeconomic and housing context for the capacity-planning layer. Candidate indicators include:

- population
- poverty
- unemployment
- median household income
- housing-cost burden
- rental vacancy
- limited-English-speaking households
- foreign-born population

ACS measures will be treated as contextual capacity indicators, not as causal explanations for federal resettlement decisions.

## Analytical roadmap

### Phase 1 — Data engineering
- Acquire and archive Refugee Processing Center reports.
- Normalize fiscal-year reports into a consistent state-month panel.
- Add validation checks and source metadata.
- Build reproducible Census API ingestion.
- Create an analytical database-ready dataset.

### Phase 2 — Demand forecasting
Benchmark several forecasting approaches:

- naive and seasonal-naive baselines
- exponential smoothing
- SARIMA
- gradient boosting with lag/calendar features

Models are evaluated with expanding-window rolling-origin backtesting at 1–3 month horizons using MAE, RMSE, WAPE, and sMAPE.

### Phase 3 — Capacity and scenario modeling
Create transparent planning indicators and configurable scenarios for:

- baseline demand
- higher/lower arrival assumptions
- staffing capacity
- caseload limits
- available funding
- minimum service coverage

The first scenario engine is implemented with explicit lower (0.5×), baseline (1.0×), and higher (1.5×) demand assumptions applied to the validated reference forecast.

### Phase 4 — Resource optimization
Translate forecast demand into resource-allocation recommendations using constrained mathematical optimization.

The first optimization benchmark is now implemented. National scenario demand is distributed to states using validated FY2024 arrival shares, then a linear program allocates a fixed staffing pool using a max-min fairness objective that maximizes the minimum service-coverage rate across states.

Example objective:

> Maximize the minimum state service-coverage rate subject to a fixed staffing budget, state demand limits, and total service capacity.

### Phase 5 — Decision-support application
Build an interactive application where users can adjust planning assumptions and compare:

- expected demand
- uncertainty ranges
- resource requirements
- optimized allocations
- unmet demand
- alternative scenarios

The first application layer is now implemented as a FastAPI service. It exposes committed benchmark outputs and a parameterized planning endpoint that reruns the scenario and constrained-optimization pipeline from user-supplied assumptions.

## Planned architecture

```text
Refugee Processing Center reports      Census ACS API
              ↓                             ↓
        source ingestion               context ingestion
              ↓                             ↓
          validation ───────────────→ normalized data
                                      ↓
                              analytical storage
                                      ↓
                         forecasting + backtesting
                                      ↓
                              scenario engine
                                      ↓
                       constrained optimization
                                      ↓
                                  API layer
                                      ↓
                         interactive planning app
```

## Repository structure

```text
analysis/             validated analytical outputs
data/
  raw/                source snapshots (not all large files committed)
  processed/          normalized analytical datasets
docs/                 methodology and data documentation
src/
  ingestion/          source retrieval and parsing
  forecasting/        forecasting and backtesting
  optimization/       resource-allocation models
  scenarios/          planning assumptions
tests/                automated validation
.github/workflows/    CI and scheduled workflows
```

## ACS capacity layer

The planning layer uses U.S. Census Bureau ACS 5-year Data Profiles for state-level socioeconomic, housing, demographic, and language context. The initial feature set includes population, poverty, unemployment, household income, rental vacancy, median rent, renter cost burden, foreign-born population share, and a derived limited-English measure.

Census data queries require a `CENSUS_API_KEY`. Local runs read the key from the environment; GitHub Actions reads it from a repository secret. Variable metadata is validated independently so schema drift can be detected even when a live key is unavailable.

See `docs/ACS_CAPACITY.md` for field definitions and interpretation constraints.

## Forecasting benchmark

The first forecasting benchmark uses the validated national monthly series for FY2021–FY2025. State-level monthly forecasting is intentionally deferred until more than one fully reconciled state-month year is available.

Rolling-origin evaluation currently compares naive, seasonal-naive, simple exponential smoothing, SARIMA, and gradient-boosting forecasts. The naive model remains the strongest overall benchmark:

- **1-month MAE:** 1,680 arrivals; WAPE 30.5%
- **2-month MAE:** 2,466 arrivals; WAPE 44.0%
- **3-month MAE:** 2,576 arrivals; WAPE 45.2%

Neither SARIMA nor gradient boosting consistently improves on the naive model. Seasonal-naive forecasts perform substantially worse. The results show that abrupt policy-driven level shifts, especially the FY2025 decline, matter more than added model complexity in this short historical series.

See `docs/FORECASTING.md` for the validation design and `analysis/forecast_backtest_summary.csv` for the full benchmark table.

## Scenario and capacity planning

The scenario layer separates empirical forecasts from explicit planning assumptions. The default lower, baseline, and higher cases apply 0.5×, 1.0×, and 1.5× multipliers to the validated reference forecast.

The capacity layer then compares those scenarios with configurable staffing and caseload assumptions. Under the default capacity assumptions, the six-month higher-demand scenario exceeds available service capacity by 513 cases.

See `docs/SCENARIOS.md`, `docs/CAPACITY.md`, and `analysis/capacity_summary.csv` for assumptions, methodology, and outputs.

## Technical principles

- Reproducible public-data ingestion
- Explicit source provenance
- Time-aware model validation
- Baseline-first model comparison
- Transparent optimization constraints
- Separation of prediction from policy judgment
- Scenario analysis instead of false precision
- Automated tests and CI

## Status

**Phase 1 — Data engineering: operational**

The RPC ingestion layer discovers the official archive, handles legacy XLS/XLSX and modern PDF source formats, preserves source provenance and checksums, and publishes only analytical grains that pass exact reconciliation checks. A national monthly demand series is validated for FY2021–FY2025, while FY2024 provides a fully reconciled state-month allocation panel.

The ACS capacity layer is scaffolded with validated variable metadata, reproducible Census API ingestion, tests, documentation, and a secret-backed refresh workflow for state-level socioeconomic, housing, demographic, and language indicators.

**Phase 2 — Demand forecasting: in progress**

A leakage-safe rolling-origin forecasting framework is now implemented and tested. Naive, seasonal-naive, simple exponential smoothing, SARIMA, and lag-based gradient boosting have all been benchmarked on the real national monthly series. The naive model remains the strongest overall reference forecast.

Scenario-aware forecasting is now implemented. A six-month reference forecast is transformed into configurable lower-demand, baseline, and higher-demand planning cases, with assumptions kept separate from the empirical model.

**Phase 3 — Capacity and scenario modeling: in progress**

The demand scenario engine is operational and produces reproducible lower, baseline, and higher planning cases. A service-capacity model now converts staffing, caseload, and utilization assumptions into monthly operational capacity and quantifies served demand, unmet demand, surplus capacity, utilization, and service coverage.

Using the default assumption of 8 FTE, 30 cases per FTE per month, and 85% usable capacity, the system provides 204 cases of monthly capacity. Across the current six-month scenarios, lower and baseline demand are fully covered, while the higher-demand case produces 513 cases of unmet demand and a 70.5% coverage rate.

**Phase 4 — Resource optimization: in progress**

A state-level linear-programming benchmark is now operational. The current model uses FY2024 state arrival shares as a transparent planning distribution and allocates a fixed 8-FTE service pool across states.

Lower and baseline scenarios achieve full coverage. In the higher-demand scenario, monthly demand of 289.5 exceeds the 204-case service ceiling, so the optimizer equalizes state coverage at approximately 70.5% rather than concentrating resources in a small number of states.

See `docs/OPTIMIZATION.md`, `analysis/optimization_state_shares.csv`, and `analysis/optimization_summary.csv` for assumptions and results.

The richer constrained optimizer is now implemented with state-specific staffing ceilings, per-FTE costs, a monthly budget, a global FTE cap, and optional minimum coverage requirements. Under the default hypothetical cost assumptions, the higher-demand scenario uses the full $60,000 monthly staffing budget and still reaches only 70.5% coverage; lower and baseline demand remain fully serviceable.

ACS-based contextual constraints are intentionally deferred because a validated `data/processed/acs_state_capacity.csv` is not currently committed. The optimizer will not invent empirical capacity weights from unavailable data.

See `docs/CONSTRAINED_OPTIMIZATION.md` and `analysis/constrained_optimization_summary.csv` for the extended formulation and benchmark outputs.

**Phase 5 — Decision-support application: in progress**

A FastAPI backend now exposes health status, forecast benchmarks, scenario summaries, capacity results, optimization outputs, and a parameterized `POST /v1/plan` endpoint. The planning endpoint validates user assumptions and reuses the existing scenario and optimization modules rather than duplicating analytical logic.

A lightweight interactive web interface is also served from the application root. Users can adjust demand, horizon, staffing, utilization, cost, budget, state ceiling, and minimum-coverage assumptions and immediately compare scenario demand, served demand, unmet demand, coverage, staffing use, and cost.

Run locally with:

```bash
uvicorn src.api.app:app --reload
```

Open the root page for the planning interface or `/docs` for FastAPI's interactive API documentation.

See `docs/API.md` and `docs/APP.md` for endpoint definitions and interface behavior.

The next milestone is deployment and presentation polish: containerize the application, add a production health check, and make the decision-support interface easy to launch from the portfolio.

## Technologies

Python · pandas · NumPy · scikit-learn · statsmodels · SciPy · PostgreSQL · FastAPI · Docker · pytest · GitHub Actions

## License

MIT
