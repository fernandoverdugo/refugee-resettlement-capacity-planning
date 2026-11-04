from pathlib import Path

import pandas as pd

from src.forecasting.backtesting import (
    prepare_monthly_series,
    rolling_origin_backtest,
    summarize_backtest,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "rpc_national_month.csv"
OUTPUT_DIR = ROOT / "analysis"


def main() -> None:
    frame = pd.read_csv(INPUT_PATH)
    series = prepare_monthly_series(frame)
    results = rolling_origin_backtest(
        series,
        min_train=24,
        max_horizon=3,
        season_length=12,
    )
    summary = summarize_backtest(results)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_DIR / "forecast_backtest_predictions.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "forecast_backtest_summary.csv", index=False)

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
