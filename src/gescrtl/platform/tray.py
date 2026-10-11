"""System tray icon and menu (FR-023). Must run on the Qt main thread."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from gescrtl.core.types import Command, Event, State, StateChanged, Warning


def _icon(on: bool) -> QIcon:
    pm = QPixmap(32, 32)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if on:
        p.setBrush(QColor(46, 160, 90))
        p.setPen(Qt.PenStyle.NoPen)
    else:
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QColor(140, 140, 150))
    p.drawEllipse(4, 4, 24, 24)
    p.end()
    return QIcon(pm)


class Tray(QObject):
    def __init__(
        self,
        on_command: Callable[[Command], None],
        on_reload: Callable[[], None],
        on_reset: Callable[[], None],
        on_exit: Callable[[], None],
        on_preview: Callable[[bool], None] = lambda _on: None,
    ) -> None:
        super().__init__()
        self._on_command = on_command
        self._icon_on, self._icon_off = _icon(True), _icon(False)
        self._tray = QSystemTrayIcon(self._icon_on)
        menu = QMenu()
        self._pause_action = QAction("Resume", menu)
        self._pause_action.triggered.connect(lambda: on_command(Command.TOGGLE_PAUSE))
        self._power_action = QAction("Turn off", menu)
        self._power_action.triggered.connect(lambda: on_command(Command.TOGGLE_POWER))
        self._preview_action = QAction("Show camera preview", menu)
        self._preview_action.setCheckable(True)
        self._preview_action.toggled.connect(lambda on: on_preview(on))
        reload_action = QAction("Reload settings", menu)
        reload_action.triggered.connect(lambda: on_reload())
        reset_action = QAction("Reset to defaults", menu)
        reset_action.triggered.connect(lambda: on_reset())
        exit_action = QAction("Exit", menu)
        exit_action.triggered.connect(lambda: on_exit())
        for action in (self._pause_action, self._power_action):
            menu.addAction(action)
        menu.addSeparator()
        menu.addAction(self._preview_action)
        menu.addAction(reload_action)
        menu.addAction(reset_action)
        menu.addSeparator()
        menu.addAction(exit_action)
        self._menu = menu  # keep a reference
        self._tray.setContextMenu(menu)
        self._tray.setToolTip("GesCRTL: Paused")
        self._tray.show()

    def handle(self, event: Event) -> None:
        if isinstance(event, StateChanged):
            off = event.state is State.INACTIVE
            self._tray.setIcon(self._icon_off if off else self._icon_on)
            self._pause_action.setEnabled(not off)
            self._pause_action.setText("Resume" if event.state is State.PAUSED else "Pause")
            self._power_action.setText("Turn on" if off else "Turn off")
            self._tray.setToolTip("GesCRTL: Off" if off else f"GesCRTL: {event.hud_text}")
        elif isinstance(event, Warning):
            self.notify(event.text)

    def set_preview_checked(self, on: bool) -> None:
        self._preview_action.blockSignals(True)
        self._preview_action.setChecked(on)
        self._preview_action.blockSignals(False)

    def notify(self, text: str, warning: bool = True) -> None:
        icon = (
            QSystemTrayIcon.MessageIcon.Warning
            if warning
            else QSystemTrayIcon.MessageIcon.Information
        )
        self._tray.showMessage("GesCRTL", text, icon, 6000)

    def close(self) -> None:
        self._tray.hide()
