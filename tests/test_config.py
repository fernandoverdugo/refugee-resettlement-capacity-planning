from src.config import (
    CENSUS_ACS_BASE_URL,
    FIRST_FISCAL_YEAR,
    FORECAST_GRAIN,
    RPC_ADMISSIONS_URL,
    RPC_ARCHIVES_URL,
)


def test_project_scope_configuration():
    assert FIRST_FISCAL_YEAR == 2012
    assert FORECAST_GRAIN == "state_month"
    assert RPC_ADMISSIONS_URL.startswith("https://")
    assert RPC_ARCHIVES_URL.startswith("https://")
    assert CENSUS_ACS_BASE_URL == "https://api.census.gov/data"
