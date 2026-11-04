# Demand scenario framework

## Purpose

The scenario layer separates empirical forecasting from planning assumptions.

The forecasting benchmark shows that the national refugee-arrival series is affected by abrupt policy-driven level shifts that historical models cannot reliably anticipate. Rather than hiding those assumptions inside a more complicated forecasting algorithm, the planning system keeps them explicit.

## Reference forecast

The initial reference forecast uses the strongest overall rolling-origin benchmark: the naive forecast.

For the current national series, the most recent observed monthly arrival count is carried forward across the planning horizon. This reference can later be replaced by another validated model without changing the scenario engine.

## Default scenarios

The first scenario set applies transparent multipliers to the reference forecast:

| Scenario | Multiplier | Interpretation |
| --- | ---: | --- |
| Lower | 0.50 | Demand is 50% below the reference forecast |
| Baseline | 1.00 | Demand follows the reference forecast |
| Higher | 1.50 | Demand is 50% above the reference forecast |

These are planning assumptions, not probability statements. They are intentionally simple and configurable.

## Why explicit scenarios

This design allows the platform to answer questions such as:

- What staffing level is needed if arrivals remain near the current baseline?
- How much unmet service demand would occur under a 50% increase?
- How much capacity could be released if demand falls by half?
- How sensitive are resource-allocation recommendations to the demand assumption?

The assumptions remain visible to the user and can be changed independently of the underlying forecast.

## Outputs

Run:

```bash
python scripts/build_demand_scenarios.py
```

The script creates:

```text
analysis/demand_reference_forecast.csv
analysis/demand_scenarios.csv
analysis/demand_scenario_summary.csv
```

The default planning horizon is six months.

## Next step

The scenario outputs are designed to feed the capacity and optimization layers. The next milestone is to combine scenario demand with service-capacity assumptions such as caseload limits, staffing levels, and available funding.
