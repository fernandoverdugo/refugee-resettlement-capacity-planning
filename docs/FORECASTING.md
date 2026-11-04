# Forecasting methodology

## Purpose

The forecasting layer estimates near-term refugee-arrival demand for planning scenarios. Forecasts are treated as uncertain operational inputs, not as predictions of federal policy or individual placement decisions.

## Current benchmark scope

The repository currently contains a validated national monthly arrival series for FY2021–FY2025 and a fully reconciled state-month panel for FY2024.

A single state-level year is not sufficient for credible monthly seasonal forecasting. The first forecasting milestone therefore uses the longer national series to establish the time-aware evaluation framework. State-level forecasting will be added when the ingestion layer supports a sufficiently long reconciled monthly panel.

## Validation design

The benchmark uses expanding-window rolling-origin backtesting.

For each forecast origin:

1. only observations available through that month are used for training;
2. the next one to three months are forecast;
3. predictions are compared with the observed values;
4. the training window expands by one month;
5. the process repeats through the end of the series.

This design prevents future observations from leaking into model fitting and better reflects how the system would operate in production.

## Models

### Naive

The most recent observed monthly arrival count is repeated across the forecast horizon.

### Seasonal naive

The corresponding values from the most recent 12-month seasonal cycle are repeated.

### Simple exponential smoothing

A level-only exponential smoothing model is re-estimated at every forecast origin. It adapts to recent changes in the series without imposing a seasonal pattern or deterministic trend.

### SARIMA

The first seasonal autoregressive challenger is SARIMA(1,1,0)×(1,0,0,12). It combines first differencing, short-run autoregression, and a 12-month seasonal autoregressive term. The specification is intentionally compact because the available monthly history is short.

These models provide increasingly flexible benchmarks while remaining interpretable. More complex models should only be retained if they demonstrate consistent out-of-sample improvement.

## Metrics

Results are summarized separately for each forecast horizon using:

- MAE — mean absolute error
- RMSE — root mean squared error
- WAPE — total absolute error divided by total observed arrivals
- sMAPE — symmetric mean absolute percentage error

WAPE and sMAPE are reported as ratios. They should be interpreted alongside the scale-dependent MAE and RMSE, especially when monthly arrival counts approach zero.

## Current benchmark results

Using the FY2021–FY2025 national monthly panel with a 24-month minimum training window:

| Model | Horizon | MAE | RMSE | WAPE |
| --- | ---: | ---: | ---: | ---: |
| Naive | 1 month | 1,680 | 2,908 | 30.5% |
| Simple exponential smoothing | 1 month | 1,927 | 3,108 | 35.0% |
| SARIMA | 1 month | 1,931 | 3,146 | 35.1% |
| Seasonal naive | 1 month | 4,238 | 5,415 | 77.0% |
| Simple exponential smoothing | 2 months | 2,462 | 3,777 | 44.0% |
| Naive | 2 months | 2,466 | 3,975 | 44.0% |
| SARIMA | 2 months | 2,665 | 4,217 | 47.6% |
| Seasonal naive | 2 months | 4,309 | 5,483 | 76.9% |
| Naive | 3 months | 2,576 | 3,971 | 45.2% |
| Simple exponential smoothing | 3 months | 2,646 | 3,912 | 46.4% |
| SARIMA | 3 months | 2,765 | 4,134 | 48.5% |
| Seasonal naive | 3 months | 4,418 | 5,563 | 77.5% |

The naive model remains the strongest overall benchmark. Simple exponential smoothing and SARIMA are close at the one-month horizon but do not consistently improve on the last-observation baseline. Seasonal naive performs substantially worse.

This pattern is consistent with a series affected by large level shifts and abrupt policy-driven changes. The sharp decline in arrivals during FY2025 is especially difficult for models that rely on historical seasonal structure.

The result should not be interpreted as evidence that forecasting is impossible. It means future models need to be evaluated against a strong adaptive baseline and may benefit from explicit regime, policy, or scenario information rather than additional time-series complexity alone.

## Reproduction

Run:

```bash
python scripts/run_forecast_backtest.py
```

The script writes:

```text
analysis/forecast_backtest_predictions.csv
analysis/forecast_backtest_summary.csv
```

## Next modeling step

The next challenger is lag-based gradient boosting using only information available at each forecast origin. Given the observed structural breaks, the planning system should also support scenario-based forecasts that can override purely historical extrapolation when policy conditions change.
