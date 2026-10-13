"""Custom gestures on disk: ``%APPDATA%\\GesCRTL\\custom_gestures.json`` (spec 004 D9, FR-027).

Only numbers are stored (landmark features and paths, thresholds, names, assigned actions), never
camera images. A missing file means no custom gestures; a damaged file disables them with a
warning and is *not* overwritten (the user may want to repair it). Writes are atomic.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

from gescrtl.core import mapping
from gescrtl.core.custom import PATH_POINTS, SHAPE_DIM, CustomGesture
from gescrtl.core.types import Mode

VERSION = 1
MOVE_DIM = 1 + 2 * PATH_POINTS + SHAPE_DIM
_MODE_NAMES = {m.name for m in Mode}


def default_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "GesCRTL" / "custom_gestures.json"


def _to_json(g: CustomGesture) -> dict[str, Any]:
    return {
        "name": g.name,
        "kind": g.kind,
        "action": g.action,
        "modes": list(g.modes),
        "enabled": g.enabled,
        "samples": [list(s) for s in g.samples],
        "threshold": g.threshold,
        "created": g.created,
    }


def _from_json(obj: Any) -> CustomGesture:
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    name, kind, action = obj["name"], obj["kind"], obj["action"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("the name is missing")
    if kind not in ("shape", "move"):
        raise ValueError(f"unknown kind {kind!r}")
    if not mapping.is_allowed(action):
        raise ValueError(f"{action!r} is not an allowed action")
    modes = tuple(obj.get("modes", ()))
    if any(m not in _MODE_NAMES for m in modes):
        raise ValueError("unknown mode")
    dim = SHAPE_DIM if kind == "shape" else MOVE_DIM
    samples = tuple(tuple(float(v) for v in s) for s in obj["samples"])
    if not samples or any(len(s) != dim for s in samples):
        raise ValueError("the samples have the wrong size")
    threshold = float(obj["threshold"])
    if not threshold > 0:
        raise ValueError("the threshold must be positive")
    return CustomGesture(
        name=name,
        kind=kind,
        action=action,
        modes=modes,
        enabled=bool(obj.get("enabled", True)),
        samples=samples,
        threshold=threshold,
        created=str(obj.get("created", "")),
    )


def save(gestures: tuple[CustomGesture, ...], path: Path | None = None) -> Path:
    path = path or default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    doc = {"version": VERSION, "gestures": [_to_json(g) for g in gestures]}
    tmp.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def load(path: Path | None = None) -> tuple[tuple[CustomGesture, ...], list[str]]:
    """The saved gestures and warnings. Never raises; a bad entry is skipped and named."""
    path = path or default_path()
    if not path.exists():
        return (), []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        entries = doc["gestures"]
        if doc.get("version") != VERSION or not isinstance(entries, list):
            raise ValueError("unsupported format")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return (), [f"{path.name} could not be read ({exc}): custom gestures are off"]
    gestures: list[CustomGesture] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for i, entry in enumerate(entries):
        try:
            g = _from_json(entry)
        except (ValueError, KeyError, TypeError) as exc:
            warnings.append(f"custom gesture #{i + 1} skipped: {exc}")
            continue
        if g.name in seen:
            warnings.append(f"custom gesture {g.name!r} appears twice: the second one is skipped")
            continue
        seen.add(g.name)
        gestures.append(g)
    return tuple(gestures), warnings


# -- edits (each returns the new tuple; the caller saves it) -------------------------------------


def upsert(gestures: tuple[CustomGesture, ...], new: CustomGesture) -> tuple[CustomGesture, ...]:
    """Add ``new``, or replace the gesture with the same name (retraining)."""
    kept = tuple(g for g in gestures if g.name != new.name)
    return (*kept, new)


def remove(gestures: tuple[CustomGesture, ...], name: str) -> tuple[CustomGesture, ...]:
    return tuple(g for g in gestures if g.name != name)


def set_enabled(
    gestures: tuple[CustomGesture, ...], name: str, enabled: bool
) -> tuple[CustomGesture, ...]:
    return tuple(replace(g, enabled=enabled) if g.name == name else g for g in gestures)


def disable_all(gestures: tuple[CustomGesture, ...]) -> tuple[CustomGesture, ...]:
    """Reset to defaults keeps custom gestures but turns every one off (FR-013)."""
    return tuple(replace(g, enabled=False) for g in gestures)


def write(gestures: tuple[CustomGesture, ...], path: Path | None = None) -> Path:
    """Save the custom gesture file (the name the app uses; numbers only, never an image)."""
    return save(gestures, path)
