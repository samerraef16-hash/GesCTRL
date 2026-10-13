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
    active_center_x: float = 0.5  # calibration may move the region (spec 004 D7)
    active_center_y: float = 0.5
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
    clutch_fist_ms: int = 600  # a fist must be held this long to end the flat-hand hold
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

    # Mode menu and level panel (spec 003 D5, D8)
    menu_hold_ms: int = 800
    menu_timeout_ms: int = 5000
    panel_hold_ms: int = 500
    panel_timeout_ms: int = 5000

    # Presentation: swipe (D6). Distances are in hand sizes, speeds in hand sizes per second.
    swipe_window_ms: int = 350
    swipe_min_frames: int = 3
    swipe_min_dist: float = 1.5
    swipe_max_dy_ratio: float = 0.5
    swipe_cooldown_ms: int = 600
    swipe_return_block_ms: int = 1000
    swipe_rearm_speed: float = 1.0
    swipe_rearm_ms: int = 100

    # Presentation: slide show start/end by thumb direction, with hysteresis (enter > exit)
    show_hold_ms: int = 1000
    show_cooldown_ms: int = 2000
    thumb_dir_enter_deg: float = 50.0
    thumb_dir_exit_deg: float = 35.0

    # Presentation: laser pointer (stronger smoothing than Pointer Mode)
    laser_min_cutoff: float = 0.3
    laser_beta: float = 0.002
    laser_grace_ms: int = 300

    # Level control (volume / brightness), in percentage points
    level_step: int = 2
    level_max_rate: float = 40.0  # percentage points per second
    level_drag_gain: float = 1.0  # percent per slider height of hand travel is 100 * gain
    level_repeat_ms: int = 150  # Media Mode: repeat interval while the pinch stays held

    # Pointing at on-screen targets (menu, panel, media grid)
    action_cooldown_ms: int = 400
    confirm_window_ms: int = 3000
    target_margin: float = 0.01  # normalized screen distance inside a target needed to select it

    # Keyboard Mode and confirmation (spec 004 D1, D2, D4)
    confirm_method: str = "pinch"  # "pinch" or "dwell"
    dwell_ms: int = 800
    dwell_still_dist: float = 0.015  # normalized screen distance the point may wander
    pointer_dwell_click: bool = False  # dwell = left click in Pointer Mode (opt-in)
    two_hand_press: bool = True  # Keyboard Mode: the other hand's pinch presses the key
    second_hand_max_dist: float = 5.0  # wrist to wrist, in hand sizes
    keyboard_position: str = "bottom"  # "bottom" or "top"
    key_repeat_delay_ms: int = 500
    key_repeat_ms: int = 100
    key_cooldown_ms: int = 150

    # Gesture to action overrides: ((slot, action name), ...) (spec 004 D6)
    mappings: tuple[tuple[str, str], ...] = ()

    # Custom gestures (spec 004 D9)
    custom_gestures_enabled: bool = False
    custom_hold_ms: int = 600
    custom_cooldown_ms: int = 1500
