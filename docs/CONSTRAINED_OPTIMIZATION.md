# Constrained optimization extension

## Purpose

The first optimization benchmark allocates a fixed service-capacity pool using a max-min fairness objective. This extension adds operational constraints that are closer to real resource planning:

- a monthly budget
- state-specific FTE ceilings
- state-specific cost per FTE
- an optional minimum service-coverage requirement
- a global FTE limit

The model still does not decide refugee placement. It allocates hypothetical service resources against planning demand that has already been specified.

## Default planning assumptions

The helper used for the initial constrained benchmark creates transparent hypothetical constraints:

| Assumption | Default |
| --- | ---: |
| Total FTE pool | 8 |
| Monthly cost per FTE | $7,500 |
| Monthly budget | $60,000 |
| State FTE ceiling | 1.5× proportional FY2024 share |
| Minimum state FTE ceiling | 0.10 FTE |
| Caseload per FTE | 30 |
| Utilization | 85% |

These values are scenario assumptions, not measured agency staffing or cost estimates.

## Optimization logic

For each state, the optimizer chooses served demand subject to:

1. served demand cannot exceed projected state demand;
2. implied FTE cannot exceed the state's staffing ceiling;
3. total implied FTE cannot exceed the national FTE pool;
4. total staffing cost cannot exceed the monthly budget;
5. service coverage must meet any user-specified minimum coverage floor.

The objective remains max-min fairness:

1. maximize the minimum coverage rate across states;
2. while preserving that fairness level, maximize total served demand.

## ACS status

The repository contains validated ACS variable definitions and an ingestion workflow, but a processed `data/processed/acs_state_capacity.csv` is not currently committed.

For that reason, ACS indicators are **not yet used as optimization weights or constraints**. This avoids creating pseudo-empirical capacity scores from unavailable data.

Once the validated ACS state file is present, contextual housing, labor-market, and demographic indicators can be incorporated through explicit, documented constraint rules.

## Why this matters

The richer formulation allows the application to answer questions such as:

- What happens if the staffing budget falls while demand remains unchanged?
- Which states become binding because of staffing ceilings?
- What budget is required to guarantee a specified minimum coverage level?
- How does the allocation change when state operating costs differ?

These are operational planning questions rather than predictions of individual placement.
