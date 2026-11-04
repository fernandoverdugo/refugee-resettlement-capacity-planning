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

## Baseline models

### Naive

The most recent observed monthly arrival count is repeated across the forecast horizon.

### Seasonal naive

The corresponding values from the most recent 12-month seasonal cycle are repeated.

These baselines are intentionally simple. More complex models should only be retained if they demonstrate consistent out-of-sample improvement.

## Metrics

Results are summarized separately for each forecast horizon using:

- MAE — mean absolute error
- RMSE — root mean squared error
- WAPE — total absolute error divided by total observed arrivals
- sMAPE — symmetric mean absolute percentage error

WAPE and sMAPE are reported as ratios. They should be interpreted alongside the scale-dependent MAE and RMSE, especially when monthly arrival counts approach zero.

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

After baseline behavior is established, candidate models can include exponential smoothing, SARIMA, and lag-based gradient boosting. Model selection should remain based on rolling out-of-sample performance rather than in-sample fit.
