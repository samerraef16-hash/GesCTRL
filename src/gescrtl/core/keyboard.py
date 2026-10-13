"""Keyboard Mode: point at a key on the on-screen keyboard, pinch (or dwell) to press it (D2).

Each hand is mapped onto the keyboard area only, so a small movement reaches every key. The first
(primary) hand and the user's second hand (see ``second_hand``) each point and press on their own,
so both hands can type; whichever presses first sends first. Nothing is sent unless a *stable*
pinch or a dwell of that hand completes on the key that hand points at. The OS cursor never moves
in this mode. Modifiers are kept
here and folded into each ``KeyStroke``; they are never held down in Windows, so a crash cannot
leave one stuck (the platform's ``release_all`` still covers a half-sent chord).
"""

from __future__ import annotations

from gescrtl.core import layout
from gescrtl.core.config import CoreConfig
from gescrtl.core.features import Features
from gescrtl.core.second_hand import SecondInput
from gescrtl.core.select import DwellSelector, PinchSelector, ScreenPointer
from gescrtl.core.types import (
    Action,
    Event,
    KeyboardView,
    KeyStroke,
    OverlayHidden,
    OverlayKind,
    Pose,
    SystemAction,
)

_MS = 1_000_000
_RECENT = 24

MODS = ("shift", "ctrl", "alt", "win")
_SHIFTED = {
    **{c: c.upper() for c in "abcdefghijklmnopqrstuvwxyz"},
    "1": "!",
    "2": "@",
    "3": "#",
    "4": "$",
    "5": "%",
    "6": "^",
    "7": "&",
    "8": "*",
    "9": "(",
    "0": ")",
    "-": "_",
    ";": ":",
    "'": '"',
    ",": "<",
    ".": ">",
    "/": "?",
}
_NAMED = {"backspace", "tab", "space", "enter", "left", "right", "up", "down"}
_REPEATING = {"backspace", "left", "right", "up", "down"}
_SHORTCUTS = {
    "s:copy": Action.COPY,
    "s:paste": Action.PASTE,
    "s:cut": Action.CUT,
    "s:undo": Action.UNDO,
    "s:redo": Action.REDO,
    "s:select_all": Action.SELECT_ALL,
    "s:alt_tab": Action.APP_SWITCH,
    "s:win": Action.WIN,
    "s:esc": Action.ESC,
}


class _Lane:
    """One hand's pointing and pressing: its own smoothing, pinch selector and dwell."""

    def __init__(self, cfg: CoreConfig) -> None:
        self.pointer = ScreenPointer(cfg)
        self.selector = PinchSelector(cfg, cooldown_ms=cfg.key_cooldown_ms)
        self.dwell = DwellSelector(cfg)
        self.pointed: str | None = None

    def reset(self) -> None:
        self.pointer.reset()
        self.selector.reset()
        self.dwell.reset()
        self.pointed = None


