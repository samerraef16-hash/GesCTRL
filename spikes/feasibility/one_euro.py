"""One Euro smoothing filter for the Phase 0 spike (THROWAWAY). See research.md R7."""
import math


def _alpha(cutoff: float, dt: float) -> float:
    return 1.0 / (1.0 + (1.0 / (2.0 * math.pi * cutoff)) / dt)


class OneEuroFilter:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self) -> None:
        self._x_hat = None
        self._t = None
        self._dx_hat = 0.0

    def __call__(self, x: float, t: float) -> float:
        """x is the new sample; t is its time in seconds."""
        if self._x_hat is None:
            self._x_hat = x
            self._t = t
            self._dx_hat = 0.0
            return x
        dt = t - self._t
        if dt <= 0:
            dt = 1e-3
        dx = (x - self._x_hat) / dt
        self._dx_hat = self._dx_hat + _alpha(self.d_cutoff, dt) * (dx - self._dx_hat)
        cutoff = self.min_cutoff + self.beta * abs(self._dx_hat)
        self._x_hat = self._x_hat + _alpha(cutoff, dt) * (x - self._x_hat)
        self._t = t
        return self._x_hat


class OneEuro2D:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self._fx = OneEuroFilter(min_cutoff, beta, d_cutoff)
        self._fy = OneEuroFilter(min_cutoff, beta, d_cutoff)

    def __call__(self, x: float, y: float, t: float) -> tuple[float, float]:
        return (self._fx(x, t), self._fy(y, t))

    def reset(self) -> None:
        self._fx.reset()
        self._fy.reset()


if __name__ == "__main__":
    f = OneEuroFilter()
    out = 0.0
    for i in range(60):
        out = f(0.5, i / 30)
        assert abs(out - 0.5) < 1e-9, out
    f = OneEuroFilter()
    out = 0.0
    for i in range(60):
        out = f(0.0 if i == 0 else 1.0, i / 30)
    assert abs(out - 1.0) < 0.01, out
    print("OK")
