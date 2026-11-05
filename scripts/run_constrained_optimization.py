from pathlib import Path

import pandas as pd

from src.optimization.allocation import (
    allocate_scenario_demand_to_states,
    build_state_shares,
)
from src.optimization.constrained import (
    build_planning_constraints,
    optimize_all_constrained_scenarios,
    summarize_constrained_optimization,
)


ROOT = Path(__file__).resolve().parents[1]
STATE_MONTH_PATH = ROOT / "data" / "processed" / "rpc_state_month.csv"
SCENARIO_PATH = ROOT / "analysis" / "demand_scenarios.csv"
OUTPUT_DIR = ROOT / "analysis"


def main() -> None:
    state_month = pd.read_csv(STATE_MONTH_PATH)
    scenarios = pd.read_csv(SCENARIO_PATH)

    state_shares = build_state_shares(state_month)
    state_scenarios = allocate_scenario_demand_to_states(
        scenarios,
        state_shares,
    )
    constraints = build_planning_constraints(state_shares)
    optimized = optimize_all_constrained_scenarios(
        state_scenarios,
        constraints,
    )
    summary = summarize_constrained_optimization(optimized)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    constraints.to_csv(
        OUTPUT_DIR / "constrained_optimization_constraints.csv",
        index=False,
    )
    optimized.to_csv(
        OUTPUT_DIR / "constrained_optimization_allocations.csv",
        index=False,
    )
    summary.to_csv(
        OUTPUT_DIR / "constrained_optimization_summary.csv",
        index=False,
    )

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
