"""Real-time ECG analysis: R peaks, features, XGBoost class, profile rules."""

import pickle

import numpy as np

import config
from feature_extractor import FeatureExtractor
from pan_tompkins import PanTompkins

# class -> (label, alert, game action). Values are consumed by the Unity game.
CLASSES = {
    0: ("Normal", False, "continuer_normal"),
    1: ("Bradycardie", True, "ralentir_jeu"),
    2: ("Tachycardie", True, "pause_respiration"),
    3: ("Danger", True, "mode_securise"),
}


class EcgModel:
    def __init__(self, fs=config.SAMPLE_RATE_HZ):
        self.peaks = PanTompkins(fs=fs)
        self.features = FeatureExtractor()
        self.model = self._load()

    @staticmethod
    def _load():
        try:
            with open(config.MODEL_PATH, "rb") as f:
                model = pickle.load(f)
            print("XGBoost model loaded")
            return model
        except OSError:
            print(f"Model not found at {config.MODEL_PATH}. Run python/train.py first.")
            return None

    @property
    def ready(self):
        return self.model is not None

    def analyze(self, signal, age, disease):
        """Return the full result dict for the game and the database, or None."""
        if self.model is None:
            return None
        signal = np.asarray(list(signal), dtype=float)
        if len(signal) < 50:
            return None

        rr = self.peaks.rr_intervals(self.peaks.detect_peaks(signal))
        features = self.features.extract(rr, age, disease)
        if features is None:
            return None

        x = np.array(self.features.to_list(features)).reshape(1, -1)
        cls = int(self.model.predict(x)[0])
        confidence = round(float(np.max(self.model.predict_proba(x)[0])) * 100, 1)
        cls = self._adapt_to_profile(
            cls, features["bpm"], age, disease, features["irregularity"]
        )
        return self._build_result(cls, confidence, features)

    @staticmethod
    def _adapt_to_profile(cls, bpm, age, disease, irregularity):
        """Adjust the class with age-dependent and condition-dependent thresholds."""
        if age <= 10:
            if bpm > 130:
                cls = 3
            if bpm < 60:
                cls = 1
        elif age <= 15:
            if bpm > 120:
                cls = 2
            if bpm < 55:
                cls = 1
        elif age <= 50:
            if bpm > 110:
                cls = 2
            if bpm < 50:
                cls = 1
        else:
            if bpm > 100:
                cls = 2
            if bpm < 45:
                cls = 1

        disease = str(disease).lower()
        if disease == "hypertension" and bpm > 100:
            cls = max(cls, 2)
        elif disease == "asthme" and bpm > 110:
            cls = max(cls, 2)
        elif disease == "arythmie" and irregularity > 0.15:
            cls = max(cls, 3)
        elif disease == "diabete" and irregularity > 0.20:
            cls = max(cls, 2)
        return cls

    @staticmethod
    def _build_result(cls, confidence, features):
        label, alert, action = CLASSES[cls]
        bpm = features["bpm"]
        messages = {
            "Normal": f"Rythme normal a {bpm} BPM",
            "Bradycardie": f"Rythme lent a {bpm} BPM, repose-toi",
            "Tachycardie": f"Rythme eleve a {bpm} BPM, respire",
            "Danger": f"Rythme anormal a {bpm} BPM, pause",
        }
        return {
            "bpm": bpm,
            "hrv": features["hrv"],
            "rr_moyen": features["rr_mean"],
            "irregularite": features["irregularity"],
            "classe": cls,
            "label": label,
            "confiance": confidence,
            "alerte": alert,
            "action_jeu": action,
            "message": messages[label],
        }
