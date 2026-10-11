"""Guards for constitution IV (pure core), VI (privacy) and VII (platform isolation)."""

import ast
import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "src" / "gescrtl"
CORE_BANNED = {"cv2", "mediapipe", "PySide6", "ctypes", "time", "socket", "datetime"}
CORE_BANNED_INTERNAL = ("gescrtl.platform", "gescrtl.tracking", "gescrtl.recording")


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_core_is_pure():
    offenders = []
    for path in (SRC / "core").rglob("*.py"):
        for name in _imports(path):
            top = name.split(".")[0]
            if top in CORE_BANNED or name.startswith(CORE_BANNED_INTERNAL):
                offenders.append(f"{path.name}: {name}")
    assert not offenders, offenders


def test_no_image_writing_or_network_in_src():
    pattern = re.compile(r"imwrite|\.save\(|socket|urllib|requests|http\.client|urlopen")
    offenders = []
    for path in SRC.rglob("*.py"):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line) and "noqa: arch" not in line:
                offenders.append(f"{path.relative_to(SRC)}:{i}: {line.strip()}")
    assert not offenders, offenders
