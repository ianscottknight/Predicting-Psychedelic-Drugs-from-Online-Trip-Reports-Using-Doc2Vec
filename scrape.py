import util

import requests
from bs4 import BeautifulSoup
import re
import collections
import itertools
import ast
import pickle
import os
import csv
import langdetect
import pandas as pd



"""
Constants
"""
PHASE = 1

DOSAGE_LEVELS = [
    "threshold",
    "light",
    "common",
    "strong",
    "heavy"
]
DOSAGE_UNITS = [
    "µg",
    "mg"
]
DURATION_TYPES = [
    "total",
    "onset",
    "come_up",
    "peak",
    "offset",
    "after_effects"
]
DURATION_UNITS = [
    "seconds",
    "minutes",
    "hours",
    "days"
]


"""
Get webpage HTML
"""
def get_webpage(url):
    headers = {
        'User-Agent': 'Ian Scott Knight',
        'From': 'ianscottknight@protonmail.com'
    }
    page = requests.get(url, headers=headers)
    if util.DEBUG:
        print(f"URL: {url}\n\tStatus code: {page.status_code}")
        if page.status_code == 200:
            return page
        else: 
            return None
    else:
        assert page.status_code == 200 # successfully retrieved 
        return page

def get_soup(url):
    page = get_webpage(url)
    soup = BeautifulSoup(page.content, "html.parser")
    return soup

def get_psychonaut_wiki_general_drug_soup(drug):
    url = f"https://psychonautwiki.org/wiki/{drug}"
    soup = get_soup(url)
    return soup

def get_psychonaut_wiki_summary_drug_soup(drug):
    url = f"https://psychonautwiki.org/wiki/{drug}/Summary"
    soup = get_soup(url)
    return soup


"""
Parse Psychonaut Wiki webpage HTML
"""
def get_unit_from_text(s, possible_units):
    if util.DEBUG: 
        print(f"\tText: {s}\n\tPossible units: {possible_units}")
    bools = [unit in s for unit in possible_units]
    assert any(bools) # check if all false
    assert bools.count(True) == 1 # check if more than one true
    index, = [i for i, x in enumerate(bools) if x]
    return possible_units[index]

def get_dosage_dict(dosechart):
    
    def get_dosage_level_href(level):
        assert level in DOSAGE_LEVELS
        return f"/wiki/Dosage_classification#{level.capitalize()}"

    dosage_levels_dict = {}
    for level in DOSAGE_LEVELS:
        dosage_level_tag = dosechart.parent.find(href=get_dosage_level_href(level))
        
        if not dosage_level_tag: continue # this particular level is not included
                    
        dosage_range_text = dosage_level_tag.parent.find_next_sibling(class_="RowValues").contents[0]
        try:
            quantities = re.findall(r"[-+]?\d*\.\d+|\d+", dosage_range_text)
            if len(quantities) == 2:
                low, high = quantities
            elif len(quantities) == 1:
                low, = quantities 
            elif len(quantities) == 0:
                continue
            unit = get_unit_from_text(dosage_range_text, DOSAGE_UNITS)
        except:
            try:
                low = high 
            except:
                continue
            
        dosage_levels_dict[level] = (float(low), unit)
        
    if len(dosage_levels_dict) == 1:
        level, = dosage_levels_dict.keys()
        next_level = DOSAGE_LEVELS[DOSAGE_LEVELS.index(level) + 1]
        dosage_levels_dict[next_level] = (float(high), unit)
        
    if util.DEBUG: 
        print(f"\tDosage levels: {dosage_levels_dict}")
        
    return dosage_levels_dict

def get_duration_dict(dosechart):
    
    def get_duration_type_href(duration_type):
        assert duration_type in DURATION_TYPES
        return f"/wiki/Duration#{duration_type.capitalize()}"
    
    duration_dict = {}
    for duration_type in DURATION_TYPES:
        duration_type_tag = dosechart.parent.find(href=get_duration_type_href(duration_type))
        
        if not duration_type_tag: continue # this particular duration type is not included
                        
        duration_type_text = duration_type_tag.parent.find_next_sibling(class_="RowValues").contents[0]
        quantities = re.findall(r"[-+]?\d*\.\d+|\d+", str(duration_type_text))
        if len(quantities) == 2:
            low, high = quantities
        elif len(quantities) == 1:
            low, = quantities 
            high = low
        unit = get_unit_from_text(duration_type_text, DURATION_UNITS)
            
        duration_dict[duration_type] = ((float(low), float(high)), unit)
    
    if util.DEBUG:
        print(f"\tDurations:{duration_dict}")
        
    return duration_dict

