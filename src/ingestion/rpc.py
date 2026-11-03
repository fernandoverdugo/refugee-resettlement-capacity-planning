from __future__ import annotations

import hashlib
import io
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup

from src.config import FIRST_FISCAL_YEAR, RPC_ARCHIVES_URL

MONTHS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
MONTH_NUMBER = {
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
}

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
    "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
    "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
]
STATE_PREFIXES = sorted(US_STATES, key=len, reverse=True)


@dataclass(frozen=True)
class RPCSource:
    fiscal_year: int
    url: str
    filename: str
    file_type: str


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def discover_rpc_sources(
    archive_url: str = RPC_ARCHIVES_URL,
    session: requests.Session | None = None,
) -> list[RPCSource]:
    client = session or requests.Session()
    response = client.get(archive_url, timeout=60)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    sources: list[RPCSource] = []

    for link in soup.find_all("a", href=True):
        label = " ".join(link.get_text(" ", strip=True).split())
        match = re.search(
            r"FY\s*(20\d{2}).*Arrivals by State and Nationality",
            label,
            flags=re.IGNORECASE,
        )
        if not match:
            continue

        fiscal_year = int(match.group(1))
        if fiscal_year < FIRST_FISCAL_YEAR:
            continue

        url = urljoin(archive_url, link["href"])
        filename = Path(url.split("?", 1)[0]).name
        suffix = Path(filename).suffix.lower().lstrip(".")

        if suffix not in {"xls", "xlsx", "pdf"}:
            continue

        sources.append(
            RPCSource(
                fiscal_year=fiscal_year,
                url=url,
                filename=filename,
                file_type=suffix,
            )
        )

    unique = {source.fiscal_year: source for source in sources}
    return [unique[year] for year in sorted(unique)]


def download_source(
    source: RPCSource,
    destination_dir: Path,
    session: requests.Session | None = None,
) -> dict:
    destination_dir.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    response = client.get(source.url, timeout=120)
    response.raise_for_status()

    content = response.content
    path = destination_dir / f"fy{source.fiscal_year}_{source.filename}"
    path.write_bytes(content)

    return {
        **asdict(source),
        "local_path": str(path),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": sha256_bytes(content),
        "bytes": len(content),
    }


def normalize_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return " ".join(str(value).replace("\n", " ").split())


def normalize_month(value: str) -> str | None:
    cleaned = normalize_cell(value).lower().replace(".", "")
    for month in MONTHS:
        if cleaned == month.lower():
            return month
    return None


def fiscal_year_for_month(fiscal_year: int, month: str) -> int:
    return fiscal_year - 1 if MONTH_NUMBER[month] >= 10 else fiscal_year


def rows_to_state_month(
    rows: list[list],
    fiscal_year: int,
    source_url: str,
    source_file: str,
    retrieved_at_utc: str,
) -> pd.DataFrame:
    header_index = None
    header_months: dict[int, str] = {}

    for index, row in enumerate(rows):
        normalized = [normalize_cell(value) for value in row]
        month_columns = {
            column: month
            for column, value in enumerate(normalized)
            if (month := normalize_month(value)) is not None
        }
        row_text = " ".join(normalized).lower()
        if len(month_columns) >= 1 and (
            "nationality" in row_text or "state" in row_text
        ):
            header_index = index
            header_months = month_columns
            break

    if header_index is None:
        raise ValueError(f"Could not identify RPC table header for FY{fiscal_year}")

    output: list[dict] = []
    current_state = ""

    for row in rows[header_index + 1 :]:
        normalized = [normalize_cell(value) for value in row]
        if not any(normalized):
            continue

        first = normalized[0] if normalized else ""
        second = normalized[1] if len(normalized) > 1 else ""

        if first and first.lower() not in {"grand total", "total"}:
            current_state = first

        nationality = second.lower()
        if nationality != "total":
            continue

        if not current_state:
            continue

        for column, month in header_months.items():
            raw_value = normalized[column] if column < len(normalized) else ""
            cleaned = raw_value.replace(",", "").strip()
            if cleaned in {"", "-", "—"}:
                arrivals = 0
            else:
                try:
                    arrivals = int(float(cleaned))
                except ValueError:
                    continue

            calendar_year = fiscal_year_for_month(fiscal_year, month)
            output.append(
                {
                    "state": current_state,
                    "date": f"{calendar_year:04d}-{MONTH_NUMBER[month]:02d}-01",
                    "calendar_year": calendar_year,
                    "calendar_month": MONTH_NUMBER[month],
                    "fiscal_year": fiscal_year,
                    "arrivals": arrivals,
                    "source_report": source_file,
                    "source_url": source_url,
                    "retrieved_at_utc": retrieved_at_utc,
                }
            )

    frame = pd.DataFrame(output)
    if frame.empty:
        raise ValueError(f"No state-month totals parsed for FY{fiscal_year}")

    return frame.drop_duplicates(
        subset=["state", "date", "fiscal_year"],
        keep="last",
    ).sort_values(["state", "date"]).reset_index(drop=True)



