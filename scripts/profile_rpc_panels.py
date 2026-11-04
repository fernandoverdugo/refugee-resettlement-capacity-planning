from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ANNUAL_PATH = Path("data/processed/rpc_state_fiscal_year.csv")
MONTHLY_PATH = Path("data/processed/rpc_state_month.csv")
NATIONAL_MONTHLY_PATH = Path("data/processed/rpc_national_month.csv")
SUMMARY_PATH = Path("analysis/rpc_ingestion_summary.json")
STATE_PROFILE_PATH = Path("analysis/rpc_monthly_state_profile.csv")
MONTH_PROFILE_PATH = Path("analysis/rpc_month_profile.csv")
ANNUAL_TOTALS_PATH = Path("analysis/rpc_annual_totals.csv")


def validate_annual(frame: pd.DataFrame) -> None:
    required = {
        "state",
        "fiscal_year",
        "arrivals",
        "source_report",
        "source_url",
        "retrieved_at_utc",
    }
    assert required.issubset(frame.columns)
    assert not frame.duplicated(["state", "fiscal_year"]).any()
    assert (frame["arrivals"] >= 0).all()
    assert frame["state"].nunique() >= 45
    assert frame["fiscal_year"].min() <= 2012
    assert frame["fiscal_year"].nunique() >= 10


def validate_monthly(frame: pd.DataFrame) -> None:
    required = {
        "state",
        "date",
        "calendar_year",
        "calendar_month",
        "fiscal_year",
        "arrivals",
        "source_report",
        "source_url",
        "retrieved_at_utc",
    }
    assert required.issubset(frame.columns)
    assert not frame.duplicated(["state", "date"]).any()
    assert (frame["arrivals"] >= 0).all()
    assert frame["state"].nunique() >= 40
    assert frame["fiscal_year"].min() >= 2021

    counts = frame.groupby(["state", "fiscal_year"]).size()
    assert (counts == 12).all()


def build_state_profile(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["date"] = pd.to_datetime(working["date"])

    profile = (
        working.groupby("state")
        .agg(
            observations=("arrivals", "size"),
            first_date=("date", "min"),
            last_date=("date", "max"),
            total_arrivals=("arrivals", "sum"),
            mean_monthly_arrivals=("arrivals", "mean"),
            median_monthly_arrivals=("arrivals", "median"),
            max_monthly_arrivals=("arrivals", "max"),
            zero_months=("arrivals", lambda x: int((x == 0).sum())),
        )
        .reset_index()
    )
    profile["zero_month_share"] = profile["zero_months"] / profile["observations"]
    profile["mean_monthly_arrivals"] = profile["mean_monthly_arrivals"].round(2)
    profile["median_monthly_arrivals"] = profile["median_monthly_arrivals"].round(2)
    profile["zero_month_share"] = profile["zero_month_share"].round(4)
    return profile.sort_values("total_arrivals", ascending=False)


def build_month_profile(frame: pd.DataFrame) -> pd.DataFrame:
    profile = (
        frame.groupby("calendar_month")
        .agg(
            observations=("arrivals", "size"),
            total_arrivals=("arrivals", "sum"),
            mean_arrivals=("arrivals", "mean"),
            median_arrivals=("arrivals", "median"),
            zero_share=("arrivals", lambda x: float((x == 0).mean())),
        )
        .reset_index()
    )
    profile["mean_arrivals"] = profile["mean_arrivals"].round(2)
    profile["median_arrivals"] = profile["median_arrivals"].round(2)
    profile["zero_share"] = profile["zero_share"].round(4)
    return profile.sort_values("calendar_month")


def build_annual_totals(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.groupby("fiscal_year", as_index=False)
        .agg(
            states=("state", "nunique"),
            total_arrivals=("arrivals", "sum"),
        )
        .sort_values("fiscal_year")
    )


def main() -> None:
    annual = pd.read_csv(ANNUAL_PATH)
    monthly = pd.read_csv(MONTHLY_PATH)
    national_monthly = pd.read_csv(NATIONAL_MONTHLY_PATH)

    validate_annual(annual)
    validate_monthly(monthly)

    assert not national_monthly.duplicated(["date"]).any()
    assert (national_monthly["arrivals"] >= 0).all()
    assert national_monthly["fiscal_year"].min() <= 2021
    assert national_monthly["fiscal_year"].nunique() >= 4

    state_profile = build_state_profile(monthly)
    month_profile = build_month_profile(monthly)
    annual_totals = build_annual_totals(annual)

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    state_profile.to_csv(STATE_PROFILE_PATH, index=False)
    month_profile.to_csv(MONTH_PROFILE_PATH, index=False)
    annual_totals.to_csv(ANNUAL_TOTALS_PATH, index=False)

    monthly_dates = pd.to_datetime(monthly["date"])
    summary = {
        "annual_panel": {
            "rows": int(len(annual)),
            "states": int(annual["state"].nunique()),
            "first_fiscal_year": int(annual["fiscal_year"].min()),
            "last_fiscal_year": int(annual["fiscal_year"].max()),
            "fiscal_years": int(annual["fiscal_year"].nunique()),
            "total_arrivals": int(annual["arrivals"].sum()),
        },
        "monthly_panel": {
            "rows": int(len(monthly)),
            "states": int(monthly["state"].nunique()),
            "first_date": monthly_dates.min().date().isoformat(),
            "last_date": monthly_dates.max().date().isoformat(),
            "fiscal_years": int(monthly["fiscal_year"].nunique()),
            "total_arrivals": int(monthly["arrivals"].sum()),
            "zero_month_share": round(float((monthly["arrivals"] == 0).mean()), 4),
            "median_state_zero_month_share": round(
                float(state_profile["zero_month_share"].median()), 4
            ),
        },
        "national_monthly_panel": {
            "rows": int(len(national_monthly)),
            "first_date": pd.to_datetime(national_monthly["date"]).min().date().isoformat(),
            "last_date": pd.to_datetime(national_monthly["date"]).max().date().isoformat(),
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
            "state_level_pdf_gap": sorted(
                set(int(value) for value in national_monthly["fiscal_year"].unique())
                - set(int(value) for value in monthly["fiscal_year"].unique())
            ),
        },
        "forecasting_diagnostics": {
            "states_with_at_least_48_months": int(
                (state_profile["observations"] >= 48).sum()
            ),
            "states_with_zero_share_at_most_25pct": int(
                (state_profile["zero_month_share"] <= 0.25).sum()
            ),
            "states_with_zero_share_over_50pct": int(
                (state_profile["zero_month_share"] > 0.50).sum()
            ),
            "top_10_states_by_arrivals": state_profile.head(10)["state"].tolist(),
        },
    }

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