"""
Get dosechart info from Psychonaut Wiki 
"""

def get_drug_to_dosechart_info_dict():
    print("Getting drug dosechart info from Psychonaut Wiki...")
    drug_to_dosechart_info_dict = {}
    for drug in util.PSYCHEDELICS["psychonaut_wiki_id"]:
        print(f"\tDrug: {drug}")
        soup = get_psychonaut_wiki_general_drug_soup(drug)
        dosecharts = soup.find_all(class_="dosechart")
        dosechart_info_dict = {}
        for dosechart in dosecharts:
            roa = dosechart["data-roa"].lower()
            dosage_dict = get_dosage_dict(dosechart)
            duration_dict = get_duration_dict(dosechart)
            if len(dosage_dict) != 0 and len(duration_dict) != 0:
                dosechart_info_dict[roa] = {
                    "dosage": dosage_dict,
                    "duration": duration_dict
                }
        drug_to_dosechart_info_dict[drug] = dosechart_info_dict
        
    # LSA dosage is provided in seeds on psychonaut wiki, so we resort to chemist Albert Hofmann's conclusion 
    # that pure LSA is "about a tenfold to twentyfold greater dose than LSD" and multiply the dosage levels 
    # of LSD by 15.
    drug_to_dosechart_info_dict["LSA"] = {}
    drug_to_dosechart_info_dict["LSA"]["oral"] = {}

    soup = get_psychonaut_wiki_general_drug_soup("LSA")
    dosechart, = soup.find_all(class_="dosechart")
    drug_to_dosechart_info_dict["LSA"]["oral"]["duration"] = get_duration_dict(dosechart)

    drug_to_dosechart_info_dict["LSA"]["oral"]["dosage"] = drug_to_dosechart_info_dict["LSD"]["sublingual"]["dosage"].copy()
    for level in drug_to_dosechart_info_dict["LSA"]["oral"]["dosage"]:
        dose, unit = drug_to_dosechart_info_dict["LSA"]["oral"]["dosage"][level]
        drug_to_dosechart_info_dict["LSA"]["oral"]["dosage"][level] = (15.0 * dose, unit)
        
    return drug_to_dosechart_info_dict

"""
Get drug effects from Psychonaut Wiki 
"""
def get_drug_to_effects_dict():
    drug_to_effects_dict = {}

    effects_list_url = "https://psychonautwiki.org/wiki/List/effects"
    effects_list_page = get_webpage(effects_list_url)
    soup = BeautifulSoup(effects_list_page.content, "html.parser")

    effect_type_tags = soup.find_all(class_="panel-header")

    effect_type_refs = []
    effect_type_ref_to_effect_refs_dict = collections.defaultdict(list)
    effect_ref_to_effect_type_ref_dict = {}
    all_effect_refs = []

    print("Getting drug effect types from Psychonaut Wiki...")
    for effect_type_tag in effect_type_tags:
        effect_type_ref = effect_type_tag.find(class_="mw-headline")["id"]
        effect_type_refs.append(effect_type_ref)
        
        effects_wrapper_tags = effect_type_tag.parent.find_all(class_="featured list-item")

        effect_tags = []
        for effects_wrapper_tag in effects_wrapper_tags:
            effect_tags += effects_wrapper_tag.find_all("a")
            
        effect_refs = list(set([tag["href"] for tag in effect_tags]))
        all_effect_refs += effect_refs
        
        effect_type_ref_to_effect_refs_dict[effect_type_ref] = effect_refs
        
        for effect_ref in effect_refs:
            effect_ref_to_effect_type_ref_dict[effect_ref] = effect_type_ref

    all_effect_refs = list(set(all_effect_refs))

    print("Getting drug effects from Psychonaut Wiki...")
    for drug in util.PSYCHEDELICS["psychonaut_wiki_id"]:
        print(f"\tDrug: {drug}")
        soup = get_psychonaut_wiki_summary_drug_soup(drug)
        effects = []
        for effect_type_ref in effect_type_refs:
            effect_type_tag = soup.find_all(id=effect_type_ref)
            if len(effect_type_tag) == 0: continue
            effect_type_tag, = effect_type_tag

            hrefs = []
            for a in effect_type_tag.parent.parent.find_all("a"):
                try:
                    hrefs.append(a["href"])
                except:
                    pass
            
            effect_refs = list(set([ref for ref in hrefs if ref in all_effect_refs]))
            effects += [ref.replace("/wiki/", "").lower() for ref in effect_refs]
        drug_to_effects_dict[drug] = effects

    return drug_to_effects_dict


