"""Monitor layout for the pointer (spec 004 D8, FR-020).

``MoveCursor`` is normalized over the *desktop box*: the bounding box of all monitors. A point
that falls in a gap between monitors (or outside a staggered arrangement) is moved to the nearest
point of the nearest monitor, so the cursor never goes where there is no screen. Without a layout
the box is the primary monitor and nothing changes (old recordings replay unchanged).
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Display:
    x: int
    y: int
    w: int
    h: int
    primary: bool = False
    name: str = ""


class Displays:
    def __init__(self, displays: tuple[Display, ...]) -> None:
        if not displays:
            raise ValueError("at least one display is required")
        self.displays = displays
        self.x = min(d.x for d in displays)
        self.y = min(d.y for d in displays)
        self.w = max(d.x + d.w for d in displays) - self.x
        self.h = max(d.y + d.h for d in displays) - self.y
        primary = next((d for d in displays if d.primary), displays[0])
        # a distance of 0.02 of the primary monitor, expressed in desktop-box fractions
        self.scale_x = primary.w / self.w
        self.scale_y = primary.h / self.h

    @classmethod
    def parse(cls, arg: str) -> Displays | None:
        """The layout in a ``DISPLAYS`` command (a JSON list), or None if it is unusable."""
        try:
            raw = json.loads(arg)
            items = tuple(
                Display(
                    int(d["x"]),
                    int(d["y"]),
                    int(d["w"]),
                    int(d["h"]),
                    bool(d.get("primary", False)),
                    str(d.get("name", "")),
                )
                for d in raw
            )
        except (ValueError, TypeError, KeyError):
            return None
        if not items or any(d.w <= 0 or d.h <= 0 for d in items):
            return None
        return cls(items)

    def clamp(self, nx: float, ny: float) -> tuple[float, float]:
        """``(nx, ny)`` over the desktop box, moved onto a monitor if it is in a gap."""
        px = self.x + nx * self.w
        py = self.y + ny * self.h
        best: tuple[float, float] | None = None
        best_d = float("inf")
        for d in self.displays:
            cx = min(max(px, d.x), d.x + d.w - 1)
            cy = min(max(py, d.y), d.y + d.h - 1)
            dist = (cx - px) ** 2 + (cy - py) ** 2
            if dist == 0:
                return nx, ny  # already on a monitor
            if dist < best_d:
                best, best_d = (cx, cy), dist
        assert best is not None
        return (best[0] - self.x) / self.w, (best[1] - self.y) / self.h
