"""The deterministic core: landmark frames and commands in, events out (plan D1, D2).

No camera, OS, or wall-clock access: time is the timestamps handed in by the caller, so a
recording replays to exactly the same events (constitution IV).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from gescrtl.core import features
from gescrtl.core.config import CoreConfig
from gescrtl.core.level_panel import LevelPanel
from gescrtl.core.media import MediaController
from gescrtl.core.mode_menu import ModeMenu
from gescrtl.core.modes import ModeController, NullController, PointerController
from gescrtl.core.pointer import Pointer
from gescrtl.core.poses import PoseClassifier, PoseTracker
from gescrtl.core.presentation import PresentationController
from gescrtl.core.primary_hand import PrimaryHand
from gescrtl.core.state_machine import StateMachine
from gescrtl.core.types import (
    DEFAULT_ASPECT,
    Command,
    CueChanged,
    CueKind,
    Event,
    Hand,
    HandFrame,
    Mode,
    Pose,
    ReleaseAll,
    State,
    Sub,
)

_MS = 1_000_000


@dataclass(frozen=True, slots=True)
class DebugInfo:
    """What the recognizer saw on the latest good frame (shown in the camera preview)."""

    raw: Pose
    stable: Pose
    pinch_index: float
    pinch_middle: float
    thumb_out: float
    curl: tuple[float, float, float, float]
    anchor: tuple[float, float]
    thumb_tilt_deg: float
    upright_deg: float = 0.0  # hand lean away from straight up (flat hand needs <= 25)
    scroll_rel_deg: float = 0.0  # thumb tilt away from where the scroll pose started
    scroll_rate: float = 0.0  # wheel units per second being sent


class Engine:
    def __init__(self, cfg: CoreConfig | None = None) -> None:
        self.cfg = cfg or CoreConfig()
        self.sm = StateMachine(self.cfg)
        self.classifier = PoseClassifier(self.cfg)
        self.tracker = PoseTracker(self.cfg)
        self.primary = PrimaryHand(self.cfg)
        self.pointer = Pointer(self.cfg)
        self.presentation = PresentationController(self.cfg)
        self._controllers: dict[Mode, ModeController] = {
            Mode.POINTER: PointerController(self.pointer),
            Mode.PRESENTATION: self.presentation,
            Mode.MEDIA: MediaController(self.cfg),
        }
        self._null = NullController()  # modes without gestures yet
        self.menu = ModeMenu(self.cfg)
        self.panel = LevelPanel(self.cfg)
        self._g7_blocked = False  # three fingers must be relaxed once before the menu
        self._g9_blocked = False  # same for the call-me gesture and the level panel
        self._bad = 0
        self._last_anchor: tuple[float, float] | None = None
        self._still_ref: tuple[float, float] | None = None  # flat-hand pause stillness check
        self._still_since_ns = 0
        self._fist = False  # stable fist while Active · Normal: cursor frozen, pause timer running
        self.debug: DebugInfo | None = None

    @property
    def state(self) -> State:
        return self.sm.state

    @property
    def sub(self) -> Sub:
        return self.sm.sub

    # -- public API ------------------------------------------------------------------------

    def start(self) -> list[Event]:
        """E1: the initial indicator events (the engine already is Paused)."""
        return self.sm.start()

    def tick(self, t_ns: int) -> list[Event]:
        """Advance timers when no frame arrived (e.g. the 'Stopped' display)."""
        return self.sm.tick(t_ns)

    def command(self, cmd: Command, t_ns: int, arg: str = "") -> list[Event]:
        events = self.sm.tick(t_ns)
        before = self._snapshot()
        events += self.sm.on_command(cmd, t_ns, arg)
        events += self._after_transition(before)
        return events

    def apply_config(self, cfg: CoreConfig) -> list[Event]:
        """Reload settings: release everything first, keep state and mode (FR-024a)."""
        events: list[Event] = [ReleaseAll("reload settings")]
        self.cfg = cfg
        self.sm.cfg = cfg
        self.classifier.cfg = cfg
        self.tracker.cfg = cfg
        self.primary.cfg = cfg
        self.pointer = Pointer(cfg)
        self._controllers[Mode.POINTER] = PointerController(self.pointer)
        self.presentation = PresentationController(cfg)
        self._controllers[Mode.PRESENTATION] = self.presentation
        self._controllers[Mode.MEDIA] = MediaController(cfg)
        self.menu = ModeMenu(cfg)
        self.panel = LevelPanel(cfg)
        self.tracker.invalidate()
        self.classifier.reset()
        self._last_anchor = None
        return events

    def step(self, frame: HandFrame | None, t_ns: int) -> list[Event]:
        events = self.sm.tick(t_ns)
        sm = self.sm
        if sm.state is State.INACTIVE or sm.sub is Sub.CAMERA_UNAVAILABLE:
            return events

        hands = frame.hands if frame is not None else ()
        aspect = frame.aspect if frame is not None else DEFAULT_ASPECT
        if sm.state is State.PAUSED and len(hands) > 1:
            hands = self._resume_candidates(hands, aspect)
        hand = self.primary.select(hands, reacquire=sm.state in (State.PAUSED, State.TRACKING_LOST))
        feats = None
        if hand is not None and hand.score >= self.cfg.min_confidence:
            feats = features.compute(hand, aspect)
        if (
            feats is not None
            and sm.state is State.ACTIVE
            and self._last_anchor is not None
            and math.dist(feats.anchor, self._last_anchor) > self.cfg.max_anchor_jump
        ):
            feats = None  # implausible jump: treat as a bad frame (plan D10)
        if feats is None:
            return events + self._bad_frame(t_ns)

        self._bad = 0
        self._last_anchor = feats.anchor
        raw = self.classifier.classify(feats)
        stable = self.tracker.update(raw, t_ns)
        self.debug = DebugInfo(
            raw,
            stable,
            feats.pinch_index,
            feats.pinch_middle,
            feats.thumb_out,
            feats.curl,
            feats.anchor,
            feats.thumb_tilt_deg,
            feats.upright_deg,
        )
        before = self._snapshot()

        if sm.state is State.PAUSED:
            events += self._paused(stable, t_ns)
        elif sm.state is State.TRACKING_LOST:
            events += sm.hand_back()
        elif sm.sub is Sub.NORMAL:
            self._still_ref = None
            if stable is Pose.G8_FLAT_HAND:
                events += sm.clutch_start()
            elif self._wants_menu(stable, t_ns):
                events += self._open_menu(t_ns)
            elif self._wants_panel(stable, t_ns):
                events += self._open_panel(t_ns)
            elif sm.mode is Mode.POINTER and stable is Pose.G5_FIST:
                events += self._fist_held()
            else:
                events += self._leave_fist()
                events += self._controller().update(feats, raw, stable, t_ns)
        elif sm.sub is Sub.MODE_MENU:
            events += self._menu_frame(feats, raw, stable, t_ns)
        elif sm.sub is Sub.LEVEL_PANEL:
            events += self._panel_frame(feats, raw, stable, t_ns)
        elif sm.sub is Sub.CLUTCHED:
            if sm.mode is Mode.PRESENTATION:
                events += self.presentation.on_swipe(feats, raw, t_ns)  # a flat-hand swipe counts
            if stable is Pose.G8_FLAT_HAND:
                events += self._flat_hand_pause(t_ns, feats.anchor)
            elif stable is not Pose.NONE:
                events += sm.clutch_end()

        self.debug = replace(
            self.debug,
            scroll_rel_deg=self.pointer.scroll_rel_deg,
            scroll_rate=self.pointer.scroll_rate,
        )
        events += self._after_transition(before)
        return events

    # -- internals -------------------------------------------------------------------------

    def _snapshot(self) -> tuple[State, Sub, Mode]:
        return (self.sm.state, self.sm.sub, self.sm.mode)

    def _wants_menu(self, stable: Pose, t_ns: int) -> bool:
        """Three fingers held long enough, and not in the middle of another gesture (FR-001)."""
        if stable is not Pose.G7_THREE_FINGERS:
            self._g7_blocked = False  # the hand relaxed: the next hold counts
            return False
        if self._controller().busy:
            self._g7_blocked = True  # ignored until the hand relaxes
        if self._g7_blocked:
            return False
        return t_ns - self.tracker.since_ns >= self.cfg.menu_hold_ms * _MS

    def _open_menu(self, t_ns: int) -> list[Event]:
        events = self.sm.open_menu()
        if events:
            events += self.menu.open(t_ns)
        return events

    def _wants_panel(self, stable: Pose, t_ns: int) -> bool:
        """Call-me held long enough, and not in the middle of another gesture (FR-021)."""
        if stable is not Pose.G9_CALL_ME:
            self._g9_blocked = False
            return False
        if self._controller().busy:
            self._g9_blocked = True  # a scroll that drifts into call-me is ignored
        if self._g9_blocked:
            return False
        return t_ns - self.tracker.since_ns >= self.cfg.panel_hold_ms * _MS

    def _open_panel(self, t_ns: int) -> list[Event]:
        events = self.sm.open_panel()
        if events:
            events += self.panel.open(t_ns)
        return events

    def _panel_frame(
        self, feats: features.Features, raw: Pose, stable: Pose, t_ns: int
    ) -> list[Event]:
        if stable is Pose.G7_THREE_FINGERS:  # the mode gesture closes the panel
            self._g7_blocked = True
            return self.sm.close_panel()
        result = self.panel.update(feats, raw, stable, t_ns)
        events = result.events
        if result.close:
            events += self.sm.close_panel()
            self._g9_blocked = True  # call-me still up must not reopen it at once
        return events

    def _menu_frame(
        self, feats: features.Features, raw: Pose, stable: Pose, t_ns: int
    ) -> list[Event]:
        result = self.menu.update(feats, raw, stable, t_ns)
        events = result.events
        if result.cancelled:
            events += self.sm.cancel_menu()
            self._g7_blocked = True  # three fingers still up must not reopen it at once
        elif result.chosen is not None:
            events += self.sm.confirm_mode(result.chosen)
            self._g7_blocked = True
        return events

    def _controller(self) -> ModeController:
        return self._controllers.get(self.sm.mode, self._null)

    def _fist_held(self) -> list[Event]:
        """Stable fist while Normal: release everything once and freeze the cursor."""
        events: list[Event] = []
        if not self._fist:
            self._fist = True
            self.pointer.reset()
            events += [ReleaseAll("fist"), CueChanged(CueKind.CLUTCH)]
        return events

    @staticmethod
    def _resume_candidates(hands: tuple[Hand, ...], aspect: float) -> tuple[Hand, ...]:
        """While Paused with several hands, the one showing the open palm is the candidate."""
        palms = []
        for h in hands:
            f = features.compute(h, aspect)
            if f is not None and f.thumb_extended and all(f.extended(i) for i in range(4)):
                palms.append(h)
        return tuple(palms) or hands

    def _flat_hand_pause(self, t_ns: int, anchor: tuple[float, float]) -> list[Event]:
        """The flat hand held *still* for pause_hold_ms is the gesture path to Pause."""
        if (
            self._still_ref is None
            or math.dist(anchor, self._still_ref) > self.cfg.pause_still_dist
        ):
            self._still_ref, self._still_since_ns = anchor, t_ns
        since = max(self.tracker.since_ns, self._still_since_ns)
        if t_ns - since >= self.cfg.pause_hold_ms * _MS:
            return self.sm.pause(t_ns, "pause gesture")
        return []

    def _leave_fist(self) -> list[Event]:
        if self._fist:
            self._fist = False
            self.pointer.reset()  # re-sync the filter to the hand
        return []

    def _bad_frame(self, t_ns: int) -> list[Event]:
        sm = self.sm
        self._bad += 1
        self.debug = None
        self.tracker.invalidate()
        self.presentation.bad_frame()
        events: list[Event] = []
        if sm.state is State.PAUSED:
            self.tracker.reset()
            self.classifier.reset()
            if self._bad >= self.cfg.loss_frames:
                sm.armed = True  # hand really gone: the resume gesture may count again
        elif sm.state is State.ACTIVE and self._bad >= self.cfg.loss_frames:
            before = self._snapshot()
            events += sm.hand_lost()
            events += self._after_transition(before)
        return events

    def _paused(self, stable: Pose, t_ns: int) -> list[Event]:
        sm = self.sm
        if stable is not Pose.G6_OPEN_PALM and stable is not Pose.NONE:
            sm.armed = True
        if (
            stable is Pose.G6_OPEN_PALM
            and sm.armed
            and t_ns - self.tracker.since_ns >= self.cfg.resume_hold_ms * _MS
            and (
                sm.last_toggle_ns is None
                or t_ns - sm.last_toggle_ns >= self.cfg.pause_resume_cooldown_ms * _MS
            )
        ):
            return sm.resume(t_ns)
        return []

    def _after_transition(self, before: tuple[State, Sub, Mode]) -> list[Event]:
        sm = self.sm
        if self._snapshot() == before:
            return []
        self.menu.reset()
        self.panel.reset()
        self._bad = 0
        self._last_anchor = None
        self._fist = False
        events: list[Event] = []
        for controller in self._controllers.values():
            events += controller.reset()
        if sm.state in (State.TRACKING_LOST, State.INACTIVE):
            self.tracker.reset()
            self.classifier.reset()
        return events