"""
Get trip reports from Erowid
"""
def get_erowid_trip_reports(drug):
    trip_reports = []
    
    # get general webpage
    url_general = "https://www.erowid.org/experiences/subs/exp_{}_General.shtml".format(drug)
    soup_general = get_soup(url_general)
    
    # get extended webpage showing all trip reports (default separated into batches of 100)
    drug_id = soup_general.find("input", {"name": "S"})["value"] # get drug_id from specific input tag of general page HTML
    MAXIMUM = 10000 # set this to a number greater than the number of trip reports and the webpage will appear with all trip reports 
    url_all_trip_reports = f"https://www.erowid.org/experiences/exp.cgi?S={drug_id}&C=1&ShowViews=0&Cellar=0&Start=0&Max={MAXIMUM}"
    soup_all_trip_reports = get_soup(url_all_trip_reports)
    
    for a in soup_all_trip_reports.find("tr", height="8").parent.find_all("a"):
        url_trip_report = f"https://www.erowid.org/{a['href']}"
        soup_trip_report = get_soup(url_trip_report)
        
        start = "<!-- Start Body -->"
        end = "<!-- End Body -->"
        
        # extract just the trip report from HTML
        s = str(soup_trip_report)
        s = s[s.find(start)+len(start):s.rfind(end)]
        trip_report = BeautifulSoup(s, "html.parser").text
        
        # remove escape sequences from text
        escapes = "".join([chr(char) for char in range(1, 32)])
        for escape in escapes:
            trip_report = trip_report.replace(escape, " ")
        
        if "concatemoji" in trip_report or "createElement" in trip_report: continue  # some outliers containing spam javascript
        
        trip_reports.append(trip_report)
        
    return trip_reports


