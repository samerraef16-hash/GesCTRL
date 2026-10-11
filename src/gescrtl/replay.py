"""Replay a recorded session through the core: ``python -m gescrtl.replay FILE``.

No camera, no Qt and no OS input: the file's landmark frames and commands go to ``Engine`` and
every event it produces is printed as ``t_ms<TAB>EventRepr`` followed by a count per event type.
Output depends only on the file and the settings, so two runs print the same thing (FR-029).

``--slice START END`` keeps the part between two times (ms from the first item). With
``--out FILE`` it writes that part as a new recording, ready to become a test fixture. A slice
starts with a RESUME command because the engine always starts Paused.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from gescrtl.core.config import CoreConfig
from gescrtl.core.engine import Engine
from gescrtl.core.types import Command, CommandRecord, Event, HandFrame
from gescrtl.recording import jsonl

Item = HandFrame | CommandRecord


def load_config(path: Path | None) -> CoreConfig:
    """CoreConfig defaults, overridden by a JSON object of CoreConfig field names."""
    cfg = CoreConfig()
    if path is None:
        return cfg
    data = json.loads(path.read_text(encoding="utf-8"))
    known = {f.name for f in dataclasses.fields(CoreConfig)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ValueError(f"unknown settings: {', '.join(unknown)}")
    return dataclasses.replace(cfg, **data)


def replay(
    items: Iterable[Item], cfg: CoreConfig | None = None, resume: bool = False
) -> list[tuple[int, Event]]:
    """Feed ``items`` to a fresh engine. Returns (t_ns, event) in order.

    ``resume`` starts the engine as if the user had already resumed it.
    """
    engine = Engine(cfg)
    out: list[tuple[int, Event]] = [(0, e) for e in engine.start()]
    first = True
    for it in items:
        if first and resume:
            out += [(it.t_ns, e) for e in engine.command(Command.RESUME, it.t_ns)]
        first = False
        if isinstance(it, CommandRecord):
            out += [(it.t_ns, e) for e in engine.command(it.cmd, it.t_ns, it.arg)]
        else:
            out += [(it.t_ns, e) for e in engine.step(it, it.t_ns)]
    return out


def slice_items(items: list[Item], start_ms: float, end_ms: float) -> list[Item]:
    if not items:
        return []
    t0 = items[0].t_ns
    lo, hi = t0 + round(start_ms * 1e6), t0 + round(end_ms * 1e6)
    return [it for it in items if lo <= it.t_ns <= hi]


def write_slice(src: Path, items: list[Item], dest: Path) -> None:
    header = jsonl.read_header(src)
    cam = header.get("camera", {})
    with jsonl.RecordingWriter(
        dest,
        scenario=str(header.get("scenario", "")) + " (slice)",
        width=int(cam.get("width", 640)),
        height=int(cam.get("height", 480)),
        fps=int(cam.get("fps_requested", 30)),
    ) as w:
        if items:
            w.command(items[0].t_ns, Command.RESUME)
        for it in items:
            if isinstance(it, CommandRecord):
                w.command(it.t_ns, it.cmd, it.arg)
            else:
                w.frame(it)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gescrtl.replay", description=__doc__.split("\n\n")[0])
    ap.add_argument("file", type=Path)
    ap.add_argument("--settings", type=Path, help="JSON of CoreConfig fields to override")
    ap.add_argument("--resume", action="store_true", help="start already resumed (Active)")
    ap.add_argument("--slice", nargs=2, type=float, metavar=("START_MS", "END_MS"))
    ap.add_argument("--out", type=Path, help="with --slice: write the slice as a recording")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    items = list(jsonl.read(args.file))
    if args.slice:
        items = slice_items(items, *args.slice)
    if args.out:
        if not args.slice:
            ap.error("--out needs --slice")
        write_slice(args.file, items, args.out)
        print(f"wrote {len(items)} items to {args.out}")
        return 0

    t0 = items[0].t_ns if items else 0
    result = replay(items, load_config(args.settings), resume=args.resume)
    counts: Counter[str] = Counter()
    for t_ns, event in result:
        counts[type(event).__name__] += 1
        print(f"{max(0, t_ns - t0) // 1_000_000}\t{event!r}")
    print("--")
    for name, n in sorted(counts.items()):
        print(f"{name}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
