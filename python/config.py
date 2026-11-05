"""Shared settings for the Heart Guardian backend."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MITBIH_DIR = DATA_DIR / "mitbih"
MODEL_PATH = DATA_DIR / "model" / "xgboost_ecg.pkl"
DB_PATH = DATA_DIR / "heartguardian.db"

HOST = os.getenv("HG_HOST", "0.0.0.0")
PORT_ESP32 = int(os.getenv("HG_PORT_ESP32", "5000"))
PORT_UNITY = int(os.getenv("HG_PORT_UNITY", "6000"))

SAMPLE_RATE_HZ = 100            # ESP32 sampling rate
WINDOW_SECONDS = 10             # signal window analysed (matches training)
ANALYSIS_EVERY_SECONDS = 1      # how often a new analysis is produced
MIN_VALID_SAMPLE = 100          # raw ADC values below this are ignored

DEFAULT_PROFILE = {"nom": "Joueur", "age": 25, "maladie": "aucune"}
