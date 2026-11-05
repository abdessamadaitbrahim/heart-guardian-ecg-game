"""Feature extraction from RR intervals for the XGBoost classifier."""

import numpy as np

DISEASE_CODES = {
    "aucune": 0,
    "asthme": 1,
    "diabete": 2,
    "hypertension": 3,
    "arythmie": 4,
    "autre": 5,
}

FEATURE_NAMES = [
    "bpm", "rr_mean", "rr_std", "rr_min", "rr_max",
    "hrv", "irregularity", "age", "disease",
]


class FeatureExtractor:
    def extract(self, rr_intervals, age, disease):
        """Return a feature dict, or None if there are too few intervals."""
        if len(rr_intervals) < 2:
            return None

        rr_mean = float(np.mean(rr_intervals))
        rr_std = float(np.std(rr_intervals))
        return {
            "bpm": int(60 / rr_mean),
            "rr_mean": round(rr_mean, 4),
            "rr_std": round(rr_std, 4),
            "rr_min": round(float(np.min(rr_intervals)), 4),
            "rr_max": round(float(np.max(rr_intervals)), 4),
            "hrv": round(float(np.sqrt(np.mean(np.diff(rr_intervals) ** 2))), 4),
            "irregularity": round(rr_std / rr_mean if rr_mean > 0 else 0, 4),
            "age": age,
            "disease": DISEASE_CODES.get(str(disease).lower(), 0),
        }

    @staticmethod
    def to_list(features):
        return [features[name] for name in FEATURE_NAMES]
