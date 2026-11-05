"""Pan-Tompkins style R-peak detection and RR interval computation."""

import numpy as np
from scipy.signal import butter, filtfilt


class PanTompkins:
    def __init__(self, fs=100):
        self.fs = fs

    def _low_pass(self, signal):
        b, a = butter(2, 15.0 / (self.fs / 2), btype="low")
        return filtfilt(b, a, signal)

    def _high_pass(self, signal):
        b, a = butter(2, 5.0 / (self.fs / 2), btype="high")
        return filtfilt(b, a, signal)

    @staticmethod
    def _derivative(signal):
        return np.diff(signal, prepend=signal[0])

    @staticmethod
    def _integrate(signal, window=15):
        return np.convolve(signal, np.ones(window) / window, mode="same")

    def detect_peaks(self, signal):
        """Return the sample indices of the R peaks."""
        signal = np.asarray(signal, dtype=float)
        if len(signal) < 30:
            return np.array([], dtype=int)

        filtered = self._high_pass(self._low_pass(signal))
        energy = self._integrate(self._derivative(filtered) ** 2)
        threshold = 0.40 * np.max(energy)

        peaks = []
        in_peak = False
        start = 0
        for i, value in enumerate(energy):
            if value > threshold and not in_peak:
                in_peak = True
                start = i
            elif value <= threshold and in_peak:
                in_peak = False
                zone = signal[start:i]
                if len(zone) > 0:
                    peaks.append(start + int(np.argmax(zone)))

        min_distance = int(0.3 * self.fs)
        kept = []
        last = -min_distance
        for peak in peaks:
            if peak - last >= min_distance:
                kept.append(peak)
                last = peak
        return np.array(kept, dtype=int)

    def rr_intervals(self, peaks):
        """RR intervals in seconds, keeping only physiological values."""
        if len(peaks) < 2:
            return np.array([])
        rr = np.diff(peaks) / self.fs
        return rr[(rr > 0.3) & (rr < 2.0)]
