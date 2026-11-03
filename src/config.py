from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ANALYSIS_DIR = PROJECT_ROOT / "analysis"

FIRST_FISCAL_YEAR = 2012
FORECAST_GRAIN = "state_month"

RPC_ADMISSIONS_URL = "https://www.rpc.state.gov/admissions-and-arrivals/"
RPC_ARCHIVES_URL = "https://www.rpc.state.gov/archives/"
CENSUS_ACS_BASE_URL = "https://api.census.gov/data"
