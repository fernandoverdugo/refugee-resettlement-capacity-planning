from pathlib import Path

import pandas as pd

from src.optimization.allocation import (
    allocate_scenario_demand_to_states,
    build_state_shares,
    optimize_all_scenarios,
    summarize_optimization,
)


ROOT = Path(__file__).resolve().parents[1]
STATE_MONTH_PATH = ROOT / "data" / "processed" / "rpc_state_month.csv"
SCENARIO_PATH = ROOT / "analysis" / "demand_scenarios.csv"
OUTPUT_DIR = ROOT / "analysis"


def main() -> None:
    state_month = pd.read_csv(STATE_MONTH_PATH)
    scenarios = pd.read_csv(SCENARIO_PATH)

    state_shares = build_state_shares(state_month, fiscal_year=2024)
    state_scenarios = allocate_scenario_demand_to_states(
        scenarios,
        state_shares,
    )
    optimized = optimize_all_scenarios(state_scenarios)
    summary = summarize_optimization(optimized)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    state_shares.to_csv(OUTPUT_DIR / "optimization_state_shares.csv", index=False)
    state_scenarios.to_csv(
        OUTPUT_DIR / "optimization_state_demand.csv", index=False
    )
    optimized.to_csv(
        OUTPUT_DIR / "optimization_allocations.csv", index=False
    )
    summary.to_csv(
        OUTPUT_DIR / "optimization_summary.csv", index=False
    )

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
