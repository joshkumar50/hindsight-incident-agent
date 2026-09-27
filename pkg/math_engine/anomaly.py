"""
Mathematical Anomaly Engine Library
Implements stateful pure math functions (Rolling Z-Score, EWMA) for detecting anomalies without LLMs.
"""

import math
from typing import List, Optional


class RollingStatistics:
    """Maintains a rolling window for mean, standard deviation, and Z-Score."""

    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.values: List[float] = []

    def update(self, value: float) -> Optional[float]:
        """
        Updates the window and returns the current Z-Score of the inserted value.
        Returns None if the window is not yet full enough to be statistically significant (e.g. < 3 points).
        """
        self.values.append(value)
        if len(self.values) > self.window_size:
            self.values.pop(0)

        if len(self.values) < 3:
            return None

        mean = sum(self.values) / len(self.values)
        variance = sum((x - mean) ** 2 for x in self.values) / (len(self.values) - 1)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        return (value - mean) / std_dev


class EWMATracker:
    """Exponentially Weighted Moving Average tracker."""

    def __init__(self, alpha: float = 0.2):
        self.alpha = alpha
        self.current_ewma: Optional[float] = None

    def update(self, value: float) -> float:
        if self.current_ewma is None:
            self.current_ewma = value
        else:
            self.current_ewma = (self.alpha * value) + (
                (1 - self.alpha) * self.current_ewma
            )
        return self.current_ewma
