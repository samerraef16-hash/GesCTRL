"""Overlay widgets: the pointing ring, the presentation laser, the mode menu, level panel, media
grid (spec 003 plan D11), and the on-screen keyboard and setup guide (spec 004 D11).

Every window is frameless, always on top, click-through, and never takes focus, exactly like the
spec 002 cursor cue. All methods must run on the Qt main thread; ``UiBridge`` in app.py marshals
core events here. None of these windows ever shows camera imagery.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from gescrtl.core import layout
from gescrtl.core.mode_menu import MODE_BY_ITEM
from gescrtl.core.types import KeyboardView, Level, Mode, SetupView
from gescrtl.platform import displays
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
        """The overlay monitor (the one chosen in Settings, else the primary), in the
        device-independent pixels Qt places windows in."""
        screen = displays.overlay_screen()
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
    """The mode menu: four big items in a row (feedback-hud.md). The current mode is filled and
    the one pointed at is outlined."""

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
            fill = PANEL_BLUE if ident == current_item else PANEL_DARK
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(box, 18, 18)
            if ident == self.highlight:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(RING_WHITE, 5))
                p.drawRoundedRect(box.adjusted(-3, -3, 3, 3), 20, 20)
            p.setFont(self.font_px(0.034, bold=True))
            p.setPen(TEXT_LIGHT)
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, MENU_LABELS[ident])
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
        for ident, rect in layout.LEVEL_STEP_TARGETS:
            box = self.box(rect)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(PANEL_DARK)
            p.drawRoundedRect(box, 16, 16)
            if ident == self.highlight:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(RING_WHITE, 5))
                p.drawRoundedRect(box.adjusted(-3, -3, 3, 3), 18, 18)
            p.setPen(TEXT_LIGHT)
            p.setFont(self.font_px(0.05, bold=True))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, "+" if ident.endswith("_up") else "−")
        self.draw_footer(p, layout.LEVEL_STEP_TARGETS, "Pinch and move, or point at + / −")


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
        self.labels: dict[str, str] = {}

    def show_grid(
        self, highlight: str, pending: str, labels: tuple[tuple[str, str], ...] = ()
    ) -> None:
        self.highlight, self.pending = highlight, pending
        self.labels = dict(labels)
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
            text = (
                "Pinch again to confirm" if waiting else self.labels.get(ident, MEDIA_LABELS[ident])
            )
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


# -- spec 004: the on-screen keyboard and the setup guide --------------------------------------

KEY_FILL = QColor(40, 40, 48, 235)
KEY_HIGHLIGHT = QColor(70, 70, 84, 245)
KEY_PRESSED = QColor(46, 160, 90, 250)
KEY_LOCKED = QColor(40, 110, 220, 250)

_KEY_LABELS = {
    "k:backspace": "⌫",
    "k:enter": "↵",
    "k:tab": "Tab",
    "k:space": "Space",
    "k:left": "←",
    "k:up": "↑",
    "k:down": "↓",
    "k:right": "→",
    "s:copy": "Copy",
    "s:paste": "Paste",
    "s:cut": "Cut",
    "s:undo": "Undo",
    "s:redo": "Redo",
    "s:select_all": "All",
    "s:alt_tab": "Alt+Tab",
    "s:win": "Win",
    "s:esc": "Esc",
    "move": "⇅ Move",
    "m:shift": "Shift",
    "m:ctrl": "Ctrl",
    "m:alt": "Alt",
    "m:win": "Win",
}
_SHIFTED = {
    **{c: c.upper() for c in "abcdefghijklmnopqrstuvwxyz"},
    **dict(zip("1234567890-;',./", '!@#$%^&*()_:"<>?', strict=True)),
}


def key_label(ident: str, shifted: bool = False) -> str:
    """The text on a key. With Shift active, letters show as capitals and symbols as shifted."""
    if ident in _KEY_LABELS:
        return _KEY_LABELS[ident]
    char = ident.partition(":")[2]
    return _SHIFTED.get(char, char) if shifted else char


class KeyboardOverlay(ScreenOverlay):
    """The on-screen keyboard: keys from the shared layout, the key pointed at highlighted, a
    flash on the key just pressed, one-shot modifiers outlined and locked ones filled, a ring
    that fills while dwelling, and a strip with the last characters sent."""

    def __init__(self) -> None:
        super().__init__()
        self.view = KeyboardView()

    def show_view(self, view: KeyboardView) -> None:
        self.view = view
        self.present()

    def paintEvent(self, _event: object) -> None:
        v = self.view
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = layout.keyboard_rect(v.position)
        board = self.box(layout.Rect(rect.x - 0.01, rect.y - 0.012, rect.w + 0.02, rect.h + 0.024))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(18, 18, 24, 200))
        p.drawRoundedRect(board, 18, 18)
        shifted = "shift" in v.oneshot or "shift" in v.locked
        for ident, key in layout.keyboard_keys(v.position):
            box = self.box(key)
            modifier = ident.partition(":")[2] if ident.startswith("m:") else ""
            locked = bool(modifier) and modifier in v.locked
            armed = bool(modifier) and modifier in v.oneshot
            fill = KEY_FILL
            pointed = ident == v.highlight or (bool(v.highlight2) and ident == v.highlight2)
            if pointed:
                fill = KEY_HIGHLIGHT
            if locked:
                fill = KEY_LOCKED
            if ident == v.pressed:
                fill = KEY_PRESSED
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(box, 10, 10)
            if pointed or armed:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(PANEL_BLUE if armed else RING_WHITE, 4))
                p.drawRoundedRect(box.adjusted(-2, -2, 2, 2), 12, 12)
            if pointed and v.dwell > 0:
                p.setPen(QPen(RING_GREEN, 5))
                p.drawArc(box.adjusted(6, 6, -6, -6).toRect(), 90 * 16, -round(360 * 16 * v.dwell))
            p.setPen(TEXT_LIGHT)
            p.setFont(self.font_px(0.026, bold=True))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, key_label(ident, shifted))
        strip_h = 0.06
        strip_y = rect.y - strip_h - 0.02 if v.position == "bottom" else rect.y + rect.h + 0.02
        strip = self.box(layout.Rect(rect.x, strip_y, rect.w, strip_h))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(18, 18, 24, 215))
        p.drawRoundedRect(strip, 12, 12)
        p.setPen(TEXT_LIGHT if v.recent else TEXT_DIM)
        p.setFont(self.font_px(0.034))
        text = v.recent or "Typed text appears here"
        p.drawText(strip.adjusted(16, 0, -16, 0), Qt.AlignmentFlag.AlignVCenter, text)


class SetupOverlay(ScreenOverlay):
    """Guides calibration and gesture enrollment: what to do now, a progress bar, and the screen
    corner to point at during the reach step."""

    def __init__(self) -> None:
        super().__init__()
        self.view = SetupView("", "", 0.0)

    def show_view(self, view: SetupView) -> None:
        self.view = view
        self.present()

    def paintEvent(self, _event: object) -> None:
        v = self.view
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 90))
        w, h = self.width(), self.height()
        if v.target is not None:
            tx = 0.04 * w + v.target[0] * 0.92 * w
            ty = 0.06 * h + v.target[1] * 0.88 * h
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(RING_GREEN, 6))
            p.drawEllipse(QPointF(tx, ty), 34, 34)
            p.setPen(QPen(RING_WHITE, 3))
            p.drawEllipse(QPointF(tx, ty), 12, 12)
        box = QRectF(w * 0.2, h * 0.38, w * 0.6, h * 0.2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(PANEL_DARK)
        p.drawRoundedRect(box, 20, 20)
        p.setPen(TEXT_LIGHT)
        p.setFont(self.font_px(0.032, bold=True))
        p.drawText(
            box.adjusted(24, 14, -24, -50),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            v.text,
        )
        bar = QRectF(box.left() + 40, box.bottom() - 34, box.width() - 80, 12)
        p.setBrush(QColor(255, 255, 255, 50))
        p.drawRoundedRect(bar, 6, 6)
        p.setBrush(PANEL_BLUE)
        fraction = min(max(v.progress, 0.0), 1.0)
        p.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * fraction, 12), 6, 6)