def state_from_pdf_cell(value) -> str | None:
    text = normalize_cell(value)
    compact = text.replace("\n", " ")
    for state in STATE_PREFIXES:
        if compact == state or compact.startswith(state + " "):
            return state
    return None


def pdf_rows_to_state_month(
    rows: list[list],
    fiscal_year: int,
    source_url: str,
    source_file: str,
    retrieved_at_utc: str,
) -> pd.DataFrame:
    totals: dict[tuple[str, str], int] = {}
    detected_states: set[str] = set()
    current_state: str | None = None

    for row in rows:
        normalized = [normalize_cell(value) for value in row]
        if len(normalized) < 14:
            continue

        first_cell = normalized[0] if normalized else ""
        detected_state = state_from_pdf_cell(first_cell)

        if first_cell:
            if detected_state:
                current_state = detected_state
                detected_states.add(detected_state)
            else:
                current_state = None

        if current_state is None:
            continue

        for offset, month in enumerate(MONTHS, start=2):
            if offset >= len(normalized):
                continue

            raw_value = normalized[offset].replace(",", "").strip()
            if raw_value in {"", "-", "—"}:
                continue

            if not re.fullmatch(r"-?\d+(?:\.0+)?", raw_value):
                continue

            arrivals = int(float(raw_value))
            key = (current_state, month)
            totals[key] = totals.get(key, 0) + arrivals

    output = []
    for state in sorted(detected_states):
        for month in MONTHS:
            arrivals = totals.get((state, month), 0)
            calendar_year = fiscal_year_for_month(fiscal_year, month)
            output.append(
                {
                    "state": state,
                    "date": f"{calendar_year:04d}-{MONTH_NUMBER[month]:02d}-01",
                    "calendar_year": calendar_year,
                    "calendar_month": MONTH_NUMBER[month],
                    "fiscal_year": fiscal_year,
                    "arrivals": arrivals,
                    "source_report": source_file,
                    "source_url": source_url,
                    "retrieved_at_utc": retrieved_at_utc,
                }
            )

    frame = pd.DataFrame(output)
    if frame.empty:
        raise ValueError(f"No PDF state-month arrivals parsed for FY{fiscal_year}")

    return frame.sort_values(["state", "date"]).reset_index(drop=True)


def excel_rows(content: bytes) -> list[list]:
    frame = pd.read_excel(io.BytesIO(content), header=None, dtype=object)
    return frame.where(pd.notna(frame), None).values.tolist()


def pdf_rows(content: bytes) -> list[list]:
    rows: list[list] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                rows.extend(table)
    return rows


def parse_source_bytes(
    source: RPCSource,
    content: bytes,
    retrieved_at_utc: str,
) -> pd.DataFrame:
    if source.file_type in {"xls", "xlsx"}:
        rows = excel_rows(content)
        return rows_to_state_month(
            rows=rows,
            fiscal_year=source.fiscal_year,
            source_url=source.url,
            source_file=source.filename,
            retrieved_at_utc=retrieved_at_utc,
        )

    if source.file_type == "pdf":
        rows = pdf_rows(content)
        return pdf_rows_to_state_month(
            rows=rows,
            fiscal_year=source.fiscal_year,
            source_url=source.url,
            source_file=source.filename,
            retrieved_at_utc=retrieved_at_utc,
        )

    raise ValueError(f"Unsupported RPC source type: {source.file_type}")


def build_state_month_panel(
    sources: list[RPCSource],
    raw_dir: Path,
    manifest_path: Path,
    output_path: Path,
) -> pd.DataFrame:
    manifest: list[dict] = []
    frames: list[pd.DataFrame] = []
    client = requests.Session()

    for source in sources:
        metadata = download_source(source, raw_dir, session=client)
        manifest.append(metadata)
        content = Path(metadata["local_path"]).read_bytes()
        frames.append(
            parse_source_bytes(
                source,
                content,
                metadata["retrieved_at_utc"],
            )
        )

    panel = pd.concat(frames, ignore_index=True)
    panel = panel.sort_values(["state", "date"]).reset_index(drop=True)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(output_path, index=False)

    return panel
