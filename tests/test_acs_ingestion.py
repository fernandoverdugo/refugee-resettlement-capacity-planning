import pandas as pd

from src.ingestion.acs import (
    ACS_PROFILE_VARIABLES,
    build_profile_params,
    validate_state_profile,
)


def test_profile_request_contains_expected_variables():
    params = build_profile_params("test-key")
    assert params["for"] == "state:*"
    assert params["key"] == "test-key"
    assert "DP05_0001E" in params["get"]
    assert "DP03_0128PE" in params["get"]
    assert "DP04_0134E" in params["get"]
    assert "DP02_0094PE" in params["get"]
    assert len(ACS_PROFILE_VARIABLES) == 12


def test_validate_state_profile_accepts_complete_panel():
    rows = []
    for index in range(51):
        rows.append(
            {
                "state_fips": f"{index + 1:02d}",
                "state": f"State {index}",
                "population": 100000 + index,
                "poverty_rate": 10.0,
                "unemployment_rate": 4.0,
                "rental_vacancy_rate": 6.0,
                "rent_burden_35_plus_pct": 35.0,
                "foreign_born_pct": 12.0,
                "limited_english_pct": 8.0,
            }
        )

    validate_state_profile(pd.DataFrame(rows))


def test_validate_state_profile_rejects_duplicate_states():
    frame = pd.DataFrame(
        [
            {
                "state_fips": "01",
                "state": "Example",
                "population": 100,
                "poverty_rate": 10,
                "unemployment_rate": 4,
                "rental_vacancy_rate": 5,
                "rent_burden_35_plus_pct": 30,
                "foreign_born_pct": 10,
                "limited_english_pct": 5,
            }
        ]
        * 51
    )

    try:
        validate_state_profile(frame)
    except ValueError as exc:
        assert "Duplicate" in str(exc)
    else:
        raise AssertionError("duplicate state validation should fail")
