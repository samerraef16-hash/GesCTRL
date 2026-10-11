"""Opt-in camera preview: a mirrored live view with the tracked hand drawn on top.

For framing the camera and checking gestures. Frames are only shown on screen: nothing is
written to disk or sent anywhere (constitution VI). Must run on the Qt main thread.

Keys: S toggles the skeleton and cursor-area box (clean view for screen recordings),
D toggles the pose readout.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gescrtl.core.engine import DebugInfo
from gescrtl.core.features import (
    FLAT_EXTENDED_MIN,
    FLAT_PINCH_CLEAR,
    FLAT_THUMB_MAX,
    FLAT_UPRIGHT_MAX_DEG,
    THUMB_OUT_MIN,
)
from gescrtl.core.types import Hand, HandFrame, Pose

HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
)  # fmt: skip

POSE_LABELS = {
    Pose.NONE: "-",
    Pose.G1_RELAXED: "relaxed (move)",
    Pose.G2_PINCH_INDEX: "pinch index (click / drag)",
    Pose.G3_PINCH_MIDDLE: "pinch middle (right click)",
    Pose.G4_THUMBS_UP: "thumb out (scroll: tilt thumb)",
    Pose.G5_FIST: "fist (cursor frozen)",
    Pose.G6_OPEN_PALM: "open palm (resume)",
    Pose.G7_THREE_FINGERS: "three fingers (no action)",
    Pose.G8_FLAT_HAND: "flat hand (hold cursor; 1.5 s = pause)",
}


class PreviewWindow(QWidget):
    closed = Signal()

    def __init__(self, region: float = 0.6) -> None:
        super().__init__(None, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("GesCRTL camera preview (not recorded)")
        self.setMinimumSize(320, 300)
        self.resize(680, 620)
        self.setStyleSheet("background-color: #101014;")
        self._region = region
        self._image: QImage | None = None
        self._hands: tuple[Hand, ...] = ()
        self._debug: DebugInfo | None = None
        self._fps = 0.0
        self._status = "Paused"
        self._camera_off = False
        self._skeleton = True
        self._readout = True

    # -- data in -----------------------------------------------------------------------------

    def set_region(self, region: float) -> None:
        self._region = region
        self.update()

    def set_status(self, text: str) -> None:
        self._status = text
        self.update()

    def set_camera_off(self, off: bool) -> None:
        self._camera_off = off
        if off:
            self._image = None
            self._hands = ()
            self._debug = None
        self.update()

    def set_frame(
        self, image: QImage, frame: HandFrame | None, debug: DebugInfo | None, fps: float
    ) -> None:
        self._image = image
        self._hands = frame.hands if frame is not None else ()
        self._debug = debug
        self._fps = fps
        self._camera_off = False
        self.update()

    # -- window events -----------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_S:
            self._skeleton = not self._skeleton
            self.update()
        elif event.key() == Qt.Key.Key_D:
            self._readout = not self._readout
            self.update()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: object) -> None:
        self.closed.emit()
        super().closeEvent(event)  # type: ignore[arg-type]

    # -- painting ----------------------------------------------------------------------------

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(16, 16, 20))
        strip = 100 if self._readout else 30
        area = QRectF(0, 0, self.width(), max(self.height() - strip, 1))

        if self._image is None:
            msg = "Camera off" if self._camera_off else "Waiting for the camera..."
            p.setPen(QColor(190, 190, 200))
            p.setFont(self._font(14))
            p.drawText(area, Qt.AlignmentFlag.AlignCenter, msg)
        else:
            rect = self._fit(area, self._image.width(), self._image.height())
            p.drawImage(rect, self._image)
            if self._skeleton:
                self._draw_region(p, rect)
                self._draw_hands(p, rect)
            self._draw_badge(p, rect)

        self._draw_footer(p, strip)

    @staticmethod
    def _fit(area: QRectF, w: int, h: int) -> QRectF:
        scale = min(area.width() / w, area.height() / h)
        rw, rh = w * scale, h * scale
        return QRectF(
            area.x() + (area.width() - rw) / 2, area.y() + (area.height() - rh) / 2, rw, rh
        )

    @staticmethod
    def _font(size: int, bold: bool = False) -> QFont:
        f = QFont()
        f.setPointSize(size)
        f.setBold(bold)
        return f

    def _draw_region(self, p: QPainter, rect: QRectF) -> None:
        r = self._region
        box = QRectF(
            rect.x() + rect.width() * (0.5 - r / 2),
            rect.y() + rect.height() * (0.5 - r / 2),
            rect.width() * r,
            rect.height() * r,
        )
        pen = QPen(QColor(255, 210, 60, 220), 2, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(box)
        p.setFont(self._font(9))
        p.drawText(box.adjusted(6, 4, 0, 0), "cursor area: keep your hand inside")

    def _draw_hands(self, p: QPainter, rect: QRectF) -> None:
        primary = self._primary_index()
        for i, hand in enumerate(self._hands):
            main = i == primary
            line = QColor(60, 220, 120) if main else QColor(150, 150, 160, 170)
            dot = QColor(255, 255, 255) if main else QColor(150, 150, 160, 170)
            pts = [
                QPointF(rect.x() + lm.x * rect.width(), rect.y() + lm.y * rect.height())
                for lm in hand.landmarks
            ]
            p.setPen(QPen(line, 3 if main else 2))
            for a, b in HAND_CONNECTIONS:
                p.drawLine(pts[a], pts[b])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dot)
            for pt in pts:
                p.drawEllipse(pt, 3.5, 3.5)
        if primary is not None and self._debug is not None:
            ax, ay = self._debug.anchor
            c = QPointF(rect.x() + ax * rect.width(), rect.y() + ay * rect.height())
            p.setPen(QPen(QColor(255, 80, 80), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(c, 9, 9)  # the point that drives the cursor

    def _primary_index(self) -> int | None:
        if not self._hands or self._debug is None:
            return None
        ax, ay = self._debug.anchor

        def gap(h: Hand) -> float:
            idx = (0, 5, 9, 13, 17)
            cx = sum(h.landmarks[i].x for i in idx) / 5
            cy = sum(h.landmarks[i].y for i in idx) / 5
            return (cx - ax) ** 2 + (cy - ay) ** 2

        return min(range(len(self._hands)), key=lambda i: gap(self._hands[i]))

    def _draw_badge(self, p: QPainter, rect: QRectF) -> None:
        p.setFont(self._font(10, True))
        text = f"{self._status}   {self._fps:.0f} fps"
        w = p.fontMetrics().horizontalAdvance(text) + 20
        box = QRectF(rect.x() + 8, rect.y() + 8, w, 26)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 150))
        p.drawRoundedRect(box, 8, 8)
        p.setPen(QColor(240, 240, 240))
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_footer(self, p: QPainter, strip: int) -> None:
        top = self.height() - strip
        p.setPen(QColor(150, 150, 165))
        p.setFont(self._font(8))
        p.drawText(
            QRectF(8, top + strip - 24, self.width() - 16, 20),
            Qt.AlignmentFlag.AlignVCenter,
            "S: skeleton on/off (clean view for recording)   D: readout on/off   "
            "Not saved or sent anywhere",
        )
        if not self._readout:
            return
        d = self._debug
        p.setFont(self._font(10))
        p.setPen(QColor(235, 235, 240))
        if d is None:
            p.drawText(QRectF(8, top + 4, self.width() - 16, 48), Qt.AlignmentFlag.AlignVCenter,
                       "No hand detected: bring your hand into view")  # fmt: skip
            return
        thumb = "out" if d.thumb_out > THUMB_OUT_MIN else "tucked"
        line1 = f"seen: {POSE_LABELS[d.raw]}     confirmed: {POSE_LABELS[d.stable]}"
        line2 = (
            f"pinch: index {d.pinch_index:.2f}   middle {d.pinch_middle:.2f}   (clicks below 0.25)"
        )
        if d.stable is Pose.G4_THUMBS_UP:
            way = "up" if d.scroll_rate > 0 else "down" if d.scroll_rate < 0 else "none"
            line3 = (
                f"scroll: thumb tilt {d.thumb_tilt_deg:+.0f} deg, "
                f"{d.scroll_rel_deg:+.0f} from where you started  ->  {way} "
                f"{abs(d.scroll_rate):.0f} units/s"
            )
        else:
            fingers = " ".join(f"{c:.2f}" for c in d.curl)
            tip_gap = min(d.pinch_index, d.pinch_middle)
            line3 = (
                f"flat hand needs: fingers {fingers} (all > {FLAT_EXTENDED_MIN}) | "
                f"upright {d.upright_deg:.0f} deg (<= {FLAT_UPRIGHT_MAX_DEG:.0f}) | "
                f"thumb {d.thumb_out:.2f} {thumb} (< {FLAT_THUMB_MAX}) | "
                f"tip gap {tip_gap:.2f} (> {FLAT_PINCH_CLEAR})"
            )
        p.drawText(QRectF(8, top + 2, self.width() - 16, 24), Qt.AlignmentFlag.AlignVCenter, line1)
        p.setFont(self._font(8))
        p.setPen(QColor(190, 190, 205))
        p.drawText(QRectF(8, top + 28, self.width() - 16, 18), Qt.AlignmentFlag.AlignVCenter, line2)
        p.drawText(QRectF(8, top + 46, self.width() - 16, 18), Qt.AlignmentFlag.AlignVCenter, line3)
