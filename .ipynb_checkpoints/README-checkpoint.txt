README - World Bank WDI Raw Export Toolkit  

This folder contains three Python files that together download original World 

Bank World Development Indicators (WDI) data directly from the live World 

Bank API (api.worldbank.org). And turn it into tidy CSVs plus Wikimedia Commons-ready .tab files. 



Files: 

1. wb_api_raw_export_lib.py 

   The core library. Implements eight numbered "steps" plus a couple of 

   helper routines, all built around a simple convention, every output file 

   is skipped if it already exists, unless force=True is passed, so re-runs 

   only cost time for what is new or explicitly forced. 

  

     01  fetch_catalog_with_cache()        Full list of indicators available 

                                            in a WDI source (the catalog). 

     02  fetch_metadata_originals()        Generic downloader, given a list 

                                            of (url, filename) pairs, caches 

                                            each response verbatim. Used both 

                                            for dataset-level metadata and for 

                                            per-indicator metadata (step 06). 

     03  build_dataset_metadata_csvs()     Turns the dataset-level metadata 

                                            originals into one-line-per-row 

                                            CSVs (wraps wb_metadata_to_csv_lib). 

     03b build_dataset_metadata_tabs()     Same as 03, but as .tab files ready 

                                            to paste into a Wikimedia Commons 

                                            Data:...tab page. 

     04  fetch_dataseries_data()           Downloads one indicator's raw, 

                                            paginated data (<base>_data.json). 

     05  build_dataseries_csv()            Turns a *_data.json into the tidy 

                                            entity/year/value/annotations CSV. 

     05b build_dataseries_tab()            Same rows as 05, as a .tab file, 

                                            with license, sources, an English 

                                            + Basque description, and a 

                                            Commons category already set. 

     06  dataseries_metadata_resources()   Builds the (url, filename) pairs 

                                            for one indicator's own metadata 

                                            (indicator + series metadata), 

                                            for use with step 02. 

     07  build_dataseries_metadata_csv()   Turns an indicator's metadata 

                                            originals into spec-compliant CSVs 

                                            (wraps wb_metadata_to_csv_lib). 

     07b build_dataseries_metadata_tab()   Same as 07, but as .tab files. 

     08  run_full_wdi_export()             Orchestrator: 01 + 02+03+03b 

                                            (dataset-level, once) + a loop of 

                                            04/06/07/07b/05/05b over every 

                                            indicator in the catalog. 

  

   Also included: 

     - run_indicator_export()   The single-indicator building block (steps 

                                 06, 07, 07b, 04, a retrieval-audit CSV, then 

                                 05, 05b) shared by run_full_wdi_export() and 

                                 by run_one_indicator.py, so the per-indicator 

                                 logic lives in exactly one place. 

     - safe_code_for_filename() Sanitizes an indicator code for safe use in a 

                                 filename. 

     - Automatic retry with backoff for flaky/slow World Bank API responses 

       (HTTP 502/503/504 and network errors), and a workaround for an API 

       quirk where some endpoints return gzip-compressed bodies without the 

       matching Content-Encoding header. 

  

   Only dependencies: `requests` and `pandas`. 

  

2. wb_metadata_to_csv_lib.py 

   Helper library used by wb_api_raw_export_lib.py to convert a raw JSON or 

   XML metadata file into a simple, single-column CSV, one row per line of 

   the pretty-printed source content. This "beautify and split into lines" 

   approach needs no per-endpoint parsing logic, at the cost of not being 

   queryable field-by-field (it's a readable, line-searchable rendering of 

   the original file, not a structured table). 

  

   Main functions: 

     - metadata_json_to_csv() / metadata_xml_to_csv() 

           Pretty-print + one CSV row per line. 

     - metadata_json_to_tab() / metadata_xml_to_tab() 

           Same content, packaged as a Wikimedia Commons Data:...tab JSON 

           file (adds license, sources URL, English/Basque description, and 

           Commons categories). 

     - translate_to_basque() 

           Free, keyless machine translation (via the MyMemory API) used to 

           auto-fill the Basque ("eu") description field on .tab files. 

           Best-effort: falls back to the original English text if the 

           translation call fails for any reason. 

  

   Also handles several Wikimedia Commons .tab import constraints 

   automatically, converting leading spaces to underscores so indentation 

   survives rendering, wrapping any line over 400 characters into 

   continuation rows (prefixed with "+"), and escaping stray control 

   characters (tabs, newlines, CRLF) that would otherwise break the format. 

  

3. run_one_indicator.py 

   Command-line entry point to process a single named WDI indicator 

   end-to-end, without touching the catalog or the dataset-level metadata 

   files (use a separate full-pipeline script for those). 

  

   Usage: 

       python3 run_one_indicator.py --code {IndicatorCode} --out-dir /path/to/folder 

       python3 run_one_indicator.py --code {IndicatorCode} --out-dir /path/to/folder --force 

  

   --code       WDI indicator code (e.g. SP.DYN.LE00.IN). 

   --out-dir    Folder where output files are written (created if missing). 

   --force      Re-download/reprocess even if cached files already exist. 

  

   Output files (in --out-dir, using the pattern WB_WDI_<code>_...): 

     _data.json                  Raw API response pages (for provenance). 

     _data.csv                   Tidy entity, year, value, annotations table. 

     _data.tab                   Same rows as the .csv, ready to paste into a 

                                  Wikimedia Commons Data:...tab page (license, 

                                  sources, English + Basque description, and 

                                  Commons category already set). 

     _metadata_indicator.json    Raw indicator metadata, as returned by the API. 

     _metadata_indicator.csv     Spec-compliant tabular transform of the above. 

     _metadata_indicator.tab     Same content as the .csv, as a .tab file. 

     _metadata_series.json       Raw series metadata (richer fields). 

     _metadata_series.csv        Spec-compliant tabular transform of the above. 

     _metadata_series.tab        Same content as the .csv, as a .tab file. 

     _metadata_retrieval.csv     Retrieval audit stats (retrieval URL/date, 

                                 entity/year coverage, row counts). Always 

                                 regenerated, since it's a cheap local 

                                 computation from data already on disk. 

  

   Any output that already exists is skipped unless --force is passed. 

  

Requirements: 

- Python 3 (uses `list[str]` type hints) 

- pip install requests pandas 

  

Notes: 

- These scripts only cover a single indicator at a time. Full-catalog runs 

  (steps 01-03b plus a loop over every indicator) are handled by 

  run_full_wdi_export() in wb_api_raw_export_lib.py, meant to be driven by a 

  separate orchestrator script (not included in this set of three files). 

- All network calls retry automatically on transient failures (timeouts, 

  connection errors, and HTTP 502/503/504), giving up after 5 attempts with 

  exponential backoff. 