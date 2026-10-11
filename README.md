# GesCRTL

Control a Windows PC with hand gestures from an ordinary webcam. This release is **Pointer Mode**:
move the cursor, click, double-click, right-click, drag and scroll with one hand, in the air.

It is a portfolio project that runs from source (Python 3.12, Windows 11). Hand tracking is
MediaPipe Hand Landmarker; everything after tracking is plain, tested logic that never touches
the camera or the OS directly.

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
.\scripts\fetch_model.ps1          # downloads the hand model once (the app itself never uses the network)
python -m gescrtl --preview        # --preview opens a camera window to help you frame your hand
```

The app starts **Paused**. Hold an open palm facing the camera for one second to resume.

## Gestures (either hand)

| Do this | To get this |
|---|---|
| Open palm, thumb out, held 1 s (while Paused) | Resume |
| Relaxed hand | Move the cursor (the centre of your palm drives it) |
| Pinch thumb and index, then let go | Left click |
| Two quick pinches | Double click |
| Hold the pinch, then move | Drag; let go to drop |
| Pinch thumb and middle finger, then let go | Right click |
| Fist sideways with the thumb out, then tilt the thumb up or down | Scroll up or down, faster the more you tilt (like holding a scroll wheel) |
| Closed fist | Freeze the cursor |
| Flat hand: upright, palm forward, fingers together, thumb across the palm | Hold the cursor still |
| Flat hand held still for 1.5 s | Pause |

Details and the reasoning are in [`docs/interaction/gesture-vocabulary.md`](docs/interaction/gesture-vocabulary.md).

## Safety

- **Emergency stop: `Ctrl+Alt+Esc`.** Lets go of every button and pauses, from any state.
  `Ctrl+Alt+P` pauses or resumes, `Ctrl+Alt+O` turns the app off or on.
- Nothing clicks or presses a key until a gesture has been seen clearly for several frames, and
  every pinch and pose has hysteresis and cooldowns so a wobble is not a click.
- Pause, losing your hand, a camera problem, an error, or exiting always releases held buttons.
- Only one hand controls at a time. A second hand or person in view is ignored.
- The tray icon shows the state and offers Pause/Resume, Turn off, Reload settings, Reset to
  defaults and the camera preview.

## Privacy

Camera frames stay in memory and are never saved or sent anywhere; the app makes no network calls
when it runs. The optional camera preview only draws on your screen. Recordings (`--record NAME`)
contain hand landmark numbers and timestamps, never images.

## Settings

`%APPDATA%\GesCRTL\settings.json` is created on first run with every value and its default. Edit
it and choose **Reload settings** in the tray. A bad value falls back to its default with a
notice. A few flags override the file for quick tuning:
`--region`, `--min-cutoff`, `--beta`, `--scroll-rate`, `--scroll-deadzone`.

## Tools and tests

```powershell
pytest                                            # unit and landmark-replay tests
ruff check .; ruff format --check .; mypy         # lint, formatting, strict types on the core
python -m gescrtl --record NAME                   # record landmarks to recordings\
python -m gescrtl.replay recordings\FILE.jsonl --resume      # replay a recording, no camera
python -m gescrtl.tools.targets                   # click-accuracy page (24/48/96 px targets)
python -m gescrtl.tools.bench --replay "recordings\*.jsonl"  # false triggers per recording
python -m gescrtl.tools.bench --live 20           # tracking rate, delay and CPU (no OS input)
```

To turn a misfire into a regression test, see [`tests/fixtures/README.md`](tests/fixtures/README.md).

## Known limitations

See [`docs/product/known-limitations.md`](docs/product/known-limitations.md). In short: it cannot
control elevated windows or the lock screen, it needs decent light, and it covers the primary
monitor only.

## Project layout

`src/gescrtl/core` is the pure gesture logic (poses, state machine, pointer, smoothing).
`platform/` holds everything Windows-specific (SendInput, hotkeys, HUD, tray, preview) behind
interfaces; `tracking/` is the camera and MediaPipe. The roadmap is in `Plan.md`, the rules in
`.specify/memory/constitution.md`, and each phase has a folder under `specs/`.
