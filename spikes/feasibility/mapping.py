"""Cursor mappers for the Phase 0 spike (THROWAWAY). See research.md R5."""


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class AbsoluteMapper:
    """Maps a central region of the (mirrored) camera view linearly onto the screen."""

    def __init__(self, screen_rect: tuple[int, int, int, int], region: float = 0.6):
        self.left, self.top, self.width, self.height = screen_rect
        self.region = region

    def map(self, x: float, y: float) -> tuple[int, int]:
        edge = 0.5 - self.region / 2
        u = _clamp((x - edge) / self.region, 0.0, 1.0)
        v = _clamp((y - edge) / self.region, 0.0, 1.0)
        return (
            self.left + round(u * (self.width - 1)),
            self.top + round(v * (self.height - 1)),
        )


class RelativeMapper:
    """Moves the cursor by hand motion; freezes (and re-anchors) while clutched."""

    def __init__(self, screen_rect: tuple[int, int, int, int], gain: float = 2.5):
        self.left, self.top, self.width, self.height = screen_rect
        self.gain = gain
        self.last: tuple[float, float] | None = None

    def reset(self) -> None:
        self.last = None

    def map(self, x: float, y: float, clutched: bool, cursor: tuple[int, int]) -> tuple[int, int] | None:
        if self.last is None or clutched:
            self.last = (x, y)
            return None
        nx = cursor[0] + (x - self.last[0]) * self.gain * self.width
        ny = cursor[1] + (y - self.last[1]) * self.gain * self.width
        self.last = (x, y)
        nx = _clamp(nx, self.left, self.left + self.width - 1)
        ny = _clamp(ny, self.top, self.top + self.height - 1)
        return (round(nx), round(ny))


if __name__ == "__main__":
    rect = (0, 0, 1920, 1080)
    a = AbsoluteMapper(rect, 0.6)
    cx, cy = a.map(0.5, 0.5)
    assert abs(cx - 959.5) <= 1 and abs(cy - 539.5) <= 1, (cx, cy)
    assert a.map(0.2, 0.2) == (0, 0)
    assert a.map(0.8, 0.8) == (1919, 1079)
    assert a.map(0.0, 1.0) == (0, 1079)

    r = RelativeMapper(rect, 2.5)
    assert r.map(0.5, 0.5, False, (100, 100)) is None
    assert r.map(0.6, 0.6, True, (100, 100)) is None
    nx, _ = r.map(0.61, 0.6, False, (100, 100))
    assert nx - 100 == 48, nx
    print("OK")
