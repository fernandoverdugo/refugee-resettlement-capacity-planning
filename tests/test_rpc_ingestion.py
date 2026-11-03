from src.ingestion.rpc import (
    RPCSource,
    fiscal_year_for_month,
    normalize_ocr_number,
    excel_rows_to_state_fiscal_year,
    pdf_rows_to_state_month,
    rows_to_state_month,
)


def test_fiscal_year_calendar_mapping():
    assert fiscal_year_for_month(2025, "Oct") == 2024
    assert fiscal_year_for_month(2025, "Dec") == 2024
    assert fiscal_year_for_month(2025, "Jan") == 2025
    assert fiscal_year_for_month(2025, "Sep") == 2025


def test_rows_to_state_month_uses_state_total_rows():
    rows = [
        ["Affiliate State Name", "PA Nationality", "Oct", "Nov", "Dec", "Grand Total"],
        ["Texas", "Total", "10", "20", "30", "60"],
        ["", "Afghanistan", "4", "5", "6", "15"],
        ["", "Burma", "6", "15", "24", "45"],
        ["Utah", "Total", "1", "", "2", "3"],
        ["", "Syria", "1", "", "2", "3"],
    ]

    frame = rows_to_state_month(
        rows=rows,
        fiscal_year=2025,
        source_url="https://example.test/report.pdf",
        source_file="report.pdf",
        retrieved_at_utc="2026-11-03T00:00:00+00:00",
    )

    assert len(frame) == 6
    assert set(frame["state"]) == {"Texas", "Utah"}
    assert frame["arrivals"].sum() == 63
    assert set(frame["date"]) == {
        "2024-10-01",
        "2024-11-01",
        "2024-12-01",
    }


def test_rpc_source_shape():
    source = RPCSource(
        fiscal_year=2025,
        url="https://example.test/report.pdf",
        filename="report.pdf",
        file_type="pdf",
    )
    assert source.fiscal_year == 2025
    assert source.file_type == "pdf"


def test_pdf_rows_sum_nationality_rows_by_state():
    rows = [
        ["Actual Destination", "PA Nationality", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Grand Total"],
        ["Texas Afghanistan\nBurma", "Afghanistan", "4", "5", "6", "", "", "", "", "", "", "", "", "", "15"],
        [None, None, "6", "15", "24", "", "", "", "", "", "", "", "", "", "45"],
        ["Utah Syria", "Syria", "1", "", "2", "", "", "", "", "", "", "", "", "", "3"],
    ]

    frame = pdf_rows_to_state_month(
        rows=rows,
        fiscal_year=2025,
        source_url="https://example.test/report.pdf",
        source_file="report.pdf",
        retrieved_at_utc="2026-11-03T00:00:00+00:00",
    )

    texas = frame[frame["state"] == "Texas"]
    assert texas["arrivals"].sum() == 60
    assert set(texas["arrivals"]) == {0, 10, 20, 30}

    utah = frame[frame["state"] == "Utah"]
    assert utah["arrivals"].sum() == 3


def test_pdf_rows_emit_zero_months_and_ignore_footer_values():
    rows = [
        ["Actual Destination", "PA Nationality", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Grand Total"],
        ["Texas Afghanistan", "Afghanistan", "4", "", "", "", "", "", "", "", "", "", "", "", "4"],
        ["Based on source notes", None, "999", "999", "999", "999", "", "", "", "", "", "", "", "", "3996"],
    ]

    frame = pdf_rows_to_state_month(
        rows=rows,
        fiscal_year=2025,
        source_url="https://example.test/report.pdf",
        source_file="report.pdf",
        retrieved_at_utc="2026-11-03T00:00:00+00:00",
    )

    assert len(frame) == 12
    assert frame["arrivals"].sum() == 4
    assert frame.loc[frame["calendar_month"] == 11, "arrivals"].iloc[0] == 0


def test_excel_rows_to_state_fiscal_year():
    rows = [
        ["Placement State", None, None, "Cumulative"],
        [None, "Nationality", "FY 2019", "Total"],
        ["Texas", None, 2456, 2456],
        [None, "Afghanistan", 100, 100],
        ["Utah", None, 463, 463],
        [None, "Syria", 10, 10],
    ]

    frame = excel_rows_to_state_fiscal_year(
        rows=rows,
        fiscal_year=2019,
        source_url="https://example.test/report.xlsx",
        source_file="report.xlsx",
        retrieved_at_utc="2026-11-03T00:00:00+00:00",
    )

    assert len(frame) == 2
    assert frame.loc[frame["state"] == "Texas", "arrivals"].iloc[0] == 2456
    assert frame.loc[frame["state"] == "Utah", "arrivals"].iloc[0] == 463


def test_normalize_ocr_number_common_confusions():
    assert normalize_ocr_number("1s") == 15
    assert normalize_ocr_number("S") == 5
    assert normalize_ocr_number("1,274") == 1274
    assert normalize_ocr_number("") is None
