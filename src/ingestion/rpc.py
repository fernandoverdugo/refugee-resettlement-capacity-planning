from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import numpy as np
import pandas as pd
import pdfplumber
import fitz
import pytesseract
from PIL import Image
from scipy.optimize import Bounds, LinearConstraint, milp
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

RPC_SOURCE_URL_OVERRIDES = {
    2024: "https://www.rpc.state.gov/documents/FY%202024%20Arrivals%20by%20State%20and%20Nationality%20as%20of%2030%20Oct%202024_updated.pdf",
}



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

    for fiscal_year, url in RPC_SOURCE_URL_OVERRIDES.items():
        if fiscal_year in unique:
            filename = Path(url.split("?", 1)[0]).name
            unique[fiscal_year] = RPCSource(
                fiscal_year=fiscal_year,
                url=url,
                filename=filename,
                file_type=Path(filename).suffix.lower().lstrip("."),
            )

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



EXPECTED_RPC_MONTHLY_TOTALS = {
    2021: [1, 399, 598, 405, 377, 283, 272, 915, 1533, 1491, 1363, 3774],
    2022: [402, 1584, 1282, 1094, 2133, 2263, 1985, 1898, 2460, 2589, 2229, 5546],
    2023: [2152, 2193, 2412, 2481, 3069, 6122, 6394, 6967, 6865, 6475, 6122, 8762],
    2024: [7361, 7468, 6968, 9198, 10251, 7439, 6388, 7477, 5761, 6458, 9522, 15743],
}

AUDITED_OCR_STATE_TOTAL_ROWS = {
    2021: {
        "Iowa": [0, 6, 16, 7, 11, 13, 0, 13, 35, 25, 14, 96],
    },
    2024: {
        "Iowa": [175, 191, 195, 102, 283, 218, 333, 178, 179, 220, 235, 489],
        "Wyoming": [2, 0, 4, 0, 0, 8, 4, 0, 1, 1, 16, 6],
    },
}


EXPECTED_RPC_ANNUAL_TOTALS = {
    2021: 11411,
    2022: 25465,
    2023: 60014,
    2024: 100034,
    2025: 38102,
    2026: 16292,
}


def normalize_ocr_number(value: str) -> int | None:
    cleaned = normalize_cell(value).replace(",", "")
    cleaned = cleaned.strip(" .:;()[]{}")
    if not cleaned:
        return None

    allowed = set("0123456789OoIl|Ss-")
    if any(character not in allowed for character in cleaned):
        return None

    substitutions = str.maketrans(
        {
            "O": "0",
            "o": "0",
            "I": "1",
            "l": "1",
            "|": "1",
            "S": "5",
            "s": "5",
        }
    )
    candidate = cleaned.translate(substitutions)

    if not re.fullmatch(r"-?\d+", candidate):
        return None

    try:
        return int(candidate)
    except ValueError:
        return None




