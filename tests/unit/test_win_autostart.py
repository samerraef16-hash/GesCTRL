"""Start with Windows: one value under the current user's Run key, off by default (D5)."""

from pathlib import Path

from gescrtl.platform import win_autostart as auto


class FakeRegistry:
    def __init__(self, value=None, fail=False):
        self.value, self.fail = value, fail

    def get(self):
        return self.value

    def set(self, command):
        if self.fail:
            raise OSError("denied")
        self.value = command

    def delete(self):
        if self.fail:
            raise OSError("denied")
        self.value = None


def test_it_is_off_by_default():
    assert auto.is_enabled(FakeRegistry()) is False


def test_turning_it_on_writes_a_quoted_command_that_starts_the_package():
    reg = FakeRegistry()
    assert auto.set_enabled(True, reg, python="C:/Program Files/Python312/python.exe") is True
    assert reg.value is not None and reg.value.endswith(" -m gescrtl")
    assert reg.value.startswith('"') and "python" in reg.value.lower()
    assert auto.is_enabled(reg) is True


def test_turning_it_off_removes_the_value_and_is_safe_twice():
    reg = FakeRegistry('"x" -m gescrtl')
    assert auto.set_enabled(False, reg) is True and reg.value is None
    assert auto.set_enabled(False, reg) is True


def test_a_refusal_is_reported_instead_of_raised():
    assert auto.set_enabled(True, FakeRegistry(fail=True)) is False
    assert auto.set_enabled(False, FakeRegistry("x", fail=True)) is False


def test_the_windowless_interpreter_is_used_when_it_exists(tmp_path: Path):
    (tmp_path / "python.exe").write_text("")
    (tmp_path / "pythonw.exe").write_text("")
    assert auto.command_line(str(tmp_path / "python.exe")).startswith(
        f'"{tmp_path / "pythonw.exe"}"'
    )
    other = tmp_path / "sub"
    other.mkdir()
    (other / "python.exe").write_text("")
    assert "pythonw" not in auto.command_line(str(other / "python.exe"))


def test_the_app_still_starts_paused_whatever_the_setting():
    from gescrtl.core.engine import Engine
    from gescrtl.core.types import State

    assert Engine().state is State.PAUSED  # sign-in never starts sending input (constitution I)
