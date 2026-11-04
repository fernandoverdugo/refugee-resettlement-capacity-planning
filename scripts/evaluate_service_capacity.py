from pathlib import Path

import pandas as pd

from src.scenarios.capacity import evaluate_capacity, summarize_capacity


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "analysis" / "demand_scenarios.csv"
OUTPUT_DIR = ROOT / "analysis"


def main() -> None:
    scenarios = pd.read_csv(INPUT_PATH)
    results = evaluate_capacity(scenarios)
    summary = summarize_capacity(results)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_DIR / "capacity_evaluation.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "capacity_summary.csv", index=False)

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
