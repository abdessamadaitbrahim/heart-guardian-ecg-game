"""Fake backend for Unity: serves cycling ECG results on port 6000.

Use it to test the game without the ESP32 or the AI pipeline.
"""

import json
import socket
import time

HOST = "0.0.0.0"
PORT = 6000

STATES = [
    {"bpm": 75, "label": "Normal", "alerte": False, "action_jeu": "continuer_normal",
     "confiance": 95.0, "message": "Rythme normal"},
    {"bpm": 110, "label": "Tachycardie", "alerte": True, "action_jeu": "pause_respiration",
     "confiance": 91.0, "message": "Rythme eleve"},
    {"bpm": 45, "label": "Bradycardie", "alerte": True, "action_jeu": "ralentir_jeu",
     "confiance": 89.0, "message": "Rythme lent"},
    {"bpm": 160, "label": "Danger", "alerte": True, "action_jeu": "mode_securise",
     "confiance": 88.0, "message": "Rythme anormal"},
]


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    print(f"Waiting for Unity on port {PORT}")
    conn, addr = server.accept()
    print(f"Unity connected: {addr}")

    index = 0
    try:
        while True:
            state = {"type": "ecg_resultat", **STATES[index % len(STATES)]}
            conn.sendall((json.dumps(state) + "\n").encode("utf-8"))
            print(f"Sent: {state['bpm']} BPM | {state['label']}")
            index += 1
            time.sleep(3)
    except (KeyboardInterrupt, OSError) as error:
        print(f"Stopped: {error}")
    finally:
        conn.close()
        server.close()


if __name__ == "__main__":
    main()