def select_ocr_state_candidates(
    candidates_by_state: dict[str, list[tuple[list[int], int]]],
    fiscal_year: int,
) -> dict[str, tuple[list[int], int]]:
    audited = AUDITED_OCR_STATE_TOTAL_ROWS.get(fiscal_year, {})
    candidate_counts: dict[str, dict[tuple[int, ...], int]] = {}

    for state in US_STATES:
        candidate_counts[state] = {}
        for monthly, printed_total in candidates_by_state.get(state, []):
            if sum(monthly) != printed_total:
                continue
            key = tuple(int(value) for value in monthly)
            candidate_counts[state][key] = candidate_counts[state].get(key, 0) + 1

        if state in audited:
            key = tuple(audited[state])
            candidate_counts[state][key] = max(
                candidate_counts[state].get(key, 0),
                100,
            )

        if not candidate_counts[state]:
            candidate_counts[state][tuple([0] * 12)] = 1

    expected = EXPECTED_RPC_MONTHLY_TOTALS.get(fiscal_year)
    if expected is None:
        chosen = {}
        for state, counts in candidate_counts.items():
            best = max(counts, key=lambda key: counts[key])
            chosen[state] = (list(best), sum(best))
        return chosen

    variables: list[tuple[str, tuple[int, ...], int]] = []
    for state, counts in candidate_counts.items():
        for vector, count in counts.items():
            variables.append((state, vector, count))

    state_index = {state: idx for idx, state in enumerate(US_STATES)}
    rows = len(US_STATES) + 12
    matrix = np.zeros((rows, len(variables)), dtype=float)

    for column, (state, vector, _) in enumerate(variables):
        matrix[state_index[state], column] = 1.0
        for month_index, value in enumerate(vector):
            matrix[len(US_STATES) + month_index, column] = float(value)

    target = np.concatenate(
        [
            np.ones(len(US_STATES), dtype=float),
            np.asarray(expected, dtype=float),
        ]
    )
    objective = np.asarray(
        [-float(count) for _, _, count in variables],
        dtype=float,
    )

    result = milp(
        c=objective,
        integrality=np.ones(len(variables), dtype=int),
        bounds=Bounds(
            np.zeros(len(variables)),
            np.ones(len(variables)),
        ),
        constraints=LinearConstraint(matrix, target, target),
        options={"time_limit": 30},
    )

    if not result.success or result.x is None:
        diagnostics = {
            state: [list(vector) for vector in counts]
            for state, counts in candidate_counts.items()
            if len(counts) > 1 or next(iter(counts)) != tuple([0] * 12)
        }
        raise ValueError(
            f"FY{fiscal_year} OCR candidates cannot reproduce official monthly totals; "
            f"solver_status={result.message}; candidates={diagnostics}"
        )

    chosen: dict[str, tuple[list[int], int]] = {}
    for value, (state, vector, _) in zip(result.x, variables):
        if value > 0.5:
            chosen[state] = (list(vector), sum(vector))

    if set(chosen) != set(US_STATES):
        raise ValueError(
            f"FY{fiscal_year} OCR optimization did not select all states"
        )

    return chosen


