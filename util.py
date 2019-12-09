

import collections
import csv
import pickle


"""
Constants
"""
DEBUG = False 

DIR = "."
DATA_DIR = f"{DIR}/data"

PSYCHEDELICS_FILE = f"{DATA_DIR}/psychedelics.csv"

def read_psychedelics_file():
    psychedelics = collections.defaultdict(list)
    with open(PSYCHEDELICS_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key, value in row.items():
                psychedelics[key].append(value)
    return psychedelics

def unpickle(filepath):
    with open(filepath, "rb") as f:
        obj = pickle.load(f)
    return obj

PSYCHEDELICS = read_psychedelics_file()

DRUG_TO_DOSECHART_INFO_DICT_FILE = f"{DATA_DIR}/drug_to_dosechart_info_dict.pickle"
DRUG_TO_EFFECTS_DICT_FILE = f"{DATA_DIR}/drug_to_effects_dict.pickle"

TRIP_REPORTS_FILE = f"{DATA_DIR}/trip_reports.csv"

CUSTOM_STOP_WORDS_FILE = f"{DATA_DIR}/custom_stop_words.txt"

TRIP_REPORTS_DATAFRAME_FILE = f"{DATA_DIR}/trip_reports_dataframe.pickle"

DOC2VEC_MODEL_DBOW_FILE = f"{DATA_DIR}/doc2vec_model_dbow.pickle"
DOC2VEC_MODEL_DM_FILE = f"{DATA_DIR}/doc2vec_model_dm.pickle"

DOC2VEC_HYPERPARAMETERS_DBOW_FILE = f"{DATA_DIR}/doc2vec_hyperparameters_dbow.pickle"
DOC2VEC_HYPERPARAMETERS_DM_FILE = f"{DATA_DIR}/doc2vec_hyperparameters_dm.pickle"

CLASSIFIER_FILE = f"{DATA_DIR}/classifier.pickle"







