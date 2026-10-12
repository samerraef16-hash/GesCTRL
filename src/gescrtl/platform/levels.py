"""System volume and built-in display brightness (plan D10, ADR 0006).

``WinLevels`` runs every COM call on one daemon thread (COM objects belong to the thread that
created them) and coalesces the steps that arrive while it is busy, so a fast drag never queues
up work. Volume uses the Windows Core Audio endpoint (pycaw); brightness uses WMI, which only
exists for built-in displays: on a desktop monitor ``read`` returns None and the panel says
"Brightness unavailable" (FR-024). Nothing here raises into the caller.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Protocol

from gescrtl.core.types import Level

log = logging.getLogger(__name__)


class Device(Protocol):
    """One adjustable level, 0..100. Created and used on the levels thread only."""

    def get(self) -> int: ...

    def set(self, percent: int) -> None: ...


DeviceFactory = Callable[[], Device]


class VolumeDevice:
    def __init__(self) -> None:
        from pycaw.pycaw import AudioUtilities

        self._endpoint = AudioUtilities.GetSpeakers().EndpointVolume

    def get(self) -> int:
        return round(self._endpoint.GetMasterVolumeLevelScalar() * 100)

    def set(self, percent: int) -> None:
        self._endpoint.SetMasterVolumeLevelScalar(max(0, min(100, percent)) / 100, None)


class BrightnessDevice:
    """WMI ``WmiMonitorBrightness`` (read) and ``WmiMonitorBrightnessMethods`` (write)."""

    def __init__(self) -> None:
        import comtypes.client

        self._wmi = comtypes.client.CoGetObject("winmgmts:root\\WMI")
        self.get()  # raises when there is no controllable display

    def get(self) -> int:
        for item in self._wmi.ExecQuery("SELECT CurrentBrightness FROM WmiMonitorBrightness"):
            return int(item.Properties_.Item("CurrentBrightness").Value)
        raise RuntimeError("no display with brightness control")

    def set(self, percent: int) -> None:
        value = max(0, min(100, percent))
        for item in self._wmi.ExecQuery("SELECT * FROM WmiMonitorBrightnessMethods"):
            params = item.Methods_.Item("WmiSetBrightness").InParameters.SpawnInstance_()
            params.Properties_.Item("Timeout").Value = 1
            params.Properties_.Item("Brightness").Value = value
            item.ExecMethod_("WmiSetBrightness", params)
            return
        raise RuntimeError("no display with brightness control")


class WinLevels:
    """``LevelBackend`` for Windows. ``on_level(level, value)`` is called from the levels thread
    once at start and after every applied step; ``value`` is None when the level is unavailable."""

    def __init__(
        self,
        on_level: Callable[[Level, int | None], None] = lambda level, value: None,
        volume_factory: DeviceFactory = VolumeDevice,
        brightness_factory: DeviceFactory = BrightnessDevice,
    ) -> None:
        self._on_level = on_level
        self._factories: dict[Level, DeviceFactory] = {
            Level.VOLUME: volume_factory,
            Level.BRIGHTNESS: brightness_factory,
        }
        self._devices: dict[Level, Device | None] = {}
        self._values: dict[Level, int | None] = {Level.VOLUME: None, Level.BRIGHTNESS: None}
        self._pending: dict[Level, int] = {}
        self._cond = threading.Condition()
        self._stopped = False
        self._thread = threading.Thread(target=self._run, name="levels", daemon=True)
        self._thread.start()

    # -- LevelBackend -----------------------------------------------------------------------

    def step(self, level: Level, delta: int) -> None:
        """Queue a relative change in percentage points. Never blocks."""
        with self._cond:
            self._pending[level] = self._pending.get(level, 0) + delta
            self._cond.notify()

    def read(self, level: Level) -> int | None:
        """The last level the thread saw, or None if it is unavailable."""
        with self._cond:
            return self._values[level]

    def stop(self) -> None:
        with self._cond:
            self._stopped = True
            self._cond.notify()
        self._thread.join(2.0)

    # -- levels thread ----------------------------------------------------------------------

    def _run(self) -> None:
        com = _com_init()
        try:
            for level in self._factories:
                self._refresh(level)
            while True:
                with self._cond:
                    while not self._pending and not self._stopped:
                        self._cond.wait()
                    if self._stopped:
                        return
                    work, self._pending = self._pending, {}
                for level, delta in work.items():
                    self._apply(level, delta)
        finally:
            self._devices.clear()  # release the COM objects before CoUninitialize
            com()

    def _device(self, level: Level) -> Device | None:
        if self._devices.get(level) is None:
            try:
                self._devices[level] = self._factories[level]()
            except Exception:
                log.info("%s control unavailable", level.name.lower(), exc_info=True)
                self._devices[level] = None
        return self._devices[level]

    def _refresh(self, level: Level) -> None:
        device = self._device(level)
        value: int | None = None
        if device is not None:
            try:
                value = device.get()
            except Exception:
                log.exception("reading %s failed", level.name.lower())
                self._devices[level] = None
        self._publish(level, value)

    def _apply(self, level: Level, delta: int) -> None:
        device = self._device(level)
        value: int | None = None
        if device is not None:
            try:
                value = max(0, min(100, device.get() + delta))
                device.set(value)
            except Exception:
                log.exception("setting %s failed", level.name.lower())
                self._devices[level] = None  # reopen next time (the default device may change)
                value = None
        self._publish(level, value)

    def _publish(self, level: Level, value: int | None) -> None:
        with self._cond:
            self._values[level] = value
        try:
            self._on_level(level, value)
        except Exception:
            log.exception("level callback failed")


def _com_init() -> Callable[[], None]:
    """Initialise COM on this thread; returns the matching uninitialise call."""
    try:
        import comtypes

        comtypes.CoInitialize()
        return comtypes.CoUninitialize
    except Exception:
        log.exception("COM initialisation failed")
        return lambda: None
