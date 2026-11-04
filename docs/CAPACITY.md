# Service capacity model

## Purpose

The capacity layer translates operational assumptions into a transparent monthly service-capacity limit and compares that capacity against each demand scenario.

It is not intended to estimate the true staffing model of any specific resettlement agency. The default values are hypothetical planning assumptions that can be changed by the user.

## Default assumptions

| Assumption | Default | Meaning |
| --- | ---: | --- |
| Staff FTE | 8.0 | Full-time-equivalent staff available for direct service |
| Monthly caseload per FTE | 30 | Maximum monthly cases per FTE before utilization adjustment |
| Utilization rate | 85% | Share of theoretical capacity assumed to be operationally usable |

The default monthly capacity is therefore:

```text
8 FTE × 30 cases per FTE × 0.85 utilization = 204 cases/month
```

## Capacity measures

For each scenario and month, the model calculates:

- **served demand** — the smaller of demand and available capacity
- **unmet demand** — demand above available capacity
- **surplus capacity** — available capacity above demand
- **capacity utilization** — served demand divided by available capacity

The summary output also reports the overall service-coverage rate for each scenario.

## Current example

Using the current six-month demand scenarios and the default monthly capacity of 204:

| Scenario | Six-month demand | Six-month capacity | Unmet demand | Coverage |
| --- | ---: | ---: | ---: | ---: |
| Lower | 579 | 1,224 | 0 | 100% |
| Baseline | 1,158 | 1,224 | 0 | 100% |
| Higher | 1,737 | 1,224 | 513 | 70.5% |

The higher-demand scenario therefore exposes a capacity gap even though the lower and baseline scenarios remain fully serviceable under the same staffing assumptions.

## Reproduction

Run:

```bash
python scripts/evaluate_service_capacity.py
```

The script creates:

```text
analysis/capacity_evaluation.csv
analysis/capacity_summary.csv
```

## Next step

The next milestone is constrained optimization. Instead of assuming fixed staffing everywhere, the optimization layer will allocate limited service resources across demand locations or planning units subject to budget, staffing, and minimum-coverage constraints.
