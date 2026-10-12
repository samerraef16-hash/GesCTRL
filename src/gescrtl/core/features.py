"""Hand features: hand size, anchor point, pinch ratios, finger extension.

All distances are measured in aspect-corrected image space and divided by hand size
(wrist to middle-finger knuckle), so they do not depend on camera distance (constitution:
scale invariance). Thresholds below were first checked against the Phase 0 pointing recording
(1031 frames): extended fingers read 1.26-1.40 tip/pip, curled ones 0.4-0.95.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from gescrtl.core.types import DEFAULT_ASPECT, Hand, Landmark

WRIST = 0
THUMB_MCP = 2
THUMB_TIP = 4
INDEX_MCP, INDEX_PIP, INDEX_TIP = 5, 6, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP = 9, 10, 12
RING_MCP, RING_PIP, RING_TIP = 13, 14, 16
PINKY_MCP, PINKY_PIP, PINKY_TIP = 17, 18, 20

ANCHOR_POINTS = (0, 5, 9, 13, 17)  # palm center (ADR 0005)

# (mcp, pip, tip) per finger: index, middle, ring, pinky
FINGERS = (
    (INDEX_MCP, INDEX_PIP, INDEX_TIP),
    (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP),
    (RING_MCP, RING_PIP, RING_TIP),
    (PINKY_MCP, PINKY_PIP, PINKY_TIP),
)

EXTENDED_MIN = 1.15  # tip/pip wrist-distance ratio above which a finger counts as extended
CURLED_MAX = 1.05  # ... below which it counts as curled (in between: ambiguous, neither)
# Thumb tip to palm center, in hand sizes. Phase 0 recording: thumb tucked across the palm or
# beside the fingers 0.35-0.55, thumb out 0.77-1.1; 0.68 sits in the gap.
THUMB_OUT_MIN = 0.68
# Thumbs-up also needs the thumb tip clearly away from the index fingertip. In the Phase 0
# recording no natural pointing or pinching frame had curled fingers, thumb out, and this
# distance above 0.8, so a pinch approach cannot start a scroll.
THUMBSUP_MIN_TIP_DIST = 0.8
# Flat hand (clutch / pause) is deliberately strict so it is not mistaken for a pointing hand
# whose thumb is on its way to a pinch: fingers clearly straight, hand upright, thumb deep in
# the palm and well clear of both fingertips.
FLAT_EXTENDED_MIN = 1.25
FLAT_THUMB_MAX = 0.5
FLAT_UPRIGHT_MAX_DEG = 25.0
FLAT_PINCH_CLEAR = 0.45
# Index point (presentation laser): the thumb must be tucked *and* clear of the index fingertip,
# so a thumb on its way to a pinch keeps the hand "relaxed" instead of flickering to a point.
INDEX_POINT_THUMB_CLEAR = 0.6
PINCH_MIN_REACH = 0.9  # a pinching fingertip must not be curled into the palm (tip/mcp)


@dataclass(frozen=True, slots=True)
class Features:
    anchor: tuple[float, float]  # palm center, camera-normalized (not aspect-corrected)
    wrist: tuple[float, float]
    size: float
    pinch_index: float
    pinch_middle: float
    curl: tuple[float, float, float, float]  # tip/pip ratio: index, middle, ring, pinky
    reach: tuple[float, float, float, float]  # tip/mcp ratio
    thumb_out: float  # thumb tip to palm center, in hand sizes
    thumb_tilt_deg: float  # thumb MCP -> tip angle above horizontal; up in the image is positive
    upright_deg: float  # wrist -> middle knuckle angle away from straight up (0 = upright)
    aspect: float = DEFAULT_ASPECT  # frame width / height the distances were corrected with

    def extended(self, finger: int) -> bool:
        return self.curl[finger] > EXTENDED_MIN

    def curled(self, finger: int) -> bool:
        return self.curl[finger] < CURLED_MAX

    @property
    def thumb_extended(self) -> bool:
        return self.thumb_out > THUMB_OUT_MIN

    @property
    def upright(self) -> bool:
        return self.upright_deg <= FLAT_UPRIGHT_MAX_DEG

    @property
    def open_upright(self) -> bool:
        """Four straight fingers on an upright hand (a pinch-middle needs a curled middle)."""
        return self.upright and all(self.extended(i) for i in range(4))

    @property
    def flat_hand(self) -> bool:
        """Strict flat hand: see the FLAT_* constants."""
        return (
            self.upright
            and all(self.curl[i] > FLAT_EXTENDED_MIN for i in range(4))
            and self.thumb_out < FLAT_THUMB_MAX
            and self.pinch_index > FLAT_PINCH_CLEAR
            and self.pinch_middle > FLAT_PINCH_CLEAR
        )

    @property
    def thumbs_up(self) -> bool:
        """Thumb out and well away from the index fingertip (fingers are checked separately)."""
        return self.thumb_extended and self.pinch_index > THUMBSUP_MIN_TIP_DIST

    @property
    def call_me(self) -> bool:
        """Thumb and pinky out, index/middle/ring curled. The pinky must be clearly out (not in
        the ambiguous band), so a scroll pose with a loose pinky never counts."""
        return (
            all(self.curled(i) for i in range(3))
            and self.extended(3)
            and self.thumbs_up  # thumb out and well away from the index fingertip
        )

    @property
    def index_point(self) -> bool:
        """Index finger alone: middle, ring, pinky curled, thumb tucked and clear of the index."""
        return (
            self.extended(0)
            and all(self.curled(i) for i in (1, 2, 3))
            and not self.thumb_extended
            and self.pinch_index > INDEX_POINT_THUMB_CLEAR
        )


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _thumb_tilt(pts: list[tuple[float, float]]) -> float:
    """Angle of the thumb above horizontal. |dx| makes it work for a thumb pointing either way."""
    dx = pts[THUMB_TIP][0] - pts[THUMB_MCP][0]
    dy = pts[THUMB_TIP][1] - pts[THUMB_MCP][1]
    return math.degrees(math.atan2(-dy, abs(dx)))


def compute(hand: Hand, aspect: float) -> Features | None:
    """Return features for ``hand`` or None if the geometry is degenerate."""
    lm: tuple[Landmark, ...] = hand.landmarks
    if len(lm) != 21:
        return None
    pts = [(p.x * aspect, p.y) for p in lm]
    size = _dist(pts[WRIST], pts[MIDDLE_MCP])
    if size < 1e-6:
        return None

    curl: list[float] = []
    reach: list[float] = []
    for mcp, pip, tip in FINGERS:
        d_tip = _dist(pts[tip], pts[WRIST])
        d_pip = max(_dist(pts[pip], pts[WRIST]), 1e-6)
        d_mcp = max(_dist(pts[mcp], pts[WRIST]), 1e-6)
        curl.append(d_tip / d_pip)
        reach.append(d_tip / d_mcp)

    ax = sum(lm[i].x for i in ANCHOR_POINTS) / len(ANCHOR_POINTS)
    ay = sum(lm[i].y for i in ANCHOR_POINTS) / len(ANCHOR_POINTS)
    palm = (ax * aspect, ay)
    return Features(
        anchor=(ax, ay),
        wrist=(lm[WRIST].x, lm[WRIST].y),
        size=size,
        pinch_index=_dist(pts[THUMB_TIP], pts[INDEX_TIP]) / size,
        pinch_middle=_dist(pts[THUMB_TIP], pts[MIDDLE_TIP]) / size,
        curl=(curl[0], curl[1], curl[2], curl[3]),
        reach=(reach[0], reach[1], reach[2], reach[3]),
        thumb_out=_dist(pts[THUMB_TIP], palm) / size,
        thumb_tilt_deg=_thumb_tilt(pts),
        upright_deg=math.degrees(
            math.atan2(abs(pts[MIDDLE_MCP][0] - pts[WRIST][0]), pts[WRIST][1] - pts[MIDDLE_MCP][1])
        ),
        aspect=aspect,
    )
