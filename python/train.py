"""Train the XGBoost rhythm classifier on the MIT-BIH Arrhythmia Database.

Records are downloaded from PhysioNet. Each 10 s segment is normalised to the
ESP32 ADC range (0-4095), processed with Pan-Tompkins and labelled from its BPM
and RR irregularity (the MIT-BIH beat annotations are not used).
"""

import pickle

import numpy as np
import pandas as pd
import wfdb
import xgboost as xgb
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

import config
from feature_extractor import FEATURE_NAMES, FeatureExtractor
from pan_tompkins import PanTompkins

RECORDS = [
    "100", "101", "102", "103", "104", "105", "106", "107", "108", "109",
    "111", "112", "113", "114", "115", "116", "117", "118", "119", "121",
    "122", "123", "124", "200", "201", "202", "203", "205", "207", "208",
    "209", "210", "212", "213", "214", "215", "217", "219", "220", "221",
    "222", "223", "228", "230", "231", "232", "233", "234",
]
MITBIH_FS = 360
SEGMENT_SECONDS = 10


def label_from_features(features):
    """0 normal, 1 bradycardia, 2 tachycardia, 3 danger / arrhythmia."""
    bpm = features["bpm"]
    if features["irregularity"] > 0.2 or bpm < 40 or bpm > 150:
        return 3
    if bpm < 60:
        return 1
    if bpm <= 100:
        return 0
    return 2


def build_dataset():
    pan = PanTompkins(fs=MITBIH_FS)
    extractor = FeatureExtractor()
    rows = []
    segment_size = MITBIH_FS * SEGMENT_SECONDS

    for record_name in RECORDS:
        try:
            print(f"Processing record {record_name}")
            record = wfdb.rdrecord(record_name, pn_dir="mitdb")
            signal = record.p_signal[:, 0]

            for start in range(0, len(signal) - segment_size, segment_size):
                segment = signal[start:start + segment_size]
                segment = segment - np.min(segment)
                if np.max(segment) > 0:
                    segment = segment / np.max(segment) * 4095

                rr = pan.rr_intervals(pan.detect_peaks(segment))
                features = extractor.extract(rr, age=30, disease="aucune")
                if features is None:
                    continue
                rows.append(extractor.to_list(features) + [label_from_features(features)])
        except Exception as error:
            print(f"Skipping record {record_name}: {error}")

    return pd.DataFrame(rows, columns=FEATURE_NAMES + ["class"])


def main():
    config.MITBIH_DIR.mkdir(parents=True, exist_ok=True)
    df = build_dataset()
    print(f"\n{len(df)} segments extracted")
    print(df["class"].value_counts().sort_index())

    X = df.drop("class", axis=1).values
    y = df["class"].values
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric="mlogloss", random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    y_pred = model.predict(X_test)
    names = ["Normal", "Bradycardie", "Tachycardie", "Danger"]
    present = sorted(set(y_test) | set(y_pred))
    print(classification_report(
        y_test, y_pred, labels=present, target_names=[names[i] for i in present]
    ))
    print(confusion_matrix(y_test, y_pred))

    config.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(config.MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    print(f"Model saved to {config.MODEL_PATH}")


if __name__ == "__main__":
    main()
