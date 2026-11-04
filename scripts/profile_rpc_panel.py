from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ANALYSIS_DIR, PROCESSED_DATA_DIR

MONTHLY_PATH = PROCESSED_DATA_DIR / "rpc_state_month.csv"
ANNUAL_PATH = PROCESSED_DATA_DIR / "rpc_state_fiscal_year.csv"
NATIONAL_MONTHLY_PATH = PROCESSED_DATA_DIR / "rpc_national_month.csv"
SUMMARY_PATH = ANALYSIS_DIR / "rpc_profile_summary.json"
STATE_SUMMARY_PATH = ANALYSIS_DIR / "rpc_state_summary.csv"
MONTH_SUMMARY_PATH = ANALYSIS_DIR / "rpc_month_summary.csv"


def main() -> None:
    monthly = pd.read_csv(MONTHLY_PATH, parse_dates=["date"])
    annual = pd.read_csv(ANNUAL_PATH)
    national_monthly = pd.read_csv(NATIONAL_MONTHLY_PATH, parse_dates=["date"])

    state_summary = (
        monthly.groupby("state")
        .agg(
            months=("date", "count"),
            first_month=("date", "min"),
            last_month=("date", "max"),
            total_arrivals=("arrivals", "sum"),
            mean_monthly_arrivals=("arrivals", "mean"),
            median_monthly_arrivals=("arrivals", "median"),
            zero_months=("arrivals", lambda values: int((values == 0).sum())),
            nonzero_months=("arrivals", lambda values: int((values > 0).sum())),
        )
        .reset_index()
    )
    state_summary["zero_share"] = (
        state_summary["zero_months"] / state_summary["months"]
    )

    monthly["month_of_year"] = monthly["date"].dt.month
    month_summary = (
        monthly.groupby("month_of_year")
        .agg(
            observations=("arrivals", "count"),
            total_arrivals=("arrivals", "sum"),
            mean_arrivals=("arrivals", "mean"),
            median_arrivals=("arrivals", "median"),
        )
        .reset_index()
    )

    fiscal_year_totals = (
        annual.groupby("fiscal_year", as_index=False)["arrivals"].sum()
    )

    monthly_year_totals = (
        monthly.assign(calendar_year=monthly["date"].dt.year)
        .groupby("calendar_year", as_index=False)["arrivals"]
        .sum()
    )

    summary = {
        "annual_panel": {
            "rows": int(len(annual)),
            "states": int(annual["state"].nunique()),
            "first_fiscal_year": int(annual["fiscal_year"].min()),
            "last_fiscal_year": int(annual["fiscal_year"].max()),
            "total_arrivals": int(annual["arrivals"].sum()),
            "fiscal_year_totals": {
                str(int(row.fiscal_year)): int(row.arrivals)
                for row in fiscal_year_totals.itertuples()
            },
        },
        "monthly_panel": {
            "rows": int(len(monthly)),
            "states": int(monthly["state"].nunique()),
            "first_date": monthly["date"].min().date().isoformat(),
            "last_date": monthly["date"].max().date().isoformat(),
            "months": int(monthly["date"].nunique()),
            "total_arrivals": int(monthly["arrivals"].sum()),
            "zero_observations": int((monthly["arrivals"] == 0).sum()),
            "zero_share": float((monthly["arrivals"] == 0).mean()),
            "median_state_zero_share": float(state_summary["zero_share"].median()),
            "states_with_at_least_24_nonzero_months": int(
                (state_summary["nonzero_months"] >= 24).sum()
            ),
            "calendar_year_totals": {
                str(int(row.calendar_year)): int(row.arrivals)
                for row in monthly_year_totals.itertuples()
            },
        },
        "national_monthly_panel": {
            "rows": int(len(national_monthly)),
            "first_date": national_monthly["date"].min().date().isoformat(),
            "last_date": national_monthly["date"].max().date().isoformat(),
            "fiscal_years": int(national_monthly["fiscal_year"].nunique()),
            "total_arrivals": int(national_monthly["arrivals"].sum()),
        },
        "coverage": {
            "state_annual_fiscal_years": sorted(
                int(value) for value in annual["fiscal_year"].unique()
            ),
            "state_monthly_fiscal_years": sorted(
                int(value) for value in monthly["fiscal_year"].unique()
            ),
            "national_monthly_fiscal_years": sorted(
                int(value) for value in national_monthly["fiscal_year"].unique()
            ),
            "state_level_pdf_gap": [2021, 2022, 2023],
        },
        "diagnostics": {
            "monthly_arrival_p50": float(np.percentile(monthly["arrivals"], 50)),
            "monthly_arrival_p75": float(np.percentile(monthly["arrivals"], 75)),
            "monthly_arrival_p90": float(np.percentile(monthly["arrivals"], 90)),
            "monthly_arrival_p95": float(np.percentile(monthly["arrivals"], 95)),
            "monthly_arrival_p99": float(np.percentile(monthly["arrivals"], 99)),
            "top_states_by_monthly_arrivals": [
                {
                    "state": row.state,
                    "total_arrivals": int(row.total_arrivals),
                    "zero_share": float(row.zero_share),
                }
                for row in state_summary.nlargest(10, "total_arrivals").itertuples()
            ],
        },
    }

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    state_summary.to_csv(STATE_SUMMARY_PATH, index=False)
    month_summary.to_csv(MONTH_SUMMARY_PATH, index=False)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