def get_custom_stop_words():

    # a few names included were found to not bias their corresponding drug, so we make exceptions for them manually
    NAME_EXCEPTIONS = [
        "the light", 
        "colour", 
        "eternity", 
        "beautiful", 
        "aurora",
        "rosy"
    ]

    custom_stop_words = []
    for drug in util.PSYCHEDELICS["psychonaut_wiki_id"]:

        # retrieve text containing the various names of the given drug
        base_url = "https://psychonautwiki.org/wiki/"
        url = base_url + drug
        soup = get_soup(url)
        tag = soup.find("th", id="Nomenclature")
        names_text = tag.parent.find_next_sibling().find("td", {"class": "RowValues"}).text

        # remove quote marks
        names_text = names_text.replace("'", " ").replace('"', " ")

        # remove brackets and their contents
        brackets = re.findall(re.compile("\(.*?\)"), names_text)
        for b in brackets:
            names_text = names_text.replace(b, " ")

        # remove parentheses and their contents
        parens = re.findall(re.compile("\[.*?\]"), names_text)
        for p in parens:
            names_text = names_text.replace(p, " ")

        # get list of names from names text
        names = [name.lstrip().rstrip().lower() for name in names_text.split(",")]

        # remove exceptions
        names = [name for name in names if name not in NAME_EXCEPTIONS]

        # add versions of names with dashes removed 
        names += [name.replace("-", "") for name in names]

        # add to custom stop words
        custom_stop_words += names

    # add names in text files:
    custom_stop_words += [drug.lower().replace("_", " ") for drug in util.PSYCHEDELICS["psychonaut_wiki_id"]]
    custom_stop_words += [drug.lower().replace("_", " ") for drug in util.PSYCHEDELICS["erowid_id"]]

    # add all others, including methods of consumption, paraphernalia, measurements, and classes of drugs
    custom_stop_words += [
        "mushroom", "fungus", "fungi", "shroom", "cubensis", "cactus", "cacti", "san", "pedro", "peyote", \
        "divinorum", "mpt", "mde", "mdma", "mdmc", "mda", "mxe", "mdpv", "eth", "lad", "molly", \
        "ghb", "bufo", "alverius", "melatonin", "flunitrazepam", "alpraolam", "xanax", "woodrose", \
        "l-amphetamine", "hostilis", "diphenhydramine", "mdpr", "br-dfly", "clonazolam", "clonazepam", \
        "etizolam", "argyreia", "nervosa", "conocybe", "copelandia", "galerina", "gymnopilus", "inocybe", \
        "panaeolus", "pholiotina", "pluteus", "psilocybe", "serotonin", "serotonergic", "dopamine", \
        "dopaminergic", "norepinephrine", "adrenergic", "enpathogen", "empathogenic", "entactogen", \
        "entactogenic", "entheogen", "entheogenic", "tab", "pipe", "smoked", "swallowed", "dropped", \
        "insufflated", "insufflation", "vaporized", "bong", "bubbler", "hitter", "inhaled", "exhaled", \
        "inhaling", "exhaling", "oral", "orally", "sublingual", "sub-lingual", "intramuscular", "injected", \
        "injection", "gram", "g", "milligram", "mg", "microgram", "µg", "mcg", "microg", "mmhg", \
        "milliliter", "ml", "freebase", "fumarate", "indole", "substituted", "lysergic", "lysergamide", \
        "tryptamine", "phenethylamine", "phen", "phenthylamine", "dimethyltryptamine", "dox", "do-x", \
        "nbome", "salvinorin", "salvorin", "amphetamine", "dexedrine", "b", "c", "d", "e", "j", "m", "p", "t", \
        "peruvianus", "hydrobromide", "kappa", "opioid", "nasal", "nasally", "buccal", "buccally", "rectal", \
        "rectally", "pcp", "hydrochloride", "foxie", "insuflated", "intranasal", "tscpn", "toke", "ipracetyl", \
        "ketamine", "ket", "k", "snort", "snorting", "erowid", "gland", "brew", "tea", "pill", "capsule", \
        "inhale", "inhaling", "exhale", "exhaling", "r", "redose", "dose", "extract", "shrooming", "syrian", \
        "rue", "methylone", "comeup", "come-up", "glory", "seed", "xtc", "insufflate", "vapor", "vaporize", \
        "hcl", "caapi", "datura", "oxide", "harmala", "alkaloid", "cocaine", "coke", "meth", "cannabis", \
        "weed", "joint", "smoke", "sublingually", "sub-lingually", "lingual", "lingually", "come-down", \
        "comedown", "aluminum", "foil", "boil", "extracted", "extraction", "toke", "syringe", "inject", \
        "methamphetamine", "magnesium", "ssri", "marijuana", "amp", "tar", "nostril", "dropper", "codine", \
        "ayahuasca", "dxm", "mush", "mushie", "ug", "nose", "inhalation", "exhalation", "eighth", "truffle", \
        "harmaline", "spore", "gelcap", "memantine", "alprazolam", "aco", "meo", "drop", "research", "chemical", \
        "rc", "hit", "smoking", "swallow", "powder", "free-base", "salt", "eyeball", "eyeballed", "eyeballing", \
        "fume", "bromo", "lime", "juice", "ingest"
    ]

    # add versions of stop words with prefixes and suffixes
    additions = []
    for prefix in ["pre-", "mid-", "post-"]:
        additions += [prefix + w for w in custom_stop_words]
    for suffix in ["-like", "-type", "-esque"]:
        additions += [w + suffix for w in custom_stop_words]
    custom_stop_words += additions

    # add an -s suffix to all custom stop words to catch plurals
    custom_stop_words += [w + 's' for w in custom_stop_words]

    # reduce to unique elements
    custom_stop_words = list(set(custom_stop_words))

    return custom_stop_words


