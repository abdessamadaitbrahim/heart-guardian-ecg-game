"""Fake ESP32: streams a synthetic ECG to the pipeline at 100 Hz.

Usage: python tools/ecg_emulator.py [bpm] [host] [port]
"""

import socket
import sys
import time

import numpy as np

FS = 100


def ecg_sample(t, bpm, rng):
    """Baseline + P/QRS/T waves repeated every 60/bpm seconds, in ADC units."""
    period = 60.0 / bpm
    phase = (t % period) / period
    qrs = np.exp(-((phase - 0.30) ** 2) / (2 * 0.008 ** 2))
    p_wave = 0.12 * np.exp(-((phase - 0.18) ** 2) / (2 * 0.02 ** 2))
    t_wave = 0.25 * np.exp(-((phase - 0.55) ** 2) / (2 * 0.04 ** 2))
    value = 2000 + 1500 * (qrs + p_wave + t_wave) + rng.normal(0, 15)
    return int(min(max(value, 150), 4095))


def main():
    bpm = float(sys.argv[1]) if len(sys.argv) > 1 else 75
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 5000

    rng = np.random.default_rng(0)
    sock = socket.create_connection((host, port))
    print(f"Streaming {bpm:.0f} BPM to {host}:{port}")
    start = time.time()
    n = 0
    try:
        while True:
            sock.sendall(f"ECG:{ecg_sample(n / FS, bpm, rng)}\n".encode())
            n += 1
            time.sleep(max(0, start + n / FS - time.time()))
    except (KeyboardInterrupt, BrokenPipeError, ConnectionResetError):
        print("Stopped")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
