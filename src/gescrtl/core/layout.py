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


# -- level panel +/- targets (dwell users cannot drag a slider, spec 004 D4) ------------------

LEVEL_STEP_TARGETS: Items = (
    ("volume_up", Rect(0.35, 0.15, 0.10, 0.10)),
    ("volume_down", Rect(0.35, 0.745, 0.10, 0.10)),
    ("brightness_up", Rect(0.55, 0.15, 0.10, 0.10)),
    ("brightness_down", Rect(0.55, 0.745, 0.10, 0.10)),
)


# -- on-screen keyboard (spec 004 D2) ----------------------------------------------------------

_KB_COLS = 11  # grid cells per row; a key may span more than one
_KB_CELL = 0.96 / _KB_COLS
_KB_GAP = 0.006
_KB_KEY_H = 0.07
_KB_ROW_GAP = 0.005
_KB_ROWS = (
    # shortcut row: copy, paste, cut, undo, redo, select all, alt+tab, windows key, esc, move
    (
        ("s:copy", 1),
        ("s:paste", 1),
        ("s:cut", 1),
        ("s:undo", 1),
        ("s:redo", 1),
        ("s:select_all", 1),
        ("s:alt_tab", 1),
        ("s:win", 1),
        ("s:esc", 1),
        ("move", 1),
    ),
    tuple((f"k:{c}", 1) for c in "1234567890-"),
    (*((f"k:{c}", 1) for c in "qwertyuiop"), ("k:backspace", 1)),
    tuple((f"k:{c}", 1) for c in "asdfghjkl;'"),
    (*((f"k:{c}", 1) for c in "zxcvbnm,./"), ("k:tab", 1)),
    (
        ("m:shift", 1),
        ("m:ctrl", 1),
        ("m:alt", 1),
        ("m:win", 1),
        ("k:space", 2),
        ("k:left", 1),
        ("k:up", 1),
        ("k:down", 1),
        ("k:right", 1),
        ("k:enter", 1),
    ),
)
KEYBOARD_H = len(_KB_ROWS) * _KB_KEY_H + (len(_KB_ROWS) - 1) * _KB_ROW_GAP
KEYBOARD_W = 0.96


def keyboard_rect(position: str) -> Rect:
    """The bounding rectangle of all keys, at the bottom or the top of the screen."""
    y = 0.02 if position == "top" else 1.0 - 0.02 - KEYBOARD_H
    return Rect(0.02, y, KEYBOARD_W, KEYBOARD_H)


def keyboard_keys(position: str = "bottom") -> Items:
    """Every key as a normalized rectangle (ids: ``k:`` character/named key, ``m:`` modifier,
    ``s:`` shortcut, ``move``). Rows with fewer cells are centered."""
    rect = keyboard_rect(position)
    keys: list[tuple[str, Rect]] = []
    for r, row in enumerate(_KB_ROWS):
        y = rect.y + r * (_KB_KEY_H + _KB_ROW_GAP)
        cells = sum(span for _, span in row)
        x = rect.x + (_KB_COLS - cells) * _KB_CELL / 2
        for ident, span in row:
            w = span * _KB_CELL - _KB_GAP
            keys.append((ident, Rect(x + _KB_GAP / 2, y, w, _KB_KEY_H)))
            x += span * _KB_CELL
    return tuple(keys)
