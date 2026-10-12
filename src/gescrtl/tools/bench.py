"""Benchmarks (FR-032, H4): false triggers from recordings, and live timing and CPU.

``python -m gescrtl.tools.bench --replay "recordings/*idle*.jsonl"``
    Replays each recording through the core and counts consequential events (clicks, drags,
    scrolls, resumes, mode changes, overlays opened, system actions, level steps). The scenario
    comes from the recording's header (the NAME given to ``--record``). A recording of an
    idle/typing/talking/second-person scenario must produce none: otherwise the exit code is 1.

``python -m gescrtl.tools.bench --live 20 [--paused]``
    Runs the real camera and tracker for N seconds with a null input backend (no OS input is
    ever sent) and reports tracking rate, capture-to-done delay and CPU use.
"""

from __future__ import annotations

import argparse
import glob
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from gescrtl.core.types import (
    ButtonDown,
    Click,
    Command,
    Event,
    LevelStep,
    ModeChanged,
    OverlayShown,
    Scroll,
    State,
    StateChanged,
    SystemAction,
)
from gescrtl.recording import jsonl
from gescrtl.replay import replay

# a recording of one of these must cause no consequential event at all
QUIET_SCENARIOS = ("idle", "typing", "talking", "second-person", "second_person")


@dataclass(frozen=True, slots=True)
class ReplayRow:
    file: str
    scenario: str
    seconds: float
    clicks: int
    drags: int
    scrolls: int
    resumes: int
    modes: int = 0  # mode changes
    overlays: int = 0  # mode menu / level panel / media grid shown
    actions: int = 0  # keys sent to the system (slides, media, screenshot, app switch)
    levels: int = 0  # volume / brightness steps

    @property
    def total(self) -> int:
        return (
            self.clicks
            + self.drags
            + self.scrolls
            + self.resumes
            + self.modes
            + self.overlays
            + self.actions
            + self.levels
        )

    @property
    def per_minute(self) -> float:
        return self.total / (self.seconds / 60) if self.seconds > 0 else 0.0

    @property
    def must_be_quiet(self) -> bool:
        return any(k in self.scenario.lower() for k in QUIET_SCENARIOS)


def bench_file(path: Path) -> ReplayRow:
    header = jsonl.read_header(path)
    items = list(jsonl.read(path))
    seconds = (items[-1].t_ns - items[0].t_ns) / 1e9 if len(items) > 1 else 0.0
    active = [e for _, e in replay(items, resume=True)]
    as_recorded = [e for _, e in replay(items)]

    def count(events: list[Event], kind: type) -> int:
        return sum(isinstance(e, kind) for e in events)

    resumes = sum(isinstance(e, StateChanged) and e.state is State.ACTIVE for e in as_recorded)
    return ReplayRow(
        file=path.name,
        scenario=str(header.get("scenario", "")),
        seconds=seconds,
        clicks=count(active, Click),
        drags=count(active, ButtonDown),
        scrolls=count(active, Scroll),
        resumes=resumes,
        modes=count(active, ModeChanged),
        overlays=count(active, OverlayShown),
        actions=count(active, SystemAction),
        levels=count(active, LevelStep),
    )


def replay_table(rows: list[ReplayRow]) -> str:
    lines = [
        "| file | scenario | seconds | clicks | drags | scrolls | resumes | modes | overlays "
        "| actions | levels | per minute | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        verdict = ("FAIL" if r.total else "ok") if r.must_be_quiet else "-"
        lines.append(
            f"| {r.file} | {r.scenario or '?'} | {r.seconds:.1f} | {r.clicks} | {r.drags} | "
            f"{r.scrolls} | {r.resumes} | {r.modes} | {r.overlays} | {r.actions} | {r.levels} | "
            f"{r.per_minute:.1f} | {verdict} |"
        )
    return "\n".join(lines)


def run_replay(pattern: str) -> int:
    files = sorted(Path(p) for p in glob.glob(pattern))
    if not files:
        print(f"no recordings match {pattern!r}", file=sys.stderr)
        return 2
    rows = [bench_file(p) for p in files]
    print(replay_table(rows))
    return 1 if any(r.must_be_quiet and r.total for r in rows) else 0


# -- live ------------------------------------------------------------------------------------


class NullInput:
    """Counts events and sends nothing to the OS."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def _n(self, name: str) -> None:
        self.counts[name] = self.counts.get(name, 0) + 1

    def move(self, nx: float, ny: float) -> None:
        self._n("move")

    def button_down(self, b: object) -> None:
        self._n("button_down")

    def button_up(self, b: object) -> None:
        self._n("button_up")

    def click(self, b: object) -> None:
        self._n("click")

    def scroll(self, d: int) -> None:
        self._n("scroll")

    def system_action(self, action: object) -> bool:
        self._n("system_action")
        return True

    def release_all(self) -> None:
        self._n("release_all")

    def double_click_ms(self) -> int:
        return 500

    def primary_rect(self) -> tuple[int, int, int, int]:
        return (0, 0, 1920, 1080)


def live_table(mode: str, seconds: float, summary: dict[str, float], cpu: float) -> str:
    return "\n".join(
        [
            "| mode | seconds | frames | tracking fps | delay p50 ms | delay p95 ms | "
            "track p95 ms | CPU % |",
            "|---|---|---|---|---|---|---|---|",
            f"| {mode} | {seconds:.0f} | {summary.get('frames', 0):.0f} | "
            f"{summary.get('fps', 0):.1f} | {summary.get('delay_p50_ms', 0):.1f} | "
            f"{summary.get('delay_p95_ms', 0):.1f} | {summary.get('track_p95_ms', 0):.1f} | "
            f"{cpu:.1f} |",
        ]
    )


def run_live(seconds: float, paused: bool) -> int:
    import os

    import psutil

    from gescrtl.app import Worker  # heavy imports only for live mode
    from gescrtl.core.engine import Engine
    from gescrtl.stats import StageStats
    from gescrtl.tracking.camera import Camera

    stats = StageStats()
    worker = Worker(Engine(), NullInput(), Camera(), lambda e: None, stats)
    proc = psutil.Process(os.getpid())
    worker.start()
    time.sleep(2.0)  # model load and camera warm-up
    if not paused:
        worker.post(Command.RESUME)
    time.sleep(0.5)
    stats.reset()
    proc.cpu_percent(None)
    time.sleep(seconds)
    cpu = proc.cpu_percent(None) / (psutil.cpu_count() or 1)  # share of the whole machine
    summary = stats.summary()
    worker.stop()
    worker.join(3.0)
    mode = "Paused" if paused else "Active"
    print(live_table(mode, seconds, summary, cpu))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gescrtl.tools.bench", description=__doc__.split("\n\n")[0])
    ap.add_argument("--replay", metavar="GLOB", help="count false triggers in recordings")
    ap.add_argument("--live", type=float, metavar="SECONDS", help="measure the real pipeline")
    ap.add_argument("--paused", action="store_true", help="with --live: stay Paused")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if args.replay:
        return run_replay(args.replay)
    if args.live:
        return run_live(args.live, args.paused)
    ap.error("choose --replay or --live")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
