"""On-screen target layout shared by the core (hit testing) and the HUD (drawing).

Rectangles are normalized to the primary monitor (0..1 on both axes), so the core never knows
pixels. Every target is at least 48 px at 1280x720 (tests/unit/test_layout.py).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    def contains(self, nx: float, ny: float, margin: float = 0.0) -> bool:
        """True if the point is inside the rectangle, at least ``margin`` from every edge."""
        return (
            self.x + margin <= nx <= self.x + self.w - margin
            and self.y + margin <= ny <= self.y + self.h - margin
        )


Items = Sequence[tuple[str, Rect]]


def _row(ids: Sequence[str], w: float, h: float, gap: float, y: float) -> list[tuple[str, Rect]]:
    total = len(ids) * w + (len(ids) - 1) * gap
    x0 = (1.0 - total) / 2
    return [(ident, Rect(x0 + i * (w + gap), y, w, h)) for i, ident in enumerate(ids)]


MODE_MENU_ITEMS: Items = tuple(
    _row(("pointer", "keyboard", "presentation", "media"), 0.18, 0.16, 0.03, 0.42)
)

LEVEL_SLIDERS: Items = tuple(_row(("volume", "brightness"), 0.10, 0.45, 0.10, 0.275))

MEDIA_TARGETS: Items = tuple(
    _row(
        ("play_pause", "prev_track", "next_track", "volume_down", "volume_up"),
        0.15,
        0.14,
        0.03,
        0.34,
    )
    + _row(
        ("mute", "brightness_down", "brightness_up", "screenshot", "app_switch"),
        0.15,
        0.14,
        0.03,
        0.52,
    )
)


def hit(
    items: Items, nx: float, ny: float, margin: float, current: str | None = None
) -> str | None:
    """The target pointed at, with hysteresis (constitution I).

    The ``current`` target stays pointed while the point is anywhere inside its rectangle. A new
    target is returned only when the point is inside it by at least ``margin``. A point on an
    edge, in a gap, or outside every target newly selects nothing.
    """
    if current is not None:
        for ident, rect in items:
            if ident == current and rect.contains(nx, ny):
                return current
    for ident, rect in items:
        if rect.contains(nx, ny, margin):
            return ident
    return None
