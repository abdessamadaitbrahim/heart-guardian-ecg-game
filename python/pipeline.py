"""Heart Guardian pipeline: ESP32 ECG stream -> AI analysis -> Unity game.

The ESP32 connects to PORT_ESP32 and sends lines "ECG:<value>" (and
"DECONNECTE" when the electrodes are off). The Unity game connects to
PORT_UNITY, optionally sends a JSON profile, and receives one JSON line per
analysis.
"""

import json
import socket
import threading
from collections import deque

import config
from ai_model import EcgModel
from database import Database


class Pipeline:
    def __init__(self):
        self.db = Database()
        self.model = EcgModel()
        self.window = deque(maxlen=config.SAMPLE_RATE_HZ * config.WINDOW_SECONDS)
        self.step = config.SAMPLE_RATE_HZ * config.ANALYSIS_EVERY_SECONDS

        self.profile = dict(config.DEFAULT_PROFILE)
        self.bpms = []
        self.alert_count = 0

        self.unity = None
        self.unity_lock = threading.Lock()
        self.lock = threading.RLock()
        self.stop = threading.Event()

        player_id = self.db.add_player(
            self.profile["nom"], self.profile["age"], self.profile["maladie"]
        )
        self.session_id = self.db.start_session(player_id)
        print(f"Default session created: #{self.session_id}")

    # --- Unity side ---------------------------------------------------

    def send_unity(self, payload):
        with self.unity_lock:
            if self.unity is None:
                return
            try:
                self.unity.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            except OSError:
                self.unity = None

    def handle_unity_message(self, line):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            print(f"Ignoring invalid Unity message: {line!r}")
            return
        if data.get("type") != "profil":
            return

        try:
            profile = {
                "nom": str(data["nom"]),
                "age": int(data["age"]),
                "maladie": str(data["maladie"]),
            }
        except (KeyError, ValueError, TypeError):
            print(f"Incomplete profile ignored: {data}")
            return

        with self.lock:
            self.finish_session("profil_change")
            self.profile = profile
            player_id = self.db.add_player(
                profile["nom"], profile["age"], profile["maladie"]
            )
            self.session_id = self.db.start_session(player_id)
            self.window.clear()
        print(f"Profile received: {profile} (session #{self.session_id})")
        self.send_unity({
            "type": "profil_confirme",
            "session_id": self.session_id,
            "message": "Profil enregistre",
        })

    def unity_loop(self, server):
        while not self.stop.is_set():
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            print("Unity connected")
            with self.unity_lock:
                self.unity = conn
            conn.settimeout(1.0)
            buffer = ""
            while not self.stop.is_set():
                try:
                    chunk = conn.recv(1024)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="ignore")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip():
                        self.handle_unity_message(line.strip())
            with self.unity_lock:
                self.unity = None
            print("Unity disconnected")

    # --- ESP32 side ---------------------------------------------------

    def handle_line(self, line, state):
        if line == "DECONNECTE":
            print("Electrodes disconnected")
            self.send_unity({
                "type": "alerte", "bpm": 0, "label": "Deconnecte", "alerte": True,
                "action_jeu": "mode_securise", "confiance": 0,
                "message": "Electrodes deconnectees",
            })
            return
        if not line.startswith("ECG:"):
            return
        try:
            value = int(line.split(":", 1)[1].strip())
        except ValueError:
            return
        if value < config.MIN_VALID_SAMPLE:
            return

        self.window.append(value)
        state["since_last"] += 1
        if len(self.window) < self.window.maxlen or state["since_last"] < self.step:
            return
        state["since_last"] = 0

        with self.lock:
            result = self.model.analyze(
                self.window, self.profile["age"], self.profile["maladie"]
            )
            if result is None:
                return

            state["count"] += 1
            result["type"] = "ecg_resultat"
            self.bpms.append(result["bpm"])
            print(f"[{state['count']}] BPM {result['bpm']} | {result['label']} | "
                  f"{result['confiance']}%")

            self.db.save_result(self.session_id, value, result)
            if result["alerte"]:
                self.alert_count += 1
                self.db.save_alert(self.session_id, result)
        self.send_unity(result)

    def esp32_loop(self, server):
        state = {"since_last": 0, "count": 0}
        while not self.stop.is_set():
            try:
                conn, addr = server.accept()
            except socket.timeout:
                continue
            print(f"ESP32 connected: {addr}")
            conn.settimeout(1.0)
            buffer = ""
            while not self.stop.is_set():
                try:
                    chunk = conn.recv(1024)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="ignore")
                *lines, buffer = buffer.split("\n")
                for line in lines:
                    self.handle_line(line.strip(), state)
            conn.close()
            self.window.clear()
            print("ESP32 disconnected, waiting for reconnection")

    # --- lifecycle ----------------------------------------------------

    def finish_session(self, final_state):
        if self.bpms:
            self.db.end_session(self.session_id, {
                "bpm_avg": round(sum(self.bpms) / len(self.bpms)),
                "bpm_min": min(self.bpms),
                "bpm_max": max(self.bpms),
                "final_state": final_state,
                "alert_count": self.alert_count,
            })
            print(f"Session summary: avg {round(sum(self.bpms) / len(self.bpms))} BPM, "
                  f"min {min(self.bpms)}, max {max(self.bpms)}, alerts {self.alert_count}")
        self.bpms = []
        self.alert_count = 0

    @staticmethod
    def _listen(port):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((config.HOST, port))
        server.listen(1)
        server.settimeout(1.0)
        return server

    def run(self):
        print("Heart Guardian pipeline started")
        print(f"Profile: {self.profile['nom']}, {self.profile['age']} years, "
              f"{self.profile['maladie']}")
        if not self.model.ready:
            print("Warning: no trained model, results will not be produced")

        unity_server = self._listen(config.PORT_UNITY)
        esp_server = self._listen(config.PORT_ESP32)
        print(f"Waiting for Unity on port {config.PORT_UNITY}")
        print(f"Waiting for ESP32 on port {config.PORT_ESP32}")

        threading.Thread(target=self.unity_loop, args=(unity_server,), daemon=True).start()
        try:
            self.esp32_loop(esp_server)
        except KeyboardInterrupt:
            print("\nStopping")
        finally:
            self.stop.set()
            self.finish_session("termine")
            self.db.close()
            unity_server.close()
            esp_server.close()


if __name__ == "__main__":
    Pipeline().run()
