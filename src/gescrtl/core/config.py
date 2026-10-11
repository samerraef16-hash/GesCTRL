"""Tunable values for the pure core.

Defaults follow ``docs/interaction/safety-policy.md`` (One Euro and loss window measured in
Phase 0; the rest provisional until Phase 2 tuning, see tasks T051).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CoreConfig:
    # Mapping and smoothing (ADR 0005)
    active_region: float = 0.6
    one_euro_min_cutoff: float = 1.0
    one_euro_beta: float = 0.007
    one_euro_d_cutoff: float = 1.0

    # Confidence and stability (safety-policy.md)
    min_confidence: float = 0.5
    stable_frames: int = 3
    loss_frames: int = 3

    # Pinch hysteresis (ratio of fingertip distance to hand size)
    pinch_enter: float = 0.25
    pinch_release: float = 0.35

    # Hold times and cooldowns (ms)
    resume_hold_ms: int = 1000
    pause_hold_ms: int = 1500
    drag_hold_ms: int = 300
    right_click_cooldown_ms: int = 300
    right_click_max_hold_ms: int = 1000
    pause_resume_cooldown_ms: int = 1000
    click_stabilize_ms: int = 100
    pinch_lookback_frames: int = 2
    flat_hand_frames: int = 5  # the flat hand must be seen longer than other poses to count
    pause_still_dist: float = 0.04  # the flat hand must also stay this still (camera units)

    # Scrolling by thumb tilt (like holding a scroll wheel): speed grows with the tilt away from
    # where the pose started
    scroll_max_rate: float = 1800.0  # wheel units per second at full tilt
    scroll_deadzone_deg: float = 8.0  # no scrolling within this tilt of the start angle
    scroll_full_deg: float = 45.0  # tilt that gives the maximum rate
    scroll_settle_ms: int = 250  # after the pose is recognized, the start angle follows the thumb
    scroll_step: int = 30  # wheel units per emitted event

    # Bad-frame rejection (camera-normalized units per frame)
    max_hand_jump: float = 0.15
    max_anchor_jump: float = 0.12

    # Feedback timing
    stopped_display_ms: int = 600
    hint_display_ms: int = 3000
    click_flash_ms: int = 150

    # Double click (platform overrides the time from the OS at startup)
    double_click_ms: int = 500
    double_click_dist: float = 0.02  # normalized screen distance within which taps are snapped
