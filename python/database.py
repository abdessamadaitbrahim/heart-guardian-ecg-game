"""SQLite storage for players, sessions, ECG results and alerts."""

import sqlite3
from datetime import datetime

import config


def _now():
    return datetime.now().isoformat()


class Database:
    def __init__(self, path=config.DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                condition TEXT DEFAULT 'aucune',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER REFERENCES players(id),
                started_at TEXT, ended_at TEXT,
                bpm_avg REAL, bpm_min INTEGER, bpm_max INTEGER,
                final_state TEXT, alert_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS ecg_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id),
                timestamp TEXT, raw_value INTEGER, bpm INTEGER,
                class_id INTEGER, label TEXT, confidence REAL, hrv REAL
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id),
                timestamp TEXT, alert_type TEXT, bpm INTEGER, action TEXT
            );
            """
        )
        self.conn.commit()

    def add_player(self, name, age, condition="aucune"):
        cur = self.conn.execute(
            "INSERT INTO players (name, age, condition, created_at) VALUES (?, ?, ?, ?)",
            (name, age, condition, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def start_session(self, player_id):
        cur = self.conn.execute(
            "INSERT INTO sessions (player_id, started_at) VALUES (?, ?)",
            (player_id, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def save_result(self, session_id, raw_value, result):
        self.conn.execute(
            "INSERT INTO ecg_results (session_id, timestamp, raw_value, bpm, class_id,"
            " label, confidence, hrv) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, _now(), raw_value, result["bpm"], result["classe"],
             result["label"], result["confiance"], result["hrv"]),
        )
        self.conn.commit()

    def save_alert(self, session_id, result):
        self.conn.execute(
            "INSERT INTO alerts (session_id, timestamp, alert_type, bpm, action)"
            " VALUES (?, ?, ?, ?, ?)",
            (session_id, _now(), result["label"], result["bpm"], result["action_jeu"]),
        )
        self.conn.commit()

    def end_session(self, session_id, stats):
        self.conn.execute(
            "UPDATE sessions SET ended_at=?, bpm_avg=?, bpm_min=?, bpm_max=?,"
            " final_state=?, alert_count=? WHERE id=?",
            (_now(), stats["bpm_avg"], stats["bpm_min"], stats["bpm_max"],
             stats["final_state"], stats["alert_count"], session_id),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
