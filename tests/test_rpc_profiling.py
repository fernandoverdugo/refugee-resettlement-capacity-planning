import pandas as pd

from scripts.profile_rpc_panels import (
    build_annual_totals,
    build_month_profile,
    build_state_profile,
    validate_annual,
    validate_monthly,
)


def test_rpc_profile_helpers():
    monthly_rows = []
    for month in range(1, 13):
        monthly_rows.append(
            {
                "state": "Texas",
                "date": f"2025-{month:02d}-01",
                "calendar_year": 2025,
                "calendar_month": month,
                "fiscal_year": 2025,
                "arrivals": month,
                "source_report": "test.pdf",
                "source_url": "https://example.test/test.pdf",
                "retrieved_at_utc": "2026-11-03T00:00:00+00:00",
            }
        )

    monthly = pd.DataFrame(monthly_rows)
    monthly = pd.concat(
        [
            monthly,
            monthly.assign(
                state="Utah",
                arrivals=0,
                source_report="test.pdf",
            ),
        ],
        ignore_index=True,
    )

    annual = pd.DataFrame(
        [
            {
                "state": state,
                "fiscal_year": year,
                "arrivals": 10,
                "source_report": "test.xls",
                "source_url": "https://example.test/test.xls",
                "retrieved_at_utc": "2026-11-03T00:00:00+00:00",
            }
            for year in range(2012, 2026)
            for state in [f"State {i}" for i in range(45)]
        ]
    )

    validate_annual(annual)

    profile = build_state_profile(monthly)
    assert profile.loc[profile["state"] == "Texas", "total_arrivals"].iloc[0] == 78
    assert profile.loc[profile["state"] == "Utah", "zero_month_share"].iloc[0] == 1

    month_profile = build_month_profile(monthly)
    assert len(month_profile) == 12

    annual_totals = build_annual_totals(annual)
    assert len(annual_totals) == 14
