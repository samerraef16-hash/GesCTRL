"""Overlay widgets for spec 003: the pointing ring, the presentation laser, and (later) the mode
menu, level panel, and media grid (plan D11).

Every window is frameless, always on top, click-through, and never takes focus, exactly like the
spec 002 cursor cue. All methods must run on the Qt main thread; ``UiBridge`` in app.py marshals
core events here. None of these windows ever shows camera imagery.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from gescrtl.core import layout
from gescrtl.core.mode_menu import MODE_BY_ITEM
from gescrtl.core.types import Level, Mode
from gescrtl.platform.win_window import make_click_through

OVERLAY_FLAGS = (
    Qt.WindowType.FramelessWindowHint
    | Qt.WindowType.Tool
    | Qt.WindowType.WindowStaysOnTopHint
    | Qt.WindowType.WindowTransparentForInput
    | Qt.WindowType.WindowDoesNotAcceptFocus
)

LASER_RED = QColor(235, 40, 40)
RING_WHITE = QColor(255, 255, 255, 230)
RING_GREEN = QColor(46, 160, 90)
PANEL_BLUE = QColor(40, 110, 220)
PANEL_DARK = QColor(28, 28, 34, 235)
TEXT_LIGHT = QColor(240, 240, 240)
TEXT_DIM = QColor(150, 150, 158)


class OverlayWindow(QWidget):
    """A transparent, click-through, non-activating window."""

    def __init__(self) -> None:
        super().__init__(None, OVERLAY_FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        make_click_through(int(self.winId()))

    @staticmethod
    def screen_rect() -> QRect:
        """The primary monitor in pixels (device-independent, as Qt places windows)."""
        screen = QGuiApplication.primaryScreen()
        return screen.geometry() if screen is not None else QRect(0, 0, 1920, 1080)

    def to_px(self, nx: float, ny: float) -> tuple[int, int]:
        geo = self.screen_rect()
        return (
            geo.left() + round(nx * (geo.width() - 1)),
            geo.top() + round(ny * (geo.height() - 1)),
        )


class ScreenOverlay(OverlayWindow):
    """Covers the primary monitor and paints targets from the shared normalized layout."""

    def present(self) -> None:
        self.setGeometry(self.screen_rect())
        if not self.isVisible():
            self.show()
        self.update()

    def box(self, rect: layout.Rect) -> QRectF:
        w, h = self.width(), self.height()
        return QRectF(rect.x * w, rect.y * h, rect.w * w, rect.h * h)

    def font_px(self, fraction: float, bold: bool = False) -> QFont:
        font = QFont(self.font())
        font.setPixelSize(max(14, round(self.height() * fraction)))
        font.setBold(bold)
        return font

    def draw_footer(self, p: QPainter, items: layout.Items, text: str) -> None:
        bottom = max(r.y + r.h for _, r in items)
        p.setFont(self.font_px(0.026))
        p.setPen(TEXT_LIGHT)
        area = QRectF(0, bottom * self.height() + 14, self.width(), self.height() * 0.06)
        p.drawText(area, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, text)


class PointerMarker(OverlayWindow):
    """A small marker centred on a normalized screen position."""

    SIZE = 40

    def __init__(self) -> None:
        super().__init__()
        self.resize(self.SIZE, self.SIZE)

    def show_marker(self, nx: float, ny: float) -> None:
        cx, cy = self.to_px(nx, ny)
        self.move(cx - self.SIZE // 2, cy - self.SIZE // 2)
        if not self.isVisible():
            self.show()
            self.raise_()  # a full-screen slide show may have taken the top since the last time
        self.update()

    def hide_marker(self) -> None:
        self.hide()


class SelectRing(PointerMarker):
    """The ring that shows which on-screen target the hand points at (menu, panel, media grid)."""

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(Qt.BrushStyle.NoBrush)
        c = self.SIZE / 2
        p.setPen(QPen(QColor(0, 0, 0, 120), 5))
        p.drawEllipse(QPointF(c, c), 11, 11)
        p.setPen(QPen(RING_WHITE, 3))
        p.drawEllipse(QPointF(c, c), 11, 11)


class LaserDot(PointerMarker):
    """The presentation laser pointer: a red dot with a soft glow, visible on any slide."""

    SIZE = 44

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self.SIZE / 2
        glow = QRadialGradient(QPointF(c, c), c)
        glow.setColorAt(0.0, QColor(255, 60, 60, 190))
        glow.setColorAt(0.45, QColor(255, 40, 40, 90))
        glow.setColorAt(1.0, QColor(255, 40, 40, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(c, c), c, c)
        p.setBrush(LASER_RED)
        p.drawEllipse(QPointF(c, c), 8, 8)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawEllipse(QPointF(c - 2, c - 2), 2.5, 2.5)


MENU_LABELS = {
    "pointer": "Pointer",
    "keyboard": "Keyboard",
    "presentation": "Presentation",
    "media": "Media/System",
}
_ITEM_BY_MODE = {mode: item for item, mode in MODE_BY_ITEM.items()}


class ModeMenuView(ScreenOverlay):
    """The mode menu: four big items in a row (feedback-hud.md). The current mode is filled, the
    one pointed at is outlined, Keyboard is greyed out until spec 004."""

    def __init__(self) -> None:
        super().__init__()
        self.current = Mode.POINTER
        self.highlight = ""

    def show_menu(self, current: Mode, highlight: str) -> None:
        self.current, self.highlight = current, highlight
        self.present()

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 70))
        current_item = _ITEM_BY_MODE.get(self.current, "")
        for ident, rect in layout.MODE_MENU_ITEMS:
            box = self.box(rect)
            available = ident != "keyboard"
            fill = PANEL_BLUE if ident == current_item else PANEL_DARK
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(box, 18, 18)
            if ident == self.highlight and available:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(RING_WHITE, 5))
                p.drawRoundedRect(box.adjusted(-3, -3, 3, 3), 20, 20)
            p.setFont(self.font_px(0.034, bold=True))
            p.setPen(TEXT_LIGHT if available else TEXT_DIM)
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, MENU_LABELS[ident])
            if not available:
                p.setFont(self.font_px(0.022))
                p.drawText(
                    box.adjusted(0, 0, 0, -10),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                    "Later",
                )
        self.draw_footer(p, layout.MODE_MENU_ITEMS, "Pinch to choose · Fist to cancel")


SLIDER_LABELS = {"volume": "Volume", "brightness": "Brightness"}
_SLIDER_LEVEL = {"volume": Level.VOLUME, "brightness": Level.BRIGHTNESS}


class LevelPanelView(ScreenOverlay):
    """The volume / brightness panel: two tall sliders filled to the level the system reported.
    The slider pointed at is outlined; a level that cannot be controlled says so."""

    def __init__(self) -> None:
        super().__init__()
        self.highlight = ""
        self.values: dict[Level, int | None] = {}

    def set_value(self, level: Level, value: int | None) -> None:
        self.values[level] = value
        if self.isVisible():
            self.update()

    def show_panel(self, highlight: str) -> None:
        self.highlight = highlight
        self.present()

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 70))
        for ident, rect in layout.LEVEL_SLIDERS:
            box = self.box(rect)
            level = _SLIDER_LEVEL[ident]
            value = self.values.get(level)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(PANEL_DARK)
            p.drawRoundedRect(box, 18, 18)
            if value is not None:
                fill = QRectF(box)
                fill.setTop(box.bottom() - box.height() * value / 100)
                p.setBrush(PANEL_BLUE)
                p.setClipRect(fill)
                p.drawRoundedRect(box, 18, 18)
                p.setClipping(False)
            if ident == self.highlight:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(RING_WHITE, 5))
                p.drawRoundedRect(box.adjusted(-3, -3, 3, 3), 20, 20)
            p.setPen(TEXT_LIGHT)
            p.setFont(self.font_px(0.034, bold=True))
            text = f"{value}%" if value is not None else "Unavailable"
            if value is None:
                p.setFont(self.font_px(0.022))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
            p.setFont(self.font_px(0.03, bold=True))
            label = QRectF(box.left() - 60, box.top() - 56, box.width() + 120, 50)
            p.drawText(
                label,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                SLIDER_LABELS[ident],
            )
        self.draw_footer(p, layout.LEVEL_SLIDERS, "Pinch and move · Fist to close")


MEDIA_LABELS = {
    "play_pause": "Play / Pause",
    "prev_track": "Previous",
    "next_track": "Next",
    "volume_down": "Volume −",
    "volume_up": "Volume +",
    "mute": "Mute",
    "brightness_down": "Brightness −",
    "brightness_up": "Brightness +",
    "screenshot": "Screenshot",
    "app_switch": "Switch app",
}
_CONFIRM_TARGETS = ("screenshot", "app_switch")


class MediaGridView(ScreenOverlay):
    """The Media/System grid: ten big targets with a label and a simple glyph each. The target
    pointed at is outlined; one waiting for its second pinch says "Pinch again to confirm"."""

    def __init__(self) -> None:
        super().__init__()
        self.highlight = ""
        self.pending = ""

    def show_grid(self, highlight: str, pending: str) -> None:
        self.highlight, self.pending = highlight, pending
        self.present()

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 70))
        for ident, rect in layout.MEDIA_TARGETS:
            box = self.box(rect)
            waiting = ident == self.pending
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(PANEL_BLUE if waiting else PANEL_DARK)
            p.drawRoundedRect(box, 16, 16)
            if ident == self.highlight or waiting:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(RING_WHITE, 5))
                p.drawRoundedRect(box.adjusted(-3, -3, 3, 3), 18, 18)
            self._glyph(p, ident, box)
            p.setPen(TEXT_LIGHT)
            p.setFont(self.font_px(0.026, bold=True))
            text = "Pinch again to confirm" if waiting else MEDIA_LABELS[ident]
            if waiting:
                p.setFont(self.font_px(0.02, bold=True))
            p.drawText(
                box.adjusted(4, 0, -4, -8),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                text,
            )
        self.draw_footer(p, layout.MEDIA_TARGETS, "Point and pinch · Fist to cancel")

    def _glyph(self, p: QPainter, ident: str, box: QRectF) -> None:
        """A simple shape above the label; targets without a shape get a big symbol."""
        cx, cy, s = box.center().x(), box.top() + box.height() * 0.36, box.height() * 0.17
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(TEXT_LIGHT)
        if ident == "play_pause":
            p.drawPolygon([QPointF(cx - s, cy - s), QPointF(cx - s, cy + s), QPointF(cx, cy)])
            p.drawRect(QRectF(cx + s * 0.2, cy - s, s * 0.35, s * 2))
            p.drawRect(QRectF(cx + s * 0.8, cy - s, s * 0.35, s * 2))
        elif ident == "prev_track":
            p.drawRect(QRectF(cx - s, cy - s, s * 0.3, s * 2))
            p.drawPolygon(
                [QPointF(cx + s, cy - s), QPointF(cx + s, cy + s), QPointF(cx - s * 0.6, cy)]
            )
        elif ident == "next_track":
            p.drawRect(QRectF(cx + s * 0.7, cy - s, s * 0.3, s * 2))
            p.drawPolygon(
                [QPointF(cx - s, cy - s), QPointF(cx - s, cy + s), QPointF(cx + s * 0.6, cy)]
            )
        else:
            symbol = {
                "volume_down": "−",
                "volume_up": "+",
                "brightness_down": "−",
                "brightness_up": "+",
                "mute": "×",
                "screenshot": "▣",
                "app_switch": "⇄",
            }[ident]
            p.setPen(TEXT_LIGHT)
            p.setFont(self.font_px(0.05, bold=True))
            p.drawText(
                QRectF(box.left(), box.top(), box.width(), box.height() * 0.65),
                Qt.AlignmentFlag.AlignCenter,
                symbol,
            )