class KeyboardController:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        self._lane = _Lane(cfg)  # the primary hand
        self._lane2 = _Lane(cfg)  # the second hand
        self.second_input: SecondInput | None = None  # set by the engine before each update
        self._position = cfg.keyboard_position
        self._shown = False
        self._clear()

    def _clear(self) -> None:
        self._mods: dict[str, int] = {m: 0 for m in MODS}  # 0 off, 1 one-shot, 2 locked
        self._recent = ""
        self._pressed = ""
        self._pressed_until_ns = 0
        self._repeat_key: str | None = None
        self._repeat_lane: _Lane | None = None
        self._repeat_next_ns = 0
        self._last_press: tuple[str, _Lane, int] | None = None
        self._last_view: KeyboardView | None = None

    @property
    def busy(self) -> bool:
        return self._lane.selector.pinching or self._lane2.selector.pinching

    @property
    def position(self) -> str:
        return self._position

    @property
    def recent(self) -> str:
        return self._recent

    def reset(self) -> list[Event]:
        self._lane.reset()
        self._lane2.reset()
        self.second_input = None
        self._clear()
        if self._shown:
            self._shown = False
            return [OverlayHidden(OverlayKind.KEYBOARD)]
        return []

    # -- per frame ----------------------------------------------------------------------------

    def update(self, feats: Features, raw: Pose, stable: Pose, t_ns: int) -> list[Event]:
        events = self._step(self._lane, feats, raw, stable, t_ns)
        second = self.second_input
        if second is not None:
            events += self._step(self._lane2, second.feats, second.raw, second.stable, t_ns)
        else:
            self._lane2.reset()  # a hand that leaves must not keep a half-made pinch
        events += self._emit_view(t_ns)
        return events

    def _step(
        self, lane: _Lane, feats: Features, raw: Pose, stable: Pose, t_ns: int
    ) -> list[Event]:
        nx, ny = lane.pointer.update(feats.anchor, t_ns)
        rect = layout.keyboard_rect(self._position)
        clip = self.cfg.target_margin + 1e-6  # the end keys must be reachable by the margin rule
        px = rect.x + clip + nx * (rect.w - 2 * clip)
        py = rect.y + clip + ny * (rect.h - 2 * clip)
        keys = layout.keyboard_keys(self._position)
        lane.pointed = layout.hit(keys, px, py, self.cfg.target_margin, current=lane.pointed)

        chosen = lane.selector.update(lane.pointed, raw, stable, t_ns)
        if self.cfg.confirm_method == "dwell":
            chosen = chosen or lane.dwell.update(lane.pointed, (px, py), t_ns)
        events: list[Event] = []
        if chosen is not None:
            if self._duplicate(chosen, lane, t_ns):
                return events  # both hands pressed the same key together: one press
            events += self._press(chosen, lane, t_ns, repeatable=lane.selector.pinching)
        elif self._repeat_key is not None and self._repeat_lane is lane:
            events += self._repeat(lane, t_ns)
        return events

    def _duplicate(self, ident: str, lane: _Lane, t_ns: int) -> bool:
        last = self._last_press
        return (
            last is not None
            and last[0] == ident
            and last[1] is not lane
            and t_ns - last[2] < self.cfg.key_cooldown_ms * _MS
        )

    # -- pressing -----------------------------------------------------------------------------

    def _press(self, ident: str, lane: _Lane, t_ns: int, repeatable: bool) -> list[Event]:
        self._last_press = (ident, lane, t_ns)
        self._pressed = ident
        self._pressed_until_ns = t_ns + self.cfg.click_flash_ms * _MS
        kind, _, name = ident.partition(":")
        if ident == "move":
            self._position = "top" if self._position == "bottom" else "bottom"
            self._lane.pointer.reset()
            self._lane2.pointer.reset()
            return []
        if kind == "m":
            self._cycle_mod(name)
            return []
        if kind == "s":
            self._clear_oneshots()
            self._recent = ""
            return [SystemAction(_SHORTCUTS[ident])]
        self._repeat_key = None
        stroke = self._stroke(name)
        self._clear_oneshots()
        if repeatable and name in _REPEATING:
            self._repeat_key = ident
            self._repeat_lane = lane
            self._repeat_next_ns = t_ns + self.cfg.key_repeat_delay_ms * _MS
        self._track_text(stroke)
        return [stroke]

    def _repeat(self, lane: _Lane, t_ns: int) -> list[Event]:
        key = self._repeat_key
        if key is None:
            return []
        if not lane.selector.pinching or lane.pointed != key:
            self._repeat_key = None
            return []
        if t_ns < self._repeat_next_ns:
            return []
        interval = self.cfg.key_repeat_ms * _MS
        self._repeat_next_ns += interval
        if self._repeat_next_ns <= t_ns:  # a stalled camera must not cause a burst
            self._repeat_next_ns = t_ns + interval
        stroke = self._stroke(key.partition(":")[2])
        self._track_text(stroke)
        self._pressed, self._pressed_until_ns = key, t_ns + self.cfg.click_flash_ms * _MS
        return [stroke]

    def _stroke(self, name: str) -> KeyStroke:
        mods = {m for m, state in self._mods.items() if state}
        if len(name) == 1 and "shift" in mods and not (mods - {"shift"}):
            return KeyStroke(_SHIFTED.get(name, name))  # only Shift: fold into the character
        return KeyStroke(name, frozenset(mods))

    def _cycle_mod(self, mod: str) -> None:
        self._mods[mod] = (self._mods[mod] + 1) % 3  # off -> one-shot -> locked -> off

    def _clear_oneshots(self) -> None:
        for m, state in self._mods.items():
            if state == 1:
                self._mods[m] = 0

    def _track_text(self, stroke: KeyStroke) -> None:
        if stroke.key == "backspace":
            self._recent = self._recent[:-1]
        elif stroke.key == "space" and not stroke.mods:
            self._recent = (self._recent + " ")[-_RECENT:]
        elif len(stroke.key) == 1 and not (stroke.mods & {"ctrl", "alt", "win"}):
            self._recent = (self._recent + stroke.key)[-_RECENT:]
        elif stroke.key in _NAMED or stroke.mods:
            self._recent = ""  # enter, tab, arrows and shortcuts move away from the typed text

    # -- view ---------------------------------------------------------------------------------

    def _emit_view(self, t_ns: int) -> list[Event]:
        if t_ns >= self._pressed_until_ns:
            self._pressed = ""
        view = KeyboardView(
            highlight=self._lane.pointed or "",
            highlight2=self._lane2.pointed or "",
            pressed=self._pressed,
            oneshot=frozenset(m for m, s in self._mods.items() if s == 1),
            locked=frozenset(m for m, s in self._mods.items() if s == 2),
            recent=self._recent,
            position=self._position,
            dwell=(
                round(max(self._lane.dwell.progress, self._lane2.dwell.progress), 1)
                if self.cfg.confirm_method == "dwell"
                else 0.0
            ),
        )
        self._shown = True
        if view == self._last_view:
            return []
        self._last_view = view
        return [view]
