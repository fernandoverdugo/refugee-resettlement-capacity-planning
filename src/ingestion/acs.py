from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd
import requests

ACS_PROFILE_VARIABLES = {
    "population": "DP05_0001E",
    "unemployment_rate": "DP03_0009PE",
    "median_household_income": "DP03_0062E",
    "poverty_rate": "DP03_0128PE",
    "rental_vacancy_rate": "DP04_0005E",
    "median_gross_rent": "DP04_0134E",
    "rent_burden_35_plus_pct": "DP04_0142PE",
    "foreign_born_pct": "DP02_0094PE",
    "spanish_lep_pct": "DP02_0117PE",
    "indo_european_lep_pct": "DP02_0119PE",
    "asian_pacific_lep_pct": "DP02_0121PE",
    "other_language_lep_pct": "DP02_0123PE",
}

ACS_PROFILE_BASE_URL = "https://api.census.gov/data/{year}/acs/acs5/profile"
ACS_VARIABLES_URL = "https://api.census.gov/data/{year}/acs/acs5/profile/variables.json"


@dataclass(frozen=True)
class ACSRequest:
    year: int
    api_key: str


def get_api_key() -> str:
    value = os.getenv("CENSUS_API_KEY", "").strip()
    if not value:
        raise RuntimeError(
            "CENSUS_API_KEY is required for Census data requests."
        )
    return value


def build_profile_params(api_key: str) -> dict[str, str]:
    variables = ["NAME", *ACS_PROFILE_VARIABLES.values()]
    return {
        "get": ",".join(variables),
        "for": "state:*",
        "key": api_key,
    }


def validate_variable_metadata(
    year: int,
    session: requests.Session | None = None,
) -> dict:
    client = session or requests.Session()
    response = client.get(
        ACS_VARIABLES_URL.format(year=year),
        timeout=60,
    )
    response.raise_for_status()
    metadata = response.json().get("variables", {})

    missing = [
        variable
        for variable in ACS_PROFILE_VARIABLES.values()
        if variable not in metadata
    ]
    if missing:
        raise ValueError(
            f"ACS {year} profile metadata is missing required variables: {missing}"
        )

    return {
        name: {
            "variable": variable,
            "label": metadata[variable].get("label"),
            "concept": metadata[variable].get("concept"),
        }
        for name, variable in ACS_PROFILE_VARIABLES.items()
    }


def fetch_acs_state_profile(
    year: int,
    api_key: str | None = None,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    key = api_key or get_api_key()
    client = session or requests.Session()

    response = client.get(
        ACS_PROFILE_BASE_URL.format(year=year),
        params=build_profile_params(key),
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    if not payload or len(payload) < 2:
        raise ValueError(f"ACS {year} returned no state rows")

    frame = pd.DataFrame(payload[1:], columns=payload[0])
    frame = frame[frame["state"] != "72"].copy()

    rename = {
        variable: name
        for name, variable in ACS_PROFILE_VARIABLES.items()
    }
    frame = frame.rename(columns=rename)

    numeric_columns = list(ACS_PROFILE_VARIABLES)
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    invalid_sentinels = {-666666666, -777777777, -888888888, -999999999}
    for column in numeric_columns:
        frame.loc[frame[column].isin(invalid_sentinels), column] = pd.NA

    frame["limited_english_pct"] = (
        frame["spanish_lep_pct"].fillna(0)
        + frame["indo_european_lep_pct"].fillna(0)
        + frame["asian_pacific_lep_pct"].fillna(0)
        + frame["other_language_lep_pct"].fillna(0)
    )

    frame["acs_year"] = year
    frame["source_dataset"] = "ACS 5-year data profiles"
    frame["source_url"] = ACS_PROFILE_BASE_URL.format(year=year)

    columns = [
        "state",
        "NAME",
        "acs_year",
        "population",
        "poverty_rate",
        "unemployment_rate",
        "median_household_income",
        "rental_vacancy_rate",
        "median_gross_rent",
        "rent_burden_35_plus_pct",
        "foreign_born_pct",
        "limited_english_pct",
        "spanish_lep_pct",
        "indo_european_lep_pct",
        "asian_pacific_lep_pct",
        "other_language_lep_pct",
        "source_dataset",
        "source_url",
    ]

    frame = frame[columns].rename(
        columns={"state": "state_fips", "NAME": "state"}
    )
    frame = frame.sort_values("state_fips").reset_index(drop=True)
    return frame


def validate_state_profile(frame: pd.DataFrame) -> None:
    if len(frame) != 51:
        raise ValueError(f"Expected 51 states/DC rows, found {len(frame)}")
    if frame["state_fips"].duplicated().any():
        raise ValueError("Duplicate state FIPS values found")
    if frame["state"].duplicated().any():
        raise ValueError("Duplicate state names found")
    if frame["population"].isna().any():
        raise ValueError("Population contains missing values")
    if (frame["population"] <= 0).any():
        raise ValueError("Population must be positive")

    bounded = [
        "poverty_rate",
        "unemployment_rate",
        "rental_vacancy_rate",
        "rent_burden_35_plus_pct",
        "foreign_born_pct",
        "limited_english_pct",
    ]
    for column in bounded:
        valid = frame[column].dropna()
        if ((valid < 0) | (valid > 100)).any():
            raise ValueError(f"{column} contains values outside 0-100")
