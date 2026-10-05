README - World Bank WDI Raw Export Toolkit  

This folder contains for Python files and one python Netbook that together download original World Bank World Development Indicators (WDI) data directly from the live World Bank API (api.worldbank.org), create corresponding items in Wikimedia Commons and Wikidata for this indicator and finally add an graphic for this indicator at the end of an existing page of Basque Wikipedia.


And turn it into tidy CSVs plus Wikimedia Commons-ready .tab files. 

Files: 

1. run_wikify indicator.py
   The core library for the whole process of importing data-series from WB-WDI to Wikimedia 
    and use it for adding a graphic in a Basque Wikipedia page related to the subject. 
   It generates a new WB-WDI indicator on Commons, Wikidata, and Wikipedia, allowing all necessary changes 
   to be made automatically through the program.  
   As there many arguments this function can be executed using the wikify_one_indicator function 
   in a PAWS Python Notebook (wb_indicator2wmc_wd_wp.ipynb). 
   For example, It was used in the following way to work on the "public debt" indicator:

    wikify_one_indicator (
                              indicator = "GC.DOD.TOTL.GD.ZS", 
                              subdir = "ZOR_PUBL",
                              prefix = "WB_WDI_",
                              eu_description = "Central government debt. Total public debt (% of GDP)",
                              en_description = "Central government debt, total (% of GDP)",
                              es_description = "Deuda del Gobierno central. Deuda pública total (% del PIB)",
                              q_main_subject = "Q3024789" ,
                              main_subject   = "government debt",
                              wp_article     = "Public debt") 

    This call automatically created all these elements:
    
        - In the ZOR_PUBL subdirectory, the indicator's data and metadata tab files 
        - Data:WB WDI GC.DOD.TOTL.GD.ZS data.tab          (data tab file on Commons)
        - Data talk:WB WDI GC.DOD.TOTL.GD.ZS data.tab     (metadata tab file on Commons)
        - https://www.wikidata.org/wiki/Q141507431        (data series item in Wikidata)
        - Data:WB WDI GC.DOD.TOTL.GD.ZS.chart             (chart file needed for creating graphs with the series data)
        - https://eu.wikipedia.org/wiki/Public debt       (Added a graph at the end of that Wikipedia page)



    run_wikify indicator function implements the following six "steps".

    # Create the data tab files in the subdirectory
    01 run_indicator_export(indicator, subdir, base_name)

    02 create_data_tab_file_on_commons (indicator, subdir, prefix)
    03 create_metadata_tab_file_on_commons (indicator, subdir, prefix)
    04 create_data_series_item_on_wikidata  (indicator, 
                                          prefix,      
                                          eu_description,
                                          en_description,
                                          q_main_subject,
                                          main_subject)    
    05 create_chart_file_on_commons (indicator, 
                                  prefix,
                                  eu_description,
                                  en_description,
                                  es_description)
    06 add_chart_with_series_data_to_wp_article (wp_article,
                                              indicator, 
                                              prefix,
                                              eu_description,
                                              en_description,
                                              es_description)

    
    # Another usage example from run_wikify_indicator.ipynb note book:
    # wikify_one_indicator (indicator = "SI.POV.GINI", 
    #                       subdir = "GINI",
    #                       prefix = "WB_WDI_",
    #                       eu_description = "GINI indizea",
    #                       en_description = "GINI index",
    #                       es_description = "Indice GINI",
    #                       q_main_subject = "",
    #                       main_subject
    #                       wp_article = "Giniren koefiziente") 




2. wb_api_raw_export_lib.py 
   The library to import data-series from WB-WDI. Implements eight numbered "steps" plus a couple of 
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
  
3. wb_metadata_to_csv_lib.py 
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


User explanations in Basque:
Hauek dira orain arte ditugun programak.

    Deskonprimatu WB_WDI_wikira_v0.zip  eta Jarri fitxategiak PAWS-eko karpeta batean 
    Aukeratu WB_WDI adierazle berri bat hemen: https://data.worldbank.org/indicator
    Hartu identifikatzailea eta  definizio motza. Adibidez:
        https://data.worldbank.org/indicator/IP.JRN.ARTC.SC
        IP.JRN.ARTC.SC
        Scientific and technical journal articles
    Ireki   PAWS wb_indicator2wmc_wd_wp_erabilera.ipynb
    Egokitu argumentuen balioak.
    Hau da lehen egin dudan exekuzio bat:

        wikify_one_indicator (adierazlea = "EN.URB.MCTY.TL.ZS", 
                              subdir = "RB.MCTY",
                              aurrizkia = "WB_WDI_",
                              eu_description = "Hri handietako biztanleriaren % (> milioi bat)",
                              en_description = "Population in urban agglomerations > 1 million (% of total population)",
                              es_description = "% Población en ciudades > 1 millón",
                              q_main_subject = "Q702492",
                              main_subject =  "Hiri eremu",
                              wp_article = "Hiri eremu") 

    Beraz, honela egokitu:

        "EN.URB.MCTY.TL.ZS"   -->  "IP.JRN.ARTC.SC"
        "RB.MCTY"                     -->   "ARTC"                     #Nahi duzuen izena, azpidirektoriori emateko
        Aurrizkiaren bet berdin ("WB_WDI_"), hori ez aldatu.
        en_description              -->   "Scientific and technical journal articles"
                                                        Hemendik hartuta: https://data.worldbank.org/indicator/IP.JRN.ARTC.SC   
        eu_description eta   es_description    berdin baina itzulita.
        "Q702492"                    -->    Bilatu ingeleseko wikipedian main subject izateko artikulu egoki bat 
                                                        https://en.wikipedia.org/wiki/Scientific_literature  adibidez?
                                                             wikidatan --> zientzia literatura (Q12042160)
                                                                   Beraz      q_main_subject = "Q12042160"
                                                                                    main_subject =  "Zientzia literatura"
                                                                                   wp_article = "Zientzia literatura"

    Klikatu goiko menuko "Run" botoian" (eskuinera  begiratzen duen triangelu/gezia)
    Programak idatziko du zer sortzen ari den.
    Dena ondo joan bada horrela bukatuko da

    [...]
    Sleeping for 9.3 seconds, 2026-09-22 12:03:47    (beste datu batzuekin, baina antzeko zerbait)
    Page [[Zientzia literatura]] saved


    Begiratu Wikipedian Zientzia literatura artikulua
    Bukaeran Erreferentziak atala baino lehenago IP.JRN.ARTC.SC adierazlearen grafiko bat azaldu behar da.
    Ikusi ea ondo dagoen   ;-)

    Arazorik badago... egun batean bilduko gara fakultatean. Zein zuretzat egun egokia Beñat? Galder?
