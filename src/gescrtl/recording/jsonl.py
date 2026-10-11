"""Landmark session recording: timestamped JSONL, landmarks only, never images (plan D16).

Format version 2 = the Phase 0 (v1) header and frame lines plus ``{"type": "command", ...}``
lines, so hotkeys, tray actions and camera events replay too. The reader accepts v1 and v2.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, TextIO

from gescrtl.core.types import (
    DEFAULT_ASPECT,
    Command,
    CommandRecord,
    Hand,
    HandFrame,
    Landmark,
)

FORMAT_VERSION = 2


def _round(v: float) -> float:
    return round(v, 5)


class RecordingWriter:
    def __init__(
        self,
        path: Path,
        scenario: str = "",
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        tracker: str = "mediapipe-hand-landmarker",
    ) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh: TextIO = path.open("w", encoding="utf-8", newline="\n")
        self._write(
            {
                "type": "header",
                "format_version": FORMAT_VERSION,
                "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tracker": {"name": tracker},
                "camera": {"width": width, "height": height, "fps_requested": fps},
                "mirrored": True,
                "scenario": scenario,
            }
        )

    def _write(self, obj: dict[str, Any]) -> None:
        self._fh.write(json.dumps(obj, separators=(",", ":")) + "\n")

    def frame(self, frame: HandFrame) -> None:
        self._write(
            {
                "type": "frame",
                "t_ns": frame.t_ns,
                "hands": [
                    {
                        "handedness": h.handedness,
                        "handedness_score": _round(h.score),
                        "landmarks": [[_round(p.x), _round(p.y), _round(p.z)] for p in h.landmarks],
                    }
                    for h in frame.hands
                ],
            }
        )

    def command(self, t_ns: int, cmd: Command, arg: str = "") -> None:
        self._write({"type": "command", "t_ns": t_ns, "cmd": cmd.name, "arg": arg})
        self._fh.flush()  # commands are rare: keep them on disk even if the app is killed

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> RecordingWriter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def read_header(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                obj = json.loads(line)
                return obj if obj.get("type") == "header" else {}
    return {}


def read(path: Path) -> Iterator[HandFrame | CommandRecord]:
    """Yield frames and commands in file order. Unknown line types are skipped."""
    header = read_header(path)
    cam = header.get("camera", {})
    width, height = cam.get("width"), cam.get("height")
    aspect = width / height if width and height else DEFAULT_ASPECT
    flip = header.get("mirrored", True) is False  # we store/consume user-view (mirrored) x
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            kind = obj.get("type")
            if kind == "frame":
                hands = tuple(_hand(h, flip) for h in obj.get("hands", []))
                yield HandFrame(t_ns=int(obj["t_ns"]), hands=hands, aspect=aspect)
            elif kind == "command":
                yield CommandRecord(
                    t_ns=int(obj["t_ns"]), cmd=Command[obj["cmd"]], arg=obj.get("arg", "")
                )


def _hand(h: dict[str, Any], flip: bool) -> Hand:
    lms = tuple(
        Landmark(1.0 - p[0] if flip else p[0], p[1], p[2] if len(p) > 2 else 0.0)
        for p in h["landmarks"]
    )
    return Hand(
        landmarks=lms,
        handedness=h.get("handedness", ""),
        score=float(h.get("handedness_score", h.get("score", 1.0))),
    )
