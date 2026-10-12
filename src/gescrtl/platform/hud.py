"""On-screen indicator (HUD pill) built with PySide6 (plan D14, docs/interaction/feedback-hud.md).

Windows are always on top, never take focus, never intercept clicks, and never show camera
imagery. All methods must run on the Qt main thread; ``UiBridge`` in app.py marshals events.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gescrtl.core.types import (
    CueChanged,
    CueKind,
    Event,
    HintsShown,
    LevelReading,
    Mode,
    ModeChanged,
    MoveCursor,
    OverlayHidden,
    OverlayKind,
    OverlayPointer,
    OverlayPointerHidden,
    OverlayShown,
    PointerStyle,
    State,
    StateChanged,
    Sub,
)
from gescrtl.platform.overlays import (
    OVERLAY_FLAGS,
    LaserDot,
    LevelPanelView,
    MediaGridView,
    ModeMenuView,
    SelectRing,
)
from gescrtl.platform.win_window import make_click_through

GREY = QColor(120, 120, 130)
GREEN = QColor(46, 160, 90)
GREEN_DIM = QColor(46, 120, 80)
AMBER = QColor(230, 160, 20)
RED = QColor(210, 60, 60)
BLUE = QColor(40, 110, 220)

_FLAGS = OVERLAY_FLAGS


def style_for(state: State, sub: Sub, text: str) -> tuple[QColor, str]:
    """Colour and optional icon for a state. Text is always shown too (accessibility)."""
    if text == "Stopped":
        return RED, ""
    if state is State.PAUSED:
        return GREY, "⚠ " if "Camera unavailable" in text else ""
    if state is State.ACTIVE:
        if sub in (Sub.MODE_MENU, Sub.LEVEL_PANEL):
            return BLUE, ""
        return (GREEN_DIM if sub is Sub.CLUTCHED else GREEN), ""
    if state is State.TRACKING_LOST:
        return (RED if sub is Sub.CAMERA_UNAVAILABLE else AMBER), "⚠ "
    return GREY, ""


class Pill(QWidget):
    """Compact pill at the top-right of the primary monitor, with optional hint lines."""

    def __init__(self, hint_ms: int = 3000) -> None:
        super().__init__(None, _FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._hint_ms = hint_ms
        self._text = "Paused"
        self._icon = ""
        self._color = GREY
        self._hints: tuple[str, ...] = ()
        self._badge = ""  # e.g. "● REC"
        self._hint_timer = QTimer(self)
        self._hint_timer.setSingleShot(True)
        self._hint_timer.timeout.connect(self._clear_hints)
        make_click_through(int(self.winId()))  # creates the native window, then styles it
        self._relayout()

    # -- content ---------------------------------------------------------------------------

    def set_status(self, state: State, sub: Sub, text: str) -> None:
        self._color, self._icon = style_for(state, sub, text)
        self._text = text
        self._relayout()
        self.update()

    def set_badge(self, badge: str) -> None:
        self._badge = badge
        self._relayout()
        self.update()

    def show_hints(self, items: tuple[str, ...]) -> None:
        self._hints = items
        self._hint_timer.start(self._hint_ms)
        self._relayout()
        self.update()

    def _clear_hints(self) -> None:
        self._hints = ()
        self._relayout()
        self.update()

    # -- geometry and painting ---------------------------------------------------------------

    def _title(self) -> str:
        return f"{self._icon}{self._text}" + (f"   {self._badge}" if self._badge else "")

    def _relayout(self) -> None:
        title_font = QFont(self.font())
        title_font.setPointSize(11)
        title_font.setBold(True)
        hint_font = QFont(self.font())
        hint_font.setPointSize(9)
        tm, hm = QFontMetrics(title_font), QFontMetrics(hint_font)
        width = tm.horizontalAdvance(self._title()) + 44
        for h in self._hints:
            width = max(width, hm.horizontalAdvance(h) + 32)
        height = 34 + (len(self._hints) * (hm.height() + 2) + 8 if self._hints else 0)
        self.resize(width, height)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            geo = screen.geometry()
            self.move(geo.right() - width - 16, geo.top() + 16)

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(28, 28, 34, 225))
        p.drawRoundedRect(rect, 17, 17)
        p.setBrush(self._color)
        p.drawEllipse(QRectF(12, 11, 12, 12))
        title_font = QFont(self.font())
        title_font.setPointSize(11)
        title_font.setBold(True)
        p.setFont(title_font)
        p.setPen(QColor(240, 240, 240))
        p.drawText(
            QRectF(32, 0, self.width() - 40, 34), Qt.AlignmentFlag.AlignVCenter, self._title()
        )
        if self._hints:
            hint_font = QFont(self.font())
            hint_font.setPointSize(9)
            p.setFont(hint_font)
            p.setPen(QColor(200, 200, 205))
            y = 34
            line = QFontMetrics(hint_font).height() + 2
            for h in self._hints:
                p.drawText(QRectF(16, y, self.width() - 24, line), Qt.AlignmentFlag.AlignVCenter, h)
                y += line


CUE_SIZE = 48


class CursorCue(QWidget):
    """48 px click-through indicator centred on the cursor (D14): what the next gesture does.

    Ring = ready, arc = pinch closing, flash = click, filled = drag, arrow = scroll direction,
    dashed = cursor held. Redraws only when a cue or the cursor position changes.
    """

    def __init__(self) -> None:
        super().__init__(None, _FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.resize(CUE_SIZE, CUE_SIZE)
        self._kind = CueKind.HIDDEN
        self._progress = 0.0
        self._center = (0, 0)
        make_click_through(int(self.winId()))

    def move_to(self, nx: float, ny: float) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.geometry()
        cx = geo.left() + round(nx * (geo.width() - 1))
        cy = geo.top() + round(ny * (geo.height() - 1))
        self._center = (cx, cy)
        self.move(cx - CUE_SIZE // 2, cy - CUE_SIZE // 2)

    def set_cue(self, kind: CueKind, progress: float) -> None:
        self._kind, self._progress = kind, progress
        if kind is CueKind.HIDDEN:
            self.hide()
            return
        if not self.isVisible():
            self.show()
        self.update()

    def paintEvent(self, _event: object) -> None:
        if self._kind is CueKind.HIDDEN:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(6, 6, CUE_SIZE - 12, CUE_SIZE - 12)
        k, prog = self._kind, self._progress

        def pen(color: QColor, width: float = 3.0, dashed: bool = False) -> QPen:
            pn = QPen(color, width)
            if dashed:
                pn.setStyle(Qt.PenStyle.DashLine)
            return pn

        p.setBrush(Qt.BrushStyle.NoBrush)
        if k is CueKind.READY:
            p.setPen(pen(QColor(255, 255, 255, 150), 2))
            p.drawEllipse(box)
        elif k is CueKind.PINCH:
            p.setPen(pen(QColor(255, 255, 255, 90), 2))
            p.drawEllipse(box)
            p.setPen(pen(GREEN, 4))
            p.drawArc(box, 90 * 16, -round(360 * 16 * max(prog, 0.05)))
        elif k is CueKind.CLICK:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 220))
            p.drawEllipse(box.adjusted(-2, -2, 2, 2))
        elif k is CueKind.DRAG:
            p.setPen(pen(GREEN, 3))
            p.setBrush(QColor(46, 160, 90, 170))
            p.drawEllipse(box)
        elif k is CueKind.SCROLL:
            p.setPen(pen(QColor(255, 255, 255, 200), 2))
            p.drawEllipse(box)
            mid, up = CUE_SIZE / 2, prog >= 0
            strength = abs(prog)
            p.setPen(pen(AMBER if strength > 0 else QColor(255, 255, 255, 120), 3))
            for tip_y, base_y, active in ((11, 19, up), (CUE_SIZE - 11, CUE_SIZE - 19, not up)):
                if strength == 0 or active:
                    p.drawLine(round(mid - 6), base_y, round(mid), tip_y)
                    p.drawLine(round(mid + 6), base_y, round(mid), tip_y)
        elif k is CueKind.CLUTCH:
            p.setPen(pen(QColor(255, 255, 255, 190), 2, dashed=True))
            p.drawEllipse(box)


class Hud:
    """Routes core events to the on-screen widgets."""

    def __init__(self, hint_ms: int = 3000) -> None:
        self.pill = Pill(hint_ms)
        self.cue = CursorCue()
        self.ring = SelectRing()  # points at menu items and action targets
        self.laser = LaserDot()  # presentation laser pointer
        self.menu_view = ModeMenuView()
        self.panel_view = LevelPanelView()
        self.media_view = MediaGridView()
        self.mode = Mode.POINTER  # the current mode, for highlighting it in the menu

    def handle(self, event: Event) -> None:
        if isinstance(event, MoveCursor):
            self.cue.move_to(event.nx, event.ny)
        elif isinstance(event, CueChanged):
            self.cue.set_cue(event.kind, event.progress)
        elif isinstance(event, OverlayPointer):
            marker, other = (
                (self.ring, self.laser)
                if event.style is PointerStyle.SELECT
                else (self.laser, self.ring)
            )
            other.hide_marker()
            marker.show_marker(event.nx, event.ny)
        elif isinstance(event, OverlayPointerHidden):
            self.ring.hide_marker()
            self.laser.hide_marker()
        elif isinstance(event, ModeChanged):
            self.mode = event.mode
        elif isinstance(event, OverlayShown):
            if event.kind is OverlayKind.MODE_MENU:
                self.menu_view.show_menu(self.mode, event.highlight)
            elif event.kind is OverlayKind.LEVELS:
                self.panel_view.show_panel(event.highlight)
            elif event.kind is OverlayKind.MEDIA:
                self.media_view.show_grid(event.highlight, event.pending)
        elif isinstance(event, LevelReading):
            self.panel_view.set_value(event.level, event.value)
        elif isinstance(event, OverlayHidden):
            if event.kind is OverlayKind.MEDIA:
                self.media_view.hide()
                self.ring.hide_marker()
            else:
                self._hide_overlays()
        elif isinstance(event, StateChanged):
            if event.state is not State.ACTIVE:
                self.cue.set_cue(CueKind.HIDDEN, 0.0)
                self._hide_overlays()
                self.laser.hide_marker()
            if event.state is State.INACTIVE or not event.hud_text:
                self.pill.hide()
                return
            self.pill.set_status(event.state, event.sub, event.hud_text)
            if not self.pill.isVisible():
                self.pill.show()
        elif isinstance(event, HintsShown):
            self.pill.show_hints(event.items)

    def _hide_overlays(self) -> None:
        self.ring.hide_marker()
        self.menu_view.hide()
        self.panel_view.hide()
        self.media_view.hide()

    def set_recording(self, on: bool) -> None:
        self.pill.set_badge("● REC" if on else "")

    def close(self) -> None:
        self.pill.close()
        self.cue.close()
        self.ring.close()
        self.laser.close()
        self.menu_view.close()
        self.panel_view.close()
        self.media_view.close()
