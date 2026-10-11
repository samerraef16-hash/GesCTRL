"""Click-accuracy target page for SC-005: ``python -m gescrtl.tools.targets``.

Shows one target at a time (24, 48 or 96 px) and asks for a left click, double click or right
click. The first attempt on a target counts: a hit needs the right action inside the target.
Results go to ``recordings/<timestamp>_targets.csv`` (numbers only) and a summary per size is
shown at the end. Esc quits. Run it next to the app, using gestures instead of the mouse.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget

SIZES = (24, 48, 96)
ACTIONS = ("left", "double", "right")
LABELS = {"left": "Click", "double": "Double-click", "right": "Right-click"}
COLOURS = {
    "left": QColor(70, 170, 255),
    "double": QColor(255, 190, 60),
    "right": QColor(230, 90, 120),
}


@dataclass(frozen=True, slots=True)
class Trial:
    index: int
    size: int
    action: str
    hit: bool
    offset_px: float  # distance from the target centre
    ms: int  # time from showing the target to the first press


def summarize(trials: list[Trial]) -> dict[int, tuple[int, int]]:
    """{size: (hits, attempts)}."""
    out: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for t in trials:
        out[t.size][0] += int(t.hit)
        out[t.size][1] += 1
    return {size: (h, n) for size, (h, n) in sorted(out.items())}


def summary_lines(trials: list[Trial]) -> list[str]:
    lines = []
    for size, (h, n) in summarize(trials).items():
        lines.append(f"{size:>3} px: {h}/{n} hit ({100 * h / n:.0f}%)")
    for action in ACTIONS:
        sub = [t for t in trials if t.action == action]
        if sub:
            lines.append(f"{action:>6}: {sum(t.hit for t in sub)}/{len(sub)} hit")
    return lines


def write_csv(trials: list[Trial], folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{time.strftime('%Y%m%d-%H%M%S')}_targets.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["trial", "size_px", "action", "hit", "offset_px", "ms"])
        for t in trials:
            w.writerow([t.index, t.size, t.action, int(t.hit), f"{t.offset_px:.1f}", t.ms])
    return path


class TargetWindow(QWidget):
    def __init__(self, trials: int, out_dir: Path, seed: int | None = None) -> None:
        super().__init__()
        self.setWindowTitle("GesCRTL targets")
        self.setStyleSheet("background-color: #16161c;")
        self._total = trials
        self._out_dir = out_dir
        self._rng = random.Random(seed)
        self.results: list[Trial] = []
        self.csv_path: Path | None = None
        self._size = 48
        self._action = "left"
        self._center = QPointF(200, 200)
        self._shown = time.monotonic()
        self._pending: tuple[QPointF, int] | None = None  # first press of a possible double
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._double_timeout)
        self._done = False
        self.next_target()

    # -- trials --------------------------------------------------------------------------------

    def next_target(self) -> None:
        if len(self.results) >= self._total:
            self._finish()
            return
        self._size = self._rng.choice(SIZES)
        self._action = self._rng.choice(ACTIONS)
        m = 80 + self._size
        self._center = QPointF(
            self._rng.uniform(m, max(m + 1, self.width() - m)),
            self._rng.uniform(m + 40, max(m + 41, self.height() - m)),
        )
        self._shown = time.monotonic()
        self.update()

    def _record(self, pos: QPointF, ms: int, correct_action: bool) -> None:
        dx, dy = pos.x() - self._center.x(), pos.y() - self._center.y()
        inside = abs(dx) <= self._size / 2 and abs(dy) <= self._size / 2
        trial = Trial(
            len(self.results) + 1,
            self._size,
            self._action,
            inside and correct_action,
            (dx * dx + dy * dy) ** 0.5,
            ms,
        )
        self.results.append(trial)
        self.next_target()

    def _finish(self) -> None:
        self._done = True
        self.csv_path = write_csv(self.results, self._out_dir)
        self.update()

    def _double_timeout(self) -> None:  # only one press came: not a double click
        if self._pending is not None:
            pos, ms = self._pending
            self._pending = None
            self._record(pos, ms, correct_action=False)

    # -- events --------------------------------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if not self._done:
                self._finish()
            self.close()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._done:
            return
        ms = round((time.monotonic() - self._shown) * 1000)
        pos = event.position()
        if event.button() == Qt.MouseButton.RightButton:
            self._record(pos, ms, self._action == "right")
        elif event.button() == Qt.MouseButton.LeftButton:
            if self._action == "double":
                self._pending = (pos, ms)
                self._timer.start(QApplication.doubleClickInterval() + 150)
            else:
                self._record(pos, ms, self._action == "left")

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._done or self._pending is None or event.button() != Qt.MouseButton.LeftButton:
            return
        pos, ms = self._pending
        self._pending = None
        self._timer.stop()
        self._record(pos, ms, correct_action=True)

    # -- painting ------------------------------------------------------------------------------

    def paintEvent(self, _event: object) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(22, 22, 28))
        p.setPen(QColor(220, 220, 228))
        font = QFont()
        font.setPointSize(14)
        p.setFont(font)
        if self._done:
            lines = ["Done. Esc closes.", "", *summary_lines(self.results)]
            if self.csv_path is not None:
                lines += ["", f"Saved {self.csv_path}"]
            area = self.rect().adjusted(60, 60, -60, -60)
            p.drawText(area, Qt.AlignmentFlag.AlignLeft, "\n".join(lines))
            return
        head = f"{LABELS[self._action]}   ({len(self.results) + 1}/{self._total})   Esc to stop"
        p.drawText(QRectF(0, 12, self.width(), 30), Qt.AlignmentFlag.AlignHCenter, head)
        half = self._size / 2
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.setBrush(COLOURS[self._action])
        p.drawRect(QRectF(self._center.x() - half, self._center.y() - half, self._size, self._size))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gescrtl.tools.targets", description=__doc__)
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--out", type=Path, default=Path("recordings"))
    args = ap.parse_args(argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    win = TargetWindow(args.trials, args.out)
    win.showFullScreen()
    code = app.exec()
    for line in summary_lines(win.results):
        print(line)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
