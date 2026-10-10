"""Optional click-through overlay check for ADR 0003 (THROWAWAY).

Requires `pip install PySide6` (not in requirements.txt). No camera, no input injection.
Shows a small label top-right. Clicks must pass through it and focus must never move to it.
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel


def main() -> int:
    app = QApplication(sys.argv)
    label = QLabel("Click-through test — Ctrl+C in terminal to quit")
    label.setWindowFlags(
        Qt.FramelessWindowHint
        | Qt.WindowStaysOnTopHint
        | Qt.Tool
        | Qt.WindowTransparentForInput
    )
    label.setAttribute(Qt.WA_TranslucentBackground)
    label.setAttribute(Qt.WA_ShowWithoutActivating)
    label.setStyleSheet(
        "background-color: rgba(30,30,30,180); color: white; padding: 8px 14px; border-radius: 10px;"
    )
    label.adjustSize()
    screen = app.primaryScreen().geometry()
    label.move(screen.right() - label.width() - 20, screen.top() + 20)
    label.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
