import collections
import copy
import csv
import pickle
import operator
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report, precision_recall_fscore_support
import matplotlib.pyplot as plt
import seaborn as sns


"""
Constants
"""
DEBUG = False 

DATA_DIR = "data"
PSYCHEDELICS_FILE = f"{DATA_DIR}/psychedelics.csv"

DRUG_TO_DOSECHART_INFO_DICT_FILE = f"{DATA_DIR}/drug_to_dosechart_info_dict.pickle"
DRUG_TO_EFFECTS_DICT_FILE = f"{DATA_DIR}/drug_to_effects_dict.pickle"

TRIP_REPORTS_FILE = f"{DATA_DIR}/trip_reports.csv"

CUSTOM_STOP_WORDS_FILE = f"{DATA_DIR}/custom_stop_words.txt"

TRIP_REPORTS_DATAFRAME_FILE = f"{DATA_DIR}/trip_reports_dataframe.pickle"

DOC2VEC_MODEL_DBOW_FILE = f"{DATA_DIR}/doc2vec_model_dbow.pickle"
DOC2VEC_MODEL_DM_FILE = f"{DATA_DIR}/doc2vec_model_dm.pickle"

DOC2VEC_HYPERPARAMETERS_DBOW_FILE = f"{DATA_DIR}/doc2vec_hyperparameters_dbow.pickle"
DOC2VEC_HYPERPARAMETERS_DM_FILE = f"{DATA_DIR}/doc2vec_hyperparameters_dm.pickle"

CLASSIFIER_MODEL_FILE = f"{DATA_DIR}/classifier_model.pickle"
CLASSIFIER_HYPERPARAMETERS_FILE = f"{DATA_DIR}/classifier_hyperparameters.pickle"

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

# test given classifier on test set
def test_classifier(clf, X_test, y_test, labels, top_n=3, show_top_n_accuracy=False, show_confusion_matrix=False):
    y_pred = clf.predict(X_test)
    precision, recall, f_score, support = precision_recall_fscore_support(y_test, y_pred, labels=labels, average=None)
    report = pd.DataFrame({
        "class": labels,
        "precision": precision,
        "recall": recall,
        "f_score": f_score,
        "support": support
    })
    
    if show_top_n_accuracy:
        y_hat = clf.predict_proba(X_test)
        classes = clf.classes_
        y_pred_sorted = []
        y_hat_sorted = []
        num_correct = 0
        for i, probs in enumerate(y_hat):
            probs_sorted, classes_sorted = (list(l) for l in zip(*sorted(zip(probs, classes), key=operator.itemgetter(0), reverse=True)))
            true_class = y_test.iloc[i]
            top_classes = classes_sorted[:top_n]
            y_pred_sorted.append(classes_sorted)
            y_hat_sorted.append(probs_sorted)
            if true_class in top_classes:
                num_correct += 1
        top_n_acc = num_correct / len(y_pred)
        print(f"Top-{top_n} accuracy: {top_n_acc}")
    
    if show_confusion_matrix:
        cm = confusion_matrix(y_test, y_pred)
        new_cm = []
        for row in cm:
            support = sum(row)
            new_row = row / support
            new_cm.append(new_row)
        cm = new_cm

        df_cm = pd.DataFrame(cm, index=labels, columns=labels)
        plt.figure(figsize=(20,20))
        ax = sns.heatmap(df_cm, annot=False, linewidth=0.05)
        bottom, top = ax.get_ylim()
        ax.set_ylim(bottom + 0.5, top - 0.5)
        
    return report

# train and test using all data with k-fold
def train_and_test_classifier_k_fold(X, y, clf_untrained, k_fold=10):
    results = []
    skf = StratifiedKFold(n_splits=k_fold)
    train_test_split_indices = skf.split(X, y)
        
    for train_indices, test_indices in train_test_split_indices:
        clf = copy.deepcopy(clf_untrained)

        X_train, X_test = X[train_indices], X[test_indices]
        y_train, y_test = y[train_indices], y[test_indices]
        
        clf.fit(X_train, y_train)
        
        labels = np.unique(y_train)
        report = test_classifier(clf, X_test, y_test, labels)
        f_score_avg = np.mean(report["f_score"])
        
        results.append((report, f_score_avg))
        
    return results



