# Resource allocation optimization

## Purpose

The optimization layer allocates a limited pool of hypothetical service capacity across state planning units after a demand scenario has been selected.

The model does not recommend where refugees should be placed. It allocates service resources against an already specified planning-demand distribution.

## State demand distribution

The current national demand scenarios do not yet contain state-level forecasts. To create a transparent planning distribution, the optimizer uses each state's share of validated FY2024 refugee arrivals.

FY2024 contains 100,034 arrivals across 51 state-level planning units in the reconciled panel. The largest historical shares are Texas, California, New York, Florida, and Pennsylvania.

For each scenario month:

```text
state demand = national scenario demand × FY2024 state arrival share
```

This is a planning assumption, not a forecast that future state shares will remain unchanged. It can be replaced when a longer state-month forecasting panel becomes available.

## Optimization objective

The first optimization benchmark uses a max-min fairness objective.

Given a fixed total staffing pool, the linear program maximizes the minimum service-coverage rate across states. In other words, if capacity is insufficient, the model avoids fully serving some states while leaving others with very low coverage.

The optimization is solved in two stages:

1. maximize the minimum state coverage rate;
2. holding that fairness level, maximize total served demand.

## Default capacity assumptions

The optimizer uses the same assumptions as the capacity model:

| Assumption | Default |
| --- | ---: |
| Total FTE | 8 |
| Monthly caseload per FTE | 30 |
| Utilization rate | 85% |
| Effective capacity per FTE | 25.5 cases/month |
| Total monthly capacity | 204 cases/month |

## Current scenario behavior

Because the lower and baseline scenarios are below 204 cases per month, the optimizer can provide full coverage while leaving some FTE capacity unused.

The higher-demand scenario contains 289.5 cases per month. With only 204 cases of monthly capacity, the maximum equitable coverage rate is approximately 70.5%. Under the fairness objective, each state receives approximately the same 70.5% service coverage rather than concentrating capacity in a small number of states.

## Reproduction

Run:

```bash
python scripts/run_resource_optimization.py
```

The script creates:

```text
analysis/optimization_state_shares.csv
analysis/optimization_state_demand.csv
analysis/optimization_allocations.csv
analysis/optimization_summary.csv
```

## Interpretation

This is an optimization benchmark, not a final policy rule. Equal staff productivity is currently assumed across states because the project does not yet contain validated agency-level cost or staffing data.

Future versions can add:

- state-specific operating costs
- state-specific staffing ceilings
- minimum coverage requirements
- budget constraints
- ACS-based contextual capacity indicators
- alternative fairness objectives

Any such constraints should remain explicit and user-configurable rather than being hidden inside the objective function.
