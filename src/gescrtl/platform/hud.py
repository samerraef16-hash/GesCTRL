"""On-screen indicator (HUD pill) built with PySide6 (plan D14, docs/interaction/feedback-hud.md).

Windows are always on top, never take focus, never intercept clicks, and never show camera
imagery. All methods must run on the Qt main thread; ``UiBridge`` in app.py marshals events.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

from gescrtl.core.types import Event, HintsShown, State, StateChanged, Sub
from gescrtl.platform.win_window import make_click_through

GREY = QColor(120, 120, 130)
GREEN = QColor(46, 160, 90)
GREEN_DIM = QColor(46, 120, 80)
AMBER = QColor(230, 160, 20)
RED = QColor(210, 60, 60)

_FLAGS = (
    Qt.WindowType.FramelessWindowHint
    | Qt.WindowType.Tool
    | Qt.WindowType.WindowStaysOnTopHint
    | Qt.WindowType.WindowTransparentForInput
    | Qt.WindowType.WindowDoesNotAcceptFocus
)


def style_for(state: State, sub: Sub, text: str) -> tuple[QColor, str]:
    """Colour and optional icon for a state. Text is always shown too (accessibility)."""
    if text == "Stopped":
        return RED, ""
    if state is State.PAUSED:
        return GREY, "⚠ " if "Camera unavailable" in text else ""
    if state is State.ACTIVE:
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


class Hud:
    """Routes core events to the on-screen widgets."""

    def __init__(self, hint_ms: int = 3000) -> None:
        self.pill = Pill(hint_ms)

    def handle(self, event: Event) -> None:
        if isinstance(event, StateChanged):
            if event.state is State.INACTIVE or not event.hud_text:
                self.pill.hide()
                return
            self.pill.set_status(event.state, event.sub, event.hud_text)
            if not self.pill.isVisible():
                self.pill.show()
        elif isinstance(event, HintsShown):
            self.pill.show_hints(event.items)

    def set_recording(self, on: bool) -> None:
        self.pill.set_badge("● REC" if on else "")

    def close(self) -> None:
        self.pill.close()
