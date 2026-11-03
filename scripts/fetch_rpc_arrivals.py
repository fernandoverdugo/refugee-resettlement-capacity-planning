from __future__ import annotations

import json

from src.config import PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.ingestion.rpc import build_state_month_panel, discover_rpc_sources

MANIFEST_PATH = RAW_DATA_DIR / "rpc_source_manifest.json"
OUTPUT_PATH = PROCESSED_DATA_DIR / "rpc_state_month.csv"


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

    panel = build_state_month_panel(
        sources=sources,
        raw_dir=RAW_DATA_DIR / "rpc",
        manifest_path=MANIFEST_PATH,
        output_path=OUTPUT_PATH,
    )

    print(
        json.dumps(
            {
                "sources": len(sources),
                "rows": len(panel),
                "states": int(panel["state"].nunique()),
                "first_date": panel["date"].min(),
                "last_date": panel["date"].max(),
                "arrivals": int(panel["arrivals"].sum()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
