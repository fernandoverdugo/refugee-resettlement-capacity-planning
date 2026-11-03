from src.ingestion.rpc import (
    RPCSource,
    fiscal_year_for_month,
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
