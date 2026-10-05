import pywikibot
import json
from wb_api_raw_export_lib import run_indicator_export, safe_code_for_filename

# from wb_metadata_to_csv_lib import (
#     translate_to_basque
# )


def wikify_one_indicator (indicator, 
                          subdir,
                          prefix,
                          eu_description,
                          en_description,
                          es_description,
                          q_main_subject,
                          main_subject,
                          wp_article) :
 
    # Example:
          # indicator = "GC.DOD.TOTL.GD.ZS", 
          # subdir = "ZOR_PUBL",
          # prefix = "WB_WDI_",
          # eu_description = "Gobernu zentralaren zorra. Zor publikoa guztira (BPGaren %)",
          # en_description = "Central government debt, total (% of GDP)",
          # es_description = "Deuda del Gobierno central. Deuda pública total (% del PIB)",
          # q_main_subject =  "Q3024789" ,
          # main_subject =  "government debt",
          # wp_article = "Zor publiko") 

    # Create the data tab files in the subdirectory
    base_name = f"{prefix}{safe_code_for_filename(indicator)}"
    run_indicator_export(indicator, subdir, base_name)


    create_data_tab_file_on_commons (indicator, subdir, prefix)
    create_metadata_tab_file_on_commons (indicator, subdir, prefix)
    create_data_series_item_on_wikidata  (indicator, 
                                          prefix,      
                                          eu_description,
                                          en_description,
                                          q_main_subject,
                                          main_subject)
    
    create_chart_file_on_commons (indicator, 
                                  prefix,
                                  eu_description,
                                  en_description,
                                  es_description)

    add_chart_with_series_data_to_wp_article (wp_article,
                                              indicator, 
                                              prefix,
                                              eu_description,
                                              en_description,
                                              es_description)

    # Usage example:
    # wikify_one_indicator (indicator = "SI.POV.GINI", 
    #                       subdir = "GINI",
    #                       prefix = "WB_WDI_",
    #                       eu_description = "GINI indizea",
    #                       en_description = "GINI index",
    #                       es_description = "Indice GINI",
    #                       q_main_subject = "",
    #                       main_subject
    #                       wp_article = "Giniren koefiziente") 



