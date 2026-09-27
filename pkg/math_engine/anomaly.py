"""Minimal anomaly detection module."""

class RollingStatistics:
    def __init__(self, window_size: int):
        self.window_size = window_size
        self.values = []

    def update(self, value: float):
        self.values.append(value)
        if len(self.values) > self.window_size:
            self.values.pop(0)
        return 0.0  # Dummy z-score