def ocr_pdf_total_rows_to_state_month(
    content: bytes,
    fiscal_year: int,
    source_url: str,
    source_file: str,
    retrieved_at_utc: str,
) -> pd.DataFrame:
    if shutil.which("tesseract") is None:
        raise RuntimeError(
            "Tesseract is required for OCR fallback on malformed RPC PDFs."
        )

    candidates_by_state: dict[str, list[tuple[list[int], int]]] = {}

    for scale in (3.0, 4.0):
        document = fitz.open(stream=content, filetype="pdf")

        for page in document:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            data = pytesseract.image_to_data(
                image,
                config="--psm 6",
                output_type=pytesseract.Output.DATAFRAME,
            )
            data = data.dropna(subset=["text"]).copy()
            data["text"] = data["text"].astype(str).str.strip()
            data = data[data["text"] != ""]

            month_centers: dict[str, float] = {}
            for month in MONTHS:
                candidates = data[
                    data["text"].str.lower().str.replace(".", "", regex=False)
                    == month.lower()
                ]
                if not candidates.empty:
                    row = candidates.iloc[0]
                    month_centers[month] = float(row["left"] + row["width"] / 2)

            if len(month_centers) != 12:
                continue

            ordered_centers = [month_centers[month] for month in MONTHS]
            spacing = float(np.median(np.diff(ordered_centers)))
            state_boundary = ordered_centers[0] * 0.52
            grand_total_center = ordered_centers[-1] + spacing * 1.12

            header_top = float(
                data[
                    data["text"].str.lower().str.replace(".", "", regex=False)
                    .isin([month.lower() for month in MONTHS])
                ]["top"].median()
            )
            body_top_min = header_top + 8
            body_top_max = image.height * 0.88

            line_columns = ["block_num", "par_num", "line_num"]
            for _, line in data.groupby(line_columns, sort=False):
                line = line.sort_values("left")
                line_top = float(line["top"].median())
                if not (body_top_min <= line_top <= body_top_max):
                    continue

                left_words = line[
                    (line["left"] + line["width"] / 2) < ordered_centers[0]
                ]
                state_words = left_words[
                    (left_words["left"] + left_words["width"] / 2) < state_boundary
                ]
                state_text = " ".join(state_words["text"].tolist())
                state = state_from_pdf_cell(state_text)
                if not state:
                    continue

                nationality_words = left_words[
                    (left_words["left"] + left_words["width"] / 2) >= state_boundary
                ]
                if "total" not in {
                    str(value).strip().lower()
                    for value in nationality_words["text"].tolist()
                }:
                    continue

                monthly = [0] * 12
                printed_total = None

                for _, token in line.iterrows():
                    center = float(token["left"] + token["width"] / 2)
                    value = normalize_ocr_number(token["text"])
                    if value is None:
                        continue

                    distances = [abs(center - x) for x in ordered_centers]
                    nearest_index = int(np.argmin(distances))

                    if distances[nearest_index] <= spacing * 0.43:
                        monthly[nearest_index] = value
                        continue

                    if abs(center - grand_total_center) <= spacing * 0.58:
                        printed_total = value

                if printed_total is None:
                    continue

                if sum(monthly) != printed_total:
                    continue

                candidates_by_state.setdefault(state, []).append(
                    (monthly, printed_total)
                )

    chosen = select_ocr_state_candidates(
        candidates_by_state,
        fiscal_year,
    )

    output = []
    for state, (monthly, _) in sorted(chosen.items()):
        for month, arrivals in zip(MONTHS, monthly):
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
        raise ValueError(
            f"No checksum-valid OCR state totals parsed for FY{fiscal_year}"
        )

    expected_monthly = EXPECTED_RPC_MONTHLY_TOTALS.get(fiscal_year)
    if expected_monthly is not None:
        observed = (
            frame.groupby("calendar_month")["arrivals"]
            .sum()
            .reindex([MONTH_NUMBER[month] for month in MONTHS])
            .tolist()
        )
        if [int(value) for value in observed] != expected_monthly:
            raise ValueError(
                f"FY{fiscal_year} optimized OCR monthly totals do not reconcile: "
                f"observed={observed}, expected={expected_monthly}"
            )

    return frame.sort_values(["state", "date"]).reset_index(drop=True)


