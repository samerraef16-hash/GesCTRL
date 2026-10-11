"""One Euro filter (Casiez et al.) driven by explicit timestamps."""

from __future__ import annotations

import math


def _alpha(cutoff: float, dt: float) -> float:
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuro:
    def __init__(self, min_cutoff: float, beta: float, d_cutoff: float) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x: float | None = None
        self._dx = 0.0
        self._t = 0.0

    def reset(self) -> None:
        self._x = None
        self._dx = 0.0

    def __call__(self, x: float, t_s: float) -> float:
        if self._x is None:
            self._x, self._dx, self._t = x, 0.0, t_s
            return x
        dt = t_s - self._t
        if dt <= 0.0:
            return self._x
        raw_dx = (x - self._x) / dt
        a_d = _alpha(self.d_cutoff, dt)
        self._dx = a_d * raw_dx + (1.0 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        a = _alpha(cutoff, dt)
        self._x = a * x + (1.0 - a) * self._x
        self._t = t_s
        return self._x