def main():
    # Erowid only permits up to 5000 requests per day, otherwise they ban your IP
    # So, we must split up scraping into two phases
    # Instructions: 
    # 1. Set the variable PHASE to 1 for the first day / IP and then run scrape.py
    # 2. Wait 24 hours or switch to another IP
    # 3. Set PHASE to 2 and then run scrape.py

    assert PHASE == 1 or PHASE == 2

    if PHASE == 1:

        # Scrape drug dosechart info from Psychonaut Wiki
        drug_to_dosechart_info_dict = get_drug_to_dosechart_info_dict()

        # Save drug dosechart info
        with open(util.DRUG_TO_DOSECHART_INFO_DICT_FILE, "wb") as f:
            pickle.dump(drug_to_dosechart_info_dict, f)

        # Scrape drug effects from Psychonaut Wiki
        drug_to_effects_dict = get_drug_to_effects_dict()

        # Save drug effects
        with open(util.DRUG_TO_EFFECTS_DICT_FILE, "wb") as f:
            pickle.dump(drug_to_effects_dict, f)

        erowid_drugs_to_scrape = util.PSYCHEDELICS["erowid_id"][:24]

        # Scrape custom stop words (words pertaining to specific drugs) for later use
        custom_stop_words = get_custom_stop_words()

        # Save custom stop words
        with open(util.CUSTOM_STOP_WORDS_FILE, "wb") as f:
            pickle.dump(custom_stop_words, f)


    else:
        erowid_drugs_to_scrape = util.PSYCHEDELICS["erowid_id"][24:]
    

    # Scrape trip reports from Erowid
    drug_to_trip_reports_dict = {}
    for drug in erowid_drugs_to_scrape:    
        print(f"Collecting trip reports for {drug}...")
        drug_to_trip_reports_dict[drug] = get_erowid_trip_reports(drug)
        print(f"\tCollected {len(drug_to_trip_reports_dict[drug])} trip reports\n")
    drug_to_trip_reports_count_dict = {key : len(values) for key, values in drug_to_trip_reports_dict.items()}
    drug_to_trip_reports_count_dict = dict(sorted(drug_to_trip_reports_count_dict.items(), key=lambda x: x[1]))
    print(f"Total number of trip reports collected: {sum(drug_to_trip_reports_count_dict.values())}")

    # Remove non-English trip reports
    print("Removing non-English trip reports...")
    non_english_count = 0
    for drug, trip_reports in drug_to_trip_reports_dict.items():
        print(f"\t\tChecking {drug}...")
        trip_reports_english = trip_reports.copy()
        for trip_report in trip_reports:
            lang = langdetect.detect(trip_report)
            if lang != "en":
                print(f"\tDetected language: {lang}")
                trip_reports_english.remove(trip_report)
                non_english_count += 1
        drug_to_trip_reports_dict[drug] = trip_reports_english 
    print(f"Removed {non_english_count} trip reports not written in English")

    # Save trip reports
    print("Saving trip reports...")
    csv_columns = ["drug", "trip_report"]
    csv_file_phase_1 = util.TRIP_REPORTS_FILE.replace(".csv", "_phase_1.csv")
    csv_file_phase_2 = util.TRIP_REPORTS_FILE.replace(".csv", "_phase_2.csv")
    if PHASE == 1:
        with open(csv_file_phase_1, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns)
            writer.writeheader()
            for drug, trip_reports in drug_to_trip_reports_dict.items():
                for trip_report in trip_reports:
                    writer.writerow({
                        csv_columns[0]: drug, 
                        csv_columns[1]: trip_report
                    })
    else:
        with open(csv_file_phase_2, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns)
            writer.writeheader()
            for drug, trip_reports in drug_to_trip_reports_dict.items():
                for trip_report in trip_reports:
                    writer.writerow({
                        csv_columns[0]: drug, 
                        csv_columns[1]: trip_report
                    })

        # merge CSV files from both phases
        trip_reports_phase_1 = pd.read_csv(csv_file_phase_1)
        trip_reports_phase_2 = pd.read_csv(csv_file_phase_2)
        trip_reports_merged = pd.concat([trip_reports_phase_1, trip_reports_phase_2]) 
        trip_reports_merged.to_csv(util.TRIP_REPORTS_FILE, index=False)


if __name__ == "__main__":
    main()