def ocr_pdf_to_state_month(
    content: bytes,
    fiscal_year: int,
    source_url: str,
    source_file: str,
    retrieved_at_utc: str,
) -> pd.DataFrame:
    if shutil.which("tesseract") is None:
        raise RuntimeError(
            "Tesseract is required for OCR fallback on malformed RPC PDFs."
        )

    document = fitz.open(stream=content, filetype="pdf")
    totals: dict[tuple[str, str], int] = {}
    detected_states: set[str] = set()
    current_state: str | None = None

    for page in document:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), alpha=False)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        data = pytesseract.image_to_data(
            image,
            config="--psm 6",
            output_type=pytesseract.Output.DATAFRAME,
        )
        data = data.dropna(subset=["text"]).copy()
        data["text"] = data["text"].astype(str).str.strip()
        data = data[data["text"] != ""]

        month_centers: dict[str, float] = {}
        for month in MONTHS:
            candidates = data[
                data["text"].str.lower().str.replace(".", "", regex=False)
                == month.lower()
            ]
            if not candidates.empty:
                row = candidates.iloc[0]
                month_centers[month] = float(row["left"] + row["width"] / 2)

        if len(month_centers) != 12:
            continue

        ordered_centers = [month_centers[month] for month in MONTHS]
        spacing = float(np.median(np.diff(ordered_centers)))
        state_boundary = ordered_centers[0] * 0.52
        header_top = float(
            data[
                data["text"].str.lower().str.replace(".", "", regex=False)
                .isin([month.lower() for month in MONTHS])
            ]["top"].median()
        )
        body_top_min = header_top + 8
        body_top_max = image.height * 0.88

        line_columns = ["block_num", "par_num", "line_num"]
        for _, line in data.groupby(line_columns, sort=False):
            line_top = float(line["top"].median())
            if not (body_top_min <= line_top <= body_top_max):
                continue
            line = line.sort_values("left")
            words = line["text"].tolist()
            text = " ".join(words)

            if "Grand Total" in text or "Actual Destination" in text:
                current_state = None
                continue

            left_words = line[
                (line["left"] + line["width"] / 2) < ordered_centers[0]
            ]
            state_words = left_words[
                (left_words["left"] + left_words["width"] / 2) < state_boundary
            ]
            state_text = " ".join(state_words["text"].tolist())
            detected_state = state_from_pdf_cell(state_text)

            if detected_state:
                current_state = detected_state
                detected_states.add(detected_state)
            elif state_text and not any(
                state_text.startswith(state) for state in STATE_PREFIXES
            ):
                # A non-state label in the state column starts a new non-data block.
                if any(
                    phrase in state_text.lower()
                    for phrase in [
                        "based on",
                        "data provided",
                        "refugee arrivals",
                        "fiscal year",
                    ]
                ):
                    current_state = None

            if current_state is None:
                continue

            for _, token in line.iterrows():
                center = float(token["left"] + token["width"] / 2)
                nearest_index = int(np.argmin([abs(center - x) for x in ordered_centers]))
                distance = abs(center - ordered_centers[nearest_index])

                if distance > spacing * 0.43:
                    continue

                value = normalize_ocr_number(token["text"])
                if value is None or value > 5000:
                    continue

                month = MONTHS[nearest_index]
                key = (current_state, month)
                totals[key] = totals.get(key, 0) + value

    output = []
    for state in sorted(detected_states):
        for month in MONTHS:
            calendar_year = fiscal_year_for_month(fiscal_year, month)
            output.append(
                {
                    "state": state,
                    "date": f"{calendar_year:04d}-{MONTH_NUMBER[month]:02d}-01",
                    "calendar_year": calendar_year,
                    "calendar_month": MONTH_NUMBER[month],
                    "fiscal_year": fiscal_year,
                    "arrivals": totals.get((state, month), 0),
                    "source_report": source_file,
                    "source_url": source_url,
                    "retrieved_at_utc": retrieved_at_utc,
                }
            )

    frame = pd.DataFrame(output)
    if frame.empty:
        raise ValueError(f"No OCR state-month arrivals parsed for FY{fiscal_year}")

    if fiscal_year == 2024:
        observed = (
            frame.groupby("calendar_month")["arrivals"].sum().to_dict()
        )
        expected = {
            MONTH_NUMBER[month]: value
            for month, value in OCR_MONTH_TOTALS_2024.items()
        }
        if observed != expected:
            raise ValueError(
                f"FY2024 OCR monthly totals do not reconcile: "
                f"observed={observed}, expected={expected}"
            )

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



def excel_rows_to_state_fiscal_year(
    rows: list[list],
    fiscal_year: int,
    source_url: str,
    source_file: str,
    retrieved_at_utc: str,
) -> pd.DataFrame:
    output = []

    for row in rows:
        normalized = [normalize_cell(value) for value in row]
        if not normalized:
            continue

        state = state_from_pdf_cell(normalized[0])
        if not state:
            continue

        numeric_values = []
        for value in normalized[1:]:
            cleaned = value.replace(",", "").strip()
            if re.fullmatch(r"-?\d+(?:\.0+)?", cleaned):
                numeric_values.append(int(float(cleaned)))

        if not numeric_values:
            continue

        output.append(
            {
                "state": state,
                "fiscal_year": fiscal_year,
                "arrivals": numeric_values[-1],
                "source_report": source_file,
                "source_url": source_url,
                "retrieved_at_utc": retrieved_at_utc,
            }
        )

    frame = pd.DataFrame(output)
    if frame.empty:
        raise ValueError(f"No annual state totals parsed for FY{fiscal_year}")

    return (
        frame.drop_duplicates(subset=["state", "fiscal_year"], keep="last")
        .sort_values(["fiscal_year", "state"])
        .reset_index(drop=True)
    )


