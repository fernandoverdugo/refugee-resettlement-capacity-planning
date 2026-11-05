# Service capacity model

## Purpose

The capacity layer translates operational assumptions into a transparent monthly service-capacity limit and compares that capacity with each demand scenario.

It does not estimate the true staffing model of a specific resettlement agency. Default staffing, caseload, utilization, and cost values are hypothetical planning assumptions that users can change.

## Default assumptions

| Assumption | Default | Meaning |
| --- | ---: | --- |
| Staff FTE | 8.0 | Full-time-equivalent staff available for service |
| Monthly caseload per FTE | 30 | Maximum monthly cases per FTE before utilization adjustment |
| Utilization rate | 85% | Share of theoretical capacity assumed usable |

Default monthly capacity:

```text
8 FTE × 30 cases per FTE × 0.85 utilization = 204 cases/month
```

## Capacity measures

For each scenario and month, the model calculates:

- **served demand**
- **unmet demand**
- **surplus capacity**
- **capacity utilization**
- **overall service coverage**

## Current example

| Scenario | Six-month demand | Six-month capacity | Unmet demand | Coverage |
| --- | ---: | ---: | ---: | ---: |
| Lower | 579 | 1,224 | 0 | 100% |
| Baseline | 1,158 | 1,224 | 0 | 100% |
| Higher | 1,737 | 1,224 | 513 | 70.5% |

The higher-demand scenario exposes a capacity gap even though lower and baseline demand remain fully serviceable under the same staffing assumptions.

## Relationship to optimization

This fixed-capacity layer provides a transparent benchmark. The implemented constrained optimization layer extends it by allocating limited service resources across state planning units subject to:

- total FTE
- monthly budget
- state-specific FTE ceilings
- per-FTE costs
- optional minimum service-coverage requirements

## Reproduction

Run:

```bash
python scripts/evaluate_service_capacity.py
```

The script generates:

```text
analysis/capacity_evaluation.csv
analysis/capacity_summary.csv
```
