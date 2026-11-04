from pathlib import Path

import pandas as pd

from src.forecasting.backtesting import prepare_monthly_series
from src.scenarios.demand import (
    build_demand_scenarios,
    build_naive_reference,
    summarize_scenarios,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "data" / "processed" / "rpc_national_month.csv"
OUTPUT_DIR = ROOT / "analysis"


def main() -> None:
    frame = pd.read_csv(INPUT_PATH)
    history = prepare_monthly_series(frame)

    reference = build_naive_reference(history, horizon=6)
    scenarios = build_demand_scenarios(reference)
    summary = summarize_scenarios(scenarios)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reference.to_csv(OUTPUT_DIR / "demand_reference_forecast.csv", index=False)
    scenarios.to_csv(OUTPUT_DIR / "demand_scenarios.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "demand_scenario_summary.csv", index=False)

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
