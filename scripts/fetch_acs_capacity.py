from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from src.config import ANALYSIS_DIR, PROCESSED_DATA_DIR
from src.ingestion.acs import (
    fetch_acs_state_profile,
    validate_state_profile,
    validate_variable_metadata,
)

DEFAULT_YEARS = [2021, 2022, 2023, 2024]
OUTPUT_PATH = PROCESSED_DATA_DIR / "acs_state_capacity.csv"
METADATA_PATH = ANALYSIS_DIR / "acs_variable_metadata.json"
SUMMARY_PATH = ANALYSIS_DIR / "acs_capacity_summary.json"


def main() -> None:
    api_key = os.getenv("CENSUS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Set CENSUS_API_KEY before running ACS capacity ingestion."
        )

    metadata = {
        str(year): validate_variable_metadata(year)
        for year in DEFAULT_YEARS
    }

    frames = []
    for year in DEFAULT_YEARS:
        frame = fetch_acs_state_profile(year, api_key=api_key)
        validate_state_profile(frame)
        frames.append(frame)

    panel = pd.concat(frames, ignore_index=True)
    panel = panel.sort_values(["acs_year", "state_fips"]).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUTPUT_PATH, index=False)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    latest = panel[panel["acs_year"] == panel["acs_year"].max()].copy()
    summary = {
        "years": sorted(int(value) for value in panel["acs_year"].unique()),
        "rows": int(len(panel)),
        "states": int(panel["state"].nunique()),
        "latest_year": int(panel["acs_year"].max()),
        "latest_year_medians": {
            "poverty_rate": float(latest["poverty_rate"].median()),
            "unemployment_rate": float(latest["unemployment_rate"].median()),
            "median_household_income": float(
                latest["median_household_income"].median()
            ),
            "rental_vacancy_rate": float(
                latest["rental_vacancy_rate"].median()
            ),
            "median_gross_rent": float(latest["median_gross_rent"].median()),
            "foreign_born_pct": float(latest["foreign_born_pct"].median()),
            "limited_english_pct": float(
                latest["limited_english_pct"].median()
            ),
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
