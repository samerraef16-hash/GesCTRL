"""WinLevels with fake devices: coalescing, clamping, and the unavailable path (no COM needed)."""

import threading
import time

from gescrtl.core.types import Level
from gescrtl.platform.levels import WinLevels


class FakeDevice:
    def __init__(self, value: int, gate: threading.Event | None = None) -> None:
        self.value = value
        self.sets: list[int] = []
        self.gate = gate

    def get(self) -> int:
        return self.value

    def set(self, percent: int) -> None:
        if self.gate is not None:
            self.gate.wait(2)
        self.value = percent
        self.sets.append(percent)


def broken():
    raise RuntimeError("no such device")


def wait_for(cond, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.005)
    return False


def make(volume=None, brightness=None):
    readings: list = []
    levels = WinLevels(
        on_level=lambda level, value: readings.append((level, value)),
        volume_factory=(lambda: volume) if volume is not None else broken,
        brightness_factory=(lambda: brightness) if brightness is not None else broken,
    )
    return levels, readings


def test_levels_are_read_once_at_start_and_after_each_applied_step():
    vol, br = FakeDevice(40), FakeDevice(70)
    levels, readings = make(vol, br)
    try:
        assert wait_for(lambda: len(readings) >= 2)
        assert (Level.VOLUME, 40) in readings and (Level.BRIGHTNESS, 70) in readings
        levels.step(Level.VOLUME, 2)
        assert wait_for(lambda: vol.sets == [42])
        assert wait_for(lambda: levels.read(Level.VOLUME) == 42)
        assert (Level.VOLUME, 42) in readings and br.sets == []
    finally:
        levels.stop()


def test_steps_that_arrive_while_busy_are_coalesced():
    gate = threading.Event()
    vol = FakeDevice(10, gate)
    levels, _ = make(vol, FakeDevice(50))
    try:
        assert wait_for(lambda: levels.read(Level.VOLUME) == 10)
        levels.step(Level.VOLUME, 2)  # picked up at once and held at the gate
        time.sleep(0.05)
        for _ in range(5):
            levels.step(Level.VOLUME, 2)  # these pile up behind it
        gate.set()
        assert wait_for(lambda: levels.read(Level.VOLUME) == 22)
        assert vol.sets == [12, 22]
    finally:
        levels.stop()


def test_levels_are_clamped_to_0_and_100():
    vol = FakeDevice(99)
    levels, _ = make(vol, FakeDevice(1))
    try:
        assert wait_for(lambda: levels.read(Level.VOLUME) == 99)
        levels.step(Level.VOLUME, 10)
        levels.step(Level.BRIGHTNESS, -10)
        assert wait_for(lambda: levels.read(Level.VOLUME) == 100)
        assert wait_for(lambda: levels.read(Level.BRIGHTNESS) == 0)
    finally:
        levels.stop()


def test_a_missing_device_is_unavailable_and_never_raises():
    levels, readings = make(volume=FakeDevice(30), brightness=None)
    try:
        assert wait_for(lambda: len(readings) >= 2)
        assert (Level.BRIGHTNESS, None) in readings and levels.read(Level.BRIGHTNESS) is None
        levels.step(Level.BRIGHTNESS, 2)  # still fine
        levels.step(Level.VOLUME, 2)
        assert wait_for(lambda: levels.read(Level.VOLUME) == 32)
    finally:
        levels.stop()


def test_a_device_that_fails_while_setting_becomes_unavailable():
    class Failing(FakeDevice):
        def set(self, percent: int) -> None:
            raise OSError("device removed")

    levels, readings = make(Failing(20), FakeDevice(50))
    try:
        assert wait_for(lambda: levels.read(Level.VOLUME) == 20)
        levels.step(Level.VOLUME, 2)
        assert wait_for(lambda: (Level.VOLUME, None) in readings)
    finally:
        levels.stop()
