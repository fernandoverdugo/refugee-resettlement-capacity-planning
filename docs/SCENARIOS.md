# Demand scenario framework

## Purpose

The scenario layer separates empirical forecasting from policy-sensitive planning assumptions.

The national arrival series contains abrupt level shifts that historical models cannot reliably anticipate. Rather than hiding those assumptions inside a more complicated forecast, the platform keeps them explicit and user-configurable.

## Reference forecast

The default reference uses the strongest overall rolling-origin benchmark: the naive forecast.

The most recent validated national monthly arrival count is carried forward across the selected horizon. The API and web planner can override that reference value without changing the underlying scenario engine.

## Default scenarios

| Scenario | Multiplier | Interpretation |
| --- | ---: | --- |
| Lower | 0.50 | 50% of reference demand |
| Baseline | 1.00 | reference demand |
| Higher | 1.50 | 150% of reference demand |

These are planning assumptions, not probability statements.

## How scenarios are used

The scenario layer feeds both the fixed-capacity benchmark and the constrained allocation model. It supports questions such as:

- What happens if arrivals rise above the current reference?
- How much unmet demand appears under current staffing?
- How sensitive are staffing and funding requirements to the demand assumption?
- How does the fair allocation change when demand changes?

The deployed planner exposes these multipliers as interactive controls.

## Outputs

Run:

```bash
python scripts/build_demand_scenarios.py
```

The script generates:

```text
analysis/demand_reference_forecast.csv
analysis/demand_scenarios.csv
analysis/demand_scenario_summary.csv
```

The default scripted planning horizon is six months; the API and interactive planner allow horizons from 1 to 24 months.
