from __future__ import annotations

import json

from src.config import PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.ingestion.rpc import build_rpc_panels, discover_rpc_sources

MANIFEST_PATH = RAW_DATA_DIR / "rpc_source_manifest.json"
MONTHLY_OUTPUT_PATH = PROCESSED_DATA_DIR / "rpc_state_month.csv"
ANNUAL_OUTPUT_PATH = PROCESSED_DATA_DIR / "rpc_state_fiscal_year.csv"


def main() -> None:
    sources = discover_rpc_sources()
    print(
        json.dumps(
            [
                {
                    "fiscal_year": source.fiscal_year,
                    "file_type": source.file_type,
                    "url": source.url,
                }
                for source in sources
            ],
            indent=2,
        )
    )

    monthly, annual = build_rpc_panels(
        sources=sources,
        raw_dir=RAW_DATA_DIR / "rpc",
        manifest_path=MANIFEST_PATH,
        monthly_output_path=MONTHLY_OUTPUT_PATH,
        annual_output_path=ANNUAL_OUTPUT_PATH,
    )

    print(
        json.dumps(
            {
                "sources": len(sources),
                "annual_rows": len(annual),
                "annual_states": int(annual["state"].nunique()),
                "annual_first_fy": int(annual["fiscal_year"].min()),
                "annual_last_fy": int(annual["fiscal_year"].max()),
                "monthly_rows": len(monthly),
                "monthly_states": int(monthly["state"].nunique()),
                "monthly_first_date": monthly["date"].min(),
                "monthly_last_date": monthly["date"].max(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
