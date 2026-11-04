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

### Phase 4 — Resource optimization
Translate forecast demand into resource-allocation recommendations using constrained mathematical optimization.

Example objective:

> Minimize unmet forecast service demand subject to a fixed budget, minimum coverage requirements, staffing limits, and state-level capacity constraints.

### Phase 5 — Decision-support application
Build an interactive application where users can adjust planning assumptions and compare:

- expected demand
- uncertainty ranges
- resource requirements
- optimized allocations
- unmet demand
- alternative scenarios

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

Rolling-origin evaluation currently compares naive, seasonal-naive, and simple exponential smoothing forecasts. The naive model is the strongest overall benchmark:

- **1-month MAE:** 1,680 arrivals; WAPE 30.5%
- **2-month MAE:** 2,466 arrivals; WAPE 44.0%
- **3-month MAE:** 2,576 arrivals; WAPE 45.2%

Simple exponential smoothing is nearly tied at two months but does not consistently improve on the naive model. Seasonal-naive forecasts perform substantially worse, reflecting strong level shifts and the abrupt FY2025 decline.

See `docs/FORECASTING.md` for the validation design and `analysis/forecast_backtest_summary.csv` for the full benchmark table.

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

A leakage-safe rolling-origin forecasting framework is now implemented and tested. Naive, seasonal-naive, and simple exponential smoothing models have been benchmarked on the real national monthly series. The current results establish a strong naive baseline and show that historical seasonality alone does not handle the observed regime changes well.

Next challengers are SARIMA and lag-based gradient boosting, followed by scenario-aware forecasting for policy-driven demand shifts.

## Technologies

Python · pandas · NumPy · scikit-learn · statsmodels · SciPy · PostgreSQL · FastAPI · Docker · pytest · GitHub Actions

## License

MIT
