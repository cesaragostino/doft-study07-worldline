"""Historia causal — PHYSICS_CONTRACT §5 (transcripción de differential_engine.py:141-168)."""
from __future__ import annotations

import math

import numpy as np


class HistoryBuffer:
    """Ring de tamaño delay_steps+1; inicializado COMPLETO con el valor t=0; push avanza head.
    La historia inicial es parte del checkpoint (CHECKPOINT_SCHEMA)."""

    def __init__(self, delay_steps: int, initial: np.ndarray) -> None:
        if delay_steps < 0:
            raise ValueError("delay_steps must be >= 0")
        self.delay_steps = int(delay_steps)
        self.size = self.delay_steps + 1
        initial = np.asarray(initial, dtype=float)
        self.buffer = np.zeros((self.size,) + initial.shape, dtype=float)
        self.head_idx = 0
        for idx in range(self.size):
            self.buffer[idx] = initial

    def push(self, value: np.ndarray) -> None:
        self.head_idx = (self.head_idx + 1) % self.size
        self.buffer[self.head_idx] = value

    def get_delayed_steps(self, steps_ago: float) -> np.ndarray:
        """Interpolación LINEAL hacia atrás: base=floor, frac entre (head−base) y (head−base−1)."""
        if self.size == 1 or steps_ago <= 0.0:
            return self.buffer[self.head_idx].copy()
        base = int(math.floor(steps_ago))
        frac = steps_ago - base
        idx0 = (self.head_idx - base) % self.size
        if frac <= 0.0:
            return self.buffer[idx0].copy()
        idx1 = (idx0 - 1) % self.size
        return (1.0 - frac) * self.buffer[idx0] + frac * self.buffer[idx1]