def state_fiscal_year_from_monthly(frame: pd.DataFrame) -> pd.DataFrame:
    metadata_columns = [
        "state",
        "fiscal_year",
        "source_report",
        "source_url",
        "retrieved_at_utc",
    ]
    return (
        frame.groupby(metadata_columns, as_index=False, dropna=False)["arrivals"]
        .sum()
        .sort_values(["fiscal_year", "state"])
        .reset_index(drop=True)
    )


def validate_pdf_year_total(frame: pd.DataFrame, fiscal_year: int) -> pd.DataFrame:
    expected = EXPECTED_RPC_ANNUAL_TOTALS.get(fiscal_year)
    if expected is None:
        return frame

    observed = int(frame["arrivals"].sum())
    if observed != expected:
        observed_states = set(frame["state"])
        missing_states = sorted(set(US_STATES) - observed_states)
        month_totals = (
            frame.groupby("calendar_month")["arrivals"].sum().to_dict()
            if "calendar_month" in frame.columns
            else {}
        )
        raise ValueError(
            f"FY{fiscal_year} parsed total does not reconcile: "
            f"observed={observed}, expected={expected}, "
            f"states={len(observed_states)}, missing={missing_states}, "
            f"month_totals={month_totals}"
        )
    return frame



def reconcile_missing_pdf_states(
    primary: pd.DataFrame,
    alternatives: list[pd.DataFrame],
    fiscal_year: int,
) -> pd.DataFrame:
    expected = EXPECTED_RPC_ANNUAL_TOTALS.get(fiscal_year)
    if expected is None or int(primary["arrivals"].sum()) == expected:
        return primary

    combined = primary.copy()
    present_states = set(combined["state"])

    for alternative in alternatives:
        missing = set(alternative["state"]) - present_states
        if not missing:
            continue

        additions = alternative[alternative["state"].isin(missing)].copy()
        combined = pd.concat([combined, additions], ignore_index=True)
        present_states.update(missing)

        if int(combined["arrivals"].sum()) == expected:
            return combined.sort_values(["state", "date"]).reset_index(drop=True)

    return combined.sort_values(["state", "date"]).reset_index(drop=True)


