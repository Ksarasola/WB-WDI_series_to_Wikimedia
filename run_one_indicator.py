"""Process a single named WDI indicator end-to-end: steps 06, 07, 07b, 04, the
retrieval-audit CSV, then 05, 05b (via run_indicator_export() in wb_api_raw_export_lib.py).
Does NOT touch the catalog or the 6 dataset-level metadata files - use
wb_wdi_pipeline.py or metadata_wdi_dataset_files.py for those.

Usage:
    python3 run_one_indicator.py --code {IndicatorCode} --out-dir /path/to/folder
    python3 run_one_indicator.py --code {IndicatorCode} --out-dir /path/to/folder --force

Produces (in --out-dir, skipping any that already exist unless --force is passed):
    WB_WDI_<code>_data.json                  raw API response pages, for provenance
    WB_WDI_<code>_data.csv                   entity, year, value, annotations
    WB_WDI_<code>_data.tab                   same rows as the .csv above, ready to
                                              paste into a Wikimedia Commons
                                              Data:...tab page (license, sources,
                                              description in English + Basque, and
                                              Commons category already set)
    WB_WDI_<code>_metadata_indicator.json    raw indicator metadata
    WB_WDI_<code>_metadata_indicator.csv     spec-compliant tabular transform
    WB_WDI_<code>_metadata_indicator.tab     same content as the .csv above, as a
                                              ready-to-paste Data:...tab file
    WB_WDI_<code>_metadata_series.json       raw series metadata (richer fields)
    WB_WDI_<code>_metadata_series.csv        spec-compliant tabular transform
    WB_WDI_<code>_metadata_series.tab        same content as the .csv above, as a
                                              ready-to-paste Data:...tab file
    WB_WDI_<code>_metadata_retrieval.csv     retrieval audit stats (always
                                              regenerated, cheap local computation)
"""

import argparse
from pathlib import Path

from wb_api_raw_export_lib import run_indicator_export, safe_code_for_filename


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True, help="WDI indicator code, e.g. SP.DYN.LE00.IN")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--force", action="store_true", help="Re-download/reprocess even if cached files already exist"
    )
    args = parser.parse_args()

    base_name = f"WB_WDI_{safe_code_for_filename(args.code)}"
    run_indicator_export(args.code, args.out_dir, base_name, force=args.force)


if __name__ == "__main__":
    main()
