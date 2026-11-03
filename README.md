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

The U.S. Department of State Refugee Processing Center publishes refugee-arrival reports by state, nationality, and month. Historical state-and-nationality reports are available from FY2012 onward.

Primary analytical grain:

```text
state × calendar month
```

Nationality-level fields will be retained where available for descriptive analysis, but the first forecasting models will target total monthly arrivals by state.

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

- seasonal-naive baseline
- exponential smoothing
- SARIMA
- gradient boosting with lag/calendar features

Models will be evaluated with rolling-origin backtesting using metrics such as MAE, RMSE, and weighted absolute percentage error where appropriate.

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

**Phase 1 — Data engineering foundation**

The repository is being initialized with source documentation, configuration, tests, and reproducible ingestion scaffolding.

## Technologies

Python · pandas · NumPy · scikit-learn · statsmodels · SciPy · PostgreSQL · FastAPI · Docker · pytest · GitHub Actions

## License

MIT