def parse_state_month_bytes(
    source: RPCSource,
    content: bytes,
    retrieved_at_utc: str,
) -> pd.DataFrame:
    if source.file_type != "pdf":
        raise ValueError(
            f"Monthly state detail is not available in archived {source.file_type} "
            f"source for FY{source.fiscal_year}"
        )

    if source.fiscal_year in {2021, 2022, 2023, 2024}:
        frame = ocr_pdf_total_rows_to_state_month(
            content=content,
            fiscal_year=source.fiscal_year,
            source_url=source.url,
            source_file=source.filename,
            retrieved_at_utc=retrieved_at_utc,
        )

        expected = EXPECTED_RPC_ANNUAL_TOTALS.get(source.fiscal_year)
        if expected is not None and int(frame["arrivals"].sum()) != expected:
            rows = pdf_rows(content)
            alternatives = []

            for parser in (rows_to_state_month, pdf_rows_to_state_month):
                try:
                    alternatives.append(
                        parser(
                            rows=rows,
                            fiscal_year=source.fiscal_year,
                            source_url=source.url,
                            source_file=source.filename,
                            retrieved_at_utc=retrieved_at_utc,
                        )
                    )
                except ValueError:
                    pass

            frame = reconcile_missing_pdf_states(
                primary=frame,
                alternatives=alternatives,
                fiscal_year=source.fiscal_year,
            )

        return validate_pdf_year_total(frame, source.fiscal_year)

    rows = pdf_rows(content)

    try:
        frame = rows_to_state_month(
            rows=rows,
            fiscal_year=source.fiscal_year,
            source_url=source.url,
            source_file=source.filename,
            retrieved_at_utc=retrieved_at_utc,
        )
        return validate_pdf_year_total(frame, source.fiscal_year)
    except ValueError:
        pass

    try:
        frame = pdf_rows_to_state_month(
            rows=rows,
            fiscal_year=source.fiscal_year,
            source_url=source.url,
            source_file=source.filename,
            retrieved_at_utc=retrieved_at_utc,
        )
        return validate_pdf_year_total(frame, source.fiscal_year)
    except ValueError:
        pass

    if source.fiscal_year == 2024:
        frame = ocr_pdf_total_rows_to_state_month(
            content=content,
            fiscal_year=source.fiscal_year,
            source_url=source.url,
            source_file=source.filename,
            retrieved_at_utc=retrieved_at_utc,
        )
        return validate_pdf_year_total(frame, source.fiscal_year)

    frame = ocr_pdf_to_state_month(
        content=content,
        fiscal_year=source.fiscal_year,
        source_url=source.url,
        source_file=source.filename,
        retrieved_at_utc=retrieved_at_utc,
    )
    return validate_pdf_year_total(frame, source.fiscal_year)


def parse_state_fiscal_year_bytes(
    source: RPCSource,
    content: bytes,
    retrieved_at_utc: str,
) -> pd.DataFrame:
    if source.file_type in {"xls", "xlsx"}:
        return excel_rows_to_state_fiscal_year(
            rows=excel_rows(content),
            fiscal_year=source.fiscal_year,
            source_url=source.url,
            source_file=source.filename,
            retrieved_at_utc=retrieved_at_utc,
        )

    if source.file_type == "pdf":
        monthly = parse_state_month_bytes(source, content, retrieved_at_utc)
        return state_fiscal_year_from_monthly(monthly)

    raise ValueError(f"Unsupported RPC source type: {source.file_type}")


def parse_source_bytes(
    source: RPCSource,
    content: bytes,
    retrieved_at_utc: str,
) -> pd.DataFrame:
    return parse_state_month_bytes(source, content, retrieved_at_utc)


def build_rpc_panels(
    sources: list[RPCSource],
    raw_dir: Path,
    manifest_path: Path,
    monthly_output_path: Path,
    annual_output_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    manifest: list[dict] = []
    monthly_frames: list[pd.DataFrame] = []
    annual_frames: list[pd.DataFrame] = []
    client = requests.Session()

    for source in sources:
        metadata = download_source(source, raw_dir, session=client)
        manifest.append(metadata)
        content = Path(metadata["local_path"]).read_bytes()
        retrieved_at = metadata["retrieved_at_utc"]

        annual_frames.append(
            parse_state_fiscal_year_bytes(source, content, retrieved_at)
        )

        if source.file_type == "pdf":
            monthly_frames.append(
                parse_state_month_bytes(source, content, retrieved_at)
            )

    annual_panel = pd.concat(annual_frames, ignore_index=True)
    annual_panel = annual_panel.sort_values(["fiscal_year", "state"]).reset_index(
        drop=True
    )

    monthly_panel = pd.concat(monthly_frames, ignore_index=True)
    monthly_panel = monthly_panel.sort_values(["state", "date"]).reset_index(drop=True)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    monthly_output_path.parent.mkdir(parents=True, exist_ok=True)
    monthly_panel.to_csv(monthly_output_path, index=False)

    annual_output_path.parent.mkdir(parents=True, exist_ok=True)
    annual_panel.to_csv(annual_output_path, index=False)

    return monthly_panel, annual_panel
