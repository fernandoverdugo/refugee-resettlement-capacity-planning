# Forecasting methodology

## Purpose

The forecasting layer estimates near-term refugee-arrival demand for planning scenarios. Forecasts are uncertain operational inputs, not predictions of federal policy or individual placement decisions.

## Current scope

The committed benchmark uses a validated **national monthly arrival series for FY2021–FY2025**. The repository also contains a fully reconciled **FY2024 state-month panel**, which is used to distribute national scenario demand across state planning units.

The state-month history is not yet long enough for credible state-level seasonal forecasting, so the forecasting benchmark remains national. State planning demand is therefore a scenario allocation, not a state-level forecast.

## Validation design

The benchmark uses expanding-window rolling-origin backtesting. At each origin, models are trained only on observations available at that time and evaluated one to three months ahead. This prevents future leakage and approximates operational forecasting.

## Models

- **Naive:** repeats the most recent observation.
- **Seasonal naive:** repeats the corresponding value from the latest 12-month cycle.
- **Simple exponential smoothing:** re-estimates a level-only model at each origin.
- **SARIMA:** compact SARIMA(1,1,0)×(1,0,0,12).
- **Gradient boosting:** recursive model using lags 1, 2, 3, and 12, trailing means, and calendar-month encodings.

The machine-learning model uses a fixed random seed and recursive multi-step predictions so future observed arrivals never enter lag features.

## Metrics

Results are summarized by forecast horizon using:

- MAE
- RMSE
- WAPE
- sMAPE

WAPE and sMAPE are ratios and should be interpreted alongside MAE and RMSE, especially when observed arrivals approach zero.

## Current benchmark results

| Model | 1-month MAE | 2-month MAE | 3-month MAE |
| --- | ---: | ---: | ---: |
| **Naive** | **1,680** | 2,466 | **2,576** |
| Simple exponential smoothing | 1,927 | **2,462** | 2,646 |
| SARIMA | 1,931 | 2,665 | 2,765 |
| Gradient boosting | 2,012 | 2,729 | 2,821 |
| Seasonal naive | 4,238 | 4,309 | 4,418 |

The naive model remains the strongest overall benchmark. Added model complexity does not consistently improve on the last-observation baseline.

That result is substantively important because the series contains abrupt policy-driven level shifts, including the sharp FY2025 decline. Historical models cannot reliably anticipate regime changes that have no analogue in their inputs.

The platform therefore separates two tasks:

1. use empirically validated forecasting as the reference baseline;
2. represent policy-sensitive uncertainty through explicit lower, baseline, and higher planning scenarios.

## Reproduction

Run:

```bash
python scripts/run_forecast_backtest.py
```

The script generates:

```text
analysis/forecast_backtest_predictions.csv
analysis/forecast_backtest_summary.csv
```

The repository commits the summary table used by the application and documentation. Detailed prediction rows can be regenerated locally from the validated monthly series.
