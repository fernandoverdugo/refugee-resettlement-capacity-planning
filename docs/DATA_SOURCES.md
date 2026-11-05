# Data sources

## Refugee Processing Center

**Publisher:** U.S. Department of State, Refugee Processing Center

The project uses current and archived Refugee Processing Center arrival reports and preserves source provenance through report names, source URLs, and retrieval timestamps.

### Current validated analytical coverage

The source formats vary substantially by fiscal year.

- **FY2012–FY2020:** legacy Excel workbooks support state-level fiscal-year totals.
- **FY2021–FY2025:** reconciled report totals support the national monthly series used for forecasting.
- **FY2024:** the repository contains a fully reconciled state × calendar-month panel used to derive state planning shares.

The project does not fabricate monthly state observations for years whose source structure has not been reconciled reliably.

Committed normalized outputs include:

```text
data/processed/rpc_state_fiscal_year.csv
data/processed/rpc_national_month.csv
data/processed/rpc_state_month.csv
```

The current state-month panel is used for state-share allocation. The national monthly panel is used for forecast benchmarking and reference demand.

RPC reports can be revised after initial publication, so retrieval metadata is preserved rather than assuming historical source files are immutable.

## American Community Survey

**Publisher:** U.S. Census Bureau

The repository includes state-level ACS ingestion code, variable validation, tests, and a secret-backed refresh workflow for contextual demographic, housing, labor-market, and language indicators.

Candidate fields include:

- total population
- poverty rate
- unemployment rate
- median household income
- rental vacancy rate
- median gross rent
- housing-cost burden
- foreign-born population share
- limited-English share

A validated `data/processed/acs_state_capacity.csv` is not currently committed. ACS indicators are therefore **not used as optimization weights or constraints in the live model**.

See `docs/ACS_CAPACITY.md` for the current variable definitions and refresh process.

## Interpretation

RPC arrivals describe observed admissions, not future policy commitments.

ACS measures describe state operating context and are not treated as causal determinants of refugee arrivals or as placement-suitability scores.

## Provenance requirements

Normalized sources preserve, where applicable:

- source organization
- source URL
- report or dataset vintage
- retrieval timestamp
- geographic grain
- temporal grain

Raw or normalized source updates should remain reproducible and auditable.