# Create the data .tab file on Commons
def create_data_tab_file_on_commons (indicator, 
                                     subdir, 
                                     prefix) :

    #  The files were previously created with the run_one_indicator.py program, like this:
    #  $ python3 run_one_indicator.py --code SL.UEM.1524.MA.ZS --out-dir UEM_MA
    
    # 1) Read your local file
    #indicator = "SI.POV.GINI"
    #subdir = "GINI"
    #prefix = "WB_WDI_"
    #tab_file = "Data:WB_WDI_SI.POV.GINI_data.tab"
    file_name = subdir + '/' + prefix + indicator + "_data.tab"
    page_name = "Data:" + prefix + indicator + "_data.tab"
    
    with open(file_name, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check that it is really valid JSON before uploading
    data = json.loads(content)  # this will raise an error if the format is not correct
    print(json.dumps(data, indent=2, ensure_ascii=False)[:500])  # preview
    
    # 2) Connect to Commons
    site = pywikibot.Site("commons", "commons")
    site.login()
    
    # 3) Upload the content of the file (file_name) to Commons (page_name)
    page = pywikibot.Page(site, page_name)
    
    page.text = content
    page.save(summary= "data series upload")
    
    print("Uploaded:", page.full_url())

# Create the metadata .tab file on Commons
def create_metadata_tab_file_on_commons (indicator, 
                                         subdir, 
                                         prefix) :
    
    # 1) Read your local JSON file
    # indicator = "SL.UEM.1524.MA.ZS"
    #json_file = "NETM/WB_WDI_SL.UEM.1524.MA.ZS_metadata_indicator.json"
    # Where to put it: "Data talk:NETM/WB_WDI_SL.UEM.1524.MA.ZS_data.tab"
    # subdir = "UEM_MA"
    # prefix = "WB_WDI_"
    file_name = subdir + '/' + prefix + indicator + "_metadata_indicator.json"
    page_name = "Data talk:" + prefix + indicator + "_data.tab"
    with open(file_name, "r", encoding="utf-8") as f:
        metadata_content = f.read()
    
    # Check that the JSON is valid (optional, but recommended)
    metadata_json = json.loads(metadata_content)
    formatted_json = json.dumps(metadata_json, indent=2, ensure_ascii=False)
    
    # 2) Connect to Commons
    site = pywikibot.Site("commons", "commons")
    site.login()
    
    # 3) Talk page name: "Data talk:" prefix, instead of "Data:"
    talk_page = pywikibot.Page(site, page_name)
    
    # 4) Build the wikitext, with the JSON inside <syntaxhighlight>
    wikitext = f"""== Metadatuak (WB_WDI_SL.UEM.1524.MA.ZS) ==
    
    Adierazlearen metadatuak, World Bank iturritik:
    
    <syntaxhighlight lang="json">
    {formatted_json}
    </syntaxhighlight>
    """
    
    talk_page.text = wikitext
    talk_page.save(summary="Indicator's metadata added " + indicator)
    
    print("Uploaded:", talk_page.full_url())

# Create the data series item on Wikidata
def create_data_series_item_on_wikidata (indicator, 
                                         prefix, 
                                         eu_description,
                                         en_description,
                                         q_main_subject,
                                         main_subject) :
    
    # --- Adjust the maxlag configuration (to reduce Sleeping delays) ---
    pywikibot.config.maxlag = 15       # default is 5; raising it makes it more tolerant
    pywikibot.config.max_retries = 30  # allow more attempts before giving up
    pywikibot.config.retry_wait = 10   # first wait time (in seconds)
    pywikibot.config.retry_max = 60    # maximum wait time per attempt
    
    # Example:
    #     indicator = "SL.UEM.1524.MA.ZS"
    #     prefix =  "WB_WDI_"
        # eu_description = "Langabezia, gizonezko gazteak (15-24 urteko emakumezkoen lan-indarraren %) (modeled ILO estimate)"  
        # en_description = "Unemployment, youth male (% of female labor force ages 15-24) (modeled ILO estimate)" 
        # q_main_subject =  "Q4261734" # TO BE ADAPTED!!!
        # main_subject =  "Youth unemployment (male)"  # TO BE ADAPTED!!!

    print ( indicator)
    
    data_series = "Data:" + prefix + indicator + "_data.tab"
    eu_label =              prefix + indicator + " datu-seriea"
    en_label =              prefix + indicator + " data-series"
    
    print (main_subject + '?')
    
    # --- Connection to Wikidata ---
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()
    site.login()
    
    # --- Create a new item ---
    item = pywikibot.ItemPage(repo)
    
    # --- Labels and descriptions ---
    labels = {
    "eu": eu_label,
    "en": en_label,
    }
    
    descriptions = {
    "eu": eu_description,
    "en": en_description,
    }
    
    item.editLabels(labels, summary="Add labels")
    item.editDescriptions(descriptions, summary="Add descriptions")
    
    # --- Helper: add a statement whose value is an item reference ---
    
    def add_item_claim(item, prop_id, target_qid, summary, reference_url=None):
        claim = pywikibot.Claim(repo, prop_id)
        target = pywikibot.ItemPage(repo, target_qid)
        claim.setTarget(target)
        item.addClaim(claim, summary=summary)
        
        if reference_url:
            ref_url = pywikibot.Claim(repo, "P854")
            ref_url.setTarget(reference_url)
            claim.addSources([ref_url], summary="Add reference URL")
        
        return claim    
    
    # --- P31: instance of -> time series (Q186588) ---
    add_item_claim(item, "P31", "Q186588", "instance of: time series")
    
    # --- P361: part of -> World Development Indicators (Q8035640) ---
    add_item_claim(item, "P361", "Q8035640", "part of: World Development Indicators")
    
    # --- P921: main subject -> Net migration rate (Q1932516) ---
    add_item_claim(item, "P921", q_main_subject, "main subject: " + main_subject)
    
    # --- P123: publisher -> World Bank (Q7164) ---
    add_item_claim(
    item, "P123", "Q7164", "publisher: World Bank",
    reference_url="https://data.worldbank.org/indicator/" + indicator
    )
    
    # --- P1813: short name (monolingual text, in English) ---
    claim_shortname = pywikibot.Claim(repo, "P1813")
    shortname_value = pywikibot.WbMonolingualText(text=indicator, language="en")
    claim_shortname.setTarget(shortname_value)
    item.addClaim(claim_shortname, summary="short name: " + indicator)
    
    # --- P14687: tabular data series (Commons Data: page, tabular-data type) ---
    claim_tabular = pywikibot.Claim(repo, "P14687")
    commons_site = pywikibot.Site("commons", "commons")
    
    # FIRST create the pywikibot.Page object, with the "Data:" prefix
    tab_page = pywikibot.Page(commons_site, data_series)
    
    # Now pass the Page object to WbTabularData
    tabular_value = pywikibot.WbTabularData(
    page=tab_page,
    site=commons_site
    )
    claim_tabular.setTarget(tabular_value)
    item.addClaim(claim_tabular, summary="tabular data series")
    
    print("Created item:", item.getID())
    print("URL:", f"https://www.wikidata.org/wiki/{item.getID()}")

    
# Create the .chart file used to make charts from the data series
def create_chart_file_on_commons (indicator,  
                                  prefix,
                                  eu_description,
                                  en_description,
                                  es_description) :
    
    # Example:
    #     indicator = "SL.UEM.1524.MA.ZS"
    #     prefix =  "WB_WDI_"
    # eu_description = "Langabezia, gizonezko gazteak (15-24 urteko emakumezkoen lan-indarraren %)"  # TO BE ADAPTED!!!
    # en_description = "Unemployment, youth male (% of female labor force ages 15-24)"  # TO BE ADAPTED!!!
    # es_description = "Paro juvenil masculino (% de la fuerza laboral femenina en edad 15-24)"  # TO BE ADAPTED!!!

    print ( indicator)
    data_series = "Data:" + prefix + indicator + "_data.tab"
    chart_file_name = "Data:"+ prefix + indicator+".chart"
    
    # 1) Read your local .chart file
    with open("Chart_template.chart", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check that the JSON is valid
    chart_data = json.loads(content)
    print(json.dumps(chart_data, indent=2, ensure_ascii=False)[:500])  # preview
    
    # --- Set the new values: yAxis -> title -> en/eu/es ---
    chart_data["yAxis"]["title"]["en"] = en_description
    chart_data["yAxis"]["title"]["eu"] = eu_description
    chart_data["yAxis"]["title"]["es"] = es_description
    chart_data["source"] = data_series
    
    # Convert back to a string, to save/use it
    adapted_content = json.dumps(chart_data, ensure_ascii=False, indent=2)
    
    print(adapted_content[:1000])  # preview, to check
    # 3) Connect to Commons
    site = pywikibot.Site("commons", "commons")
    site.login()
    
    # 4) Create/edit the Data: page, ending in ".chart"
    page = pywikibot.Page(site, chart_file_name)
    
    page.text = adapted_content
    page.save(summary="Data:.chart file upload")
    
    print("Uploaded:", page.full_url())

# Add a chart with the data series data to a Wikipedia article
# (inserted at the end as the last section, before the references).
def add_chart_with_series_data_to_wp_article (page_name, 
                                              indicator, 
                                              prefix,
                                              eu_description,
                                              en_description,
                                              es_description):   
    # page_name = "Langabezia"
    # indicator = "SL.UEM.1524.MA.ZS"
    # print ( indicator)
    # prefix =  "WB_WDI_"
    data_series = "Data:" + prefix + indicator + "_data.tab"
    # eu_description = "Gizonezko gazteen langabezia"  # TO BE ADAPTED!!!
    # en_description = "Unemployment, youth male"  # TO BE ADAPTED!!!
    # es_description = "Paro juvenil masculino"  # TO BE ADAPTED!!!
        
    # --- Connection to eu.wikipedia ---
    site = pywikibot.Site("eu", "wikipedia")
    site.login()
    
    page = pywikibot.Page(site, page_name)
    text = page.text
    
    # --- Add the new section you want ---
    new_section = "\n== "+ eu_description +" (bilakaera, ''"+ indicator +"""'' datu-seriea) ==\n[[Munduko Bankua|Munduko Bankuak]] [[Denbora serie|denbora-serie]] estatistiko bat eskaintzen du herrialde bakoitzean 1990az geroztik urtero izan diren datuekin.<ref name="WB">{{Erreferentzia|izenburua="""+eu_description+"""|url=https://data.worldbank.org/indicator/"""+ indicator +"""|aldizkaria=World Bank Open Data|sartze-data=2026-07-30}}</ref>
{{image frame|content={{Herrialde grafikoa|"""+ prefix + indicator +""".chart|USA,FRA,ESP,RUS,TUR,MEX,CHN,BRA,EGY,IND,NGA,ETH}}|width=1000|caption="""+ eu_description +""" bilakaera munduko hainbat herrialdetan 1990-2025.<ref name="WB"/>|align=center}}
\n"""
    
    # --- Find the start of the "Erreferentziak" section ---
    marker = "== Erreferentziak =="
    
    if marker not in text:
        raise ValueError(f"Section heading '{marker}' not found in the article. Check the exact name (upper/lower case, spaces).")
    
    # --- Insert the new section BEFORE "Erreferentziak" ---
    new_text = text.replace(marker, new_section + marker, 1)  # 1 = replace only the first occurrence
    
    # --- Preview, before saving ---
    print(new_text[-2000:])  # show the last part, to check
    
    # --- Save (I left it commented out for safety, check first that it is correct) ---
    page.text = new_text
    page.save(summary="Add new section with statistical data (World Bank "+ indicator +")")
    
    """
    RUN example:
    Sleeping for 8.8 seconds, 2026-09-18 11:36:00
    Page [[Giza migrazio]] saved
    """
