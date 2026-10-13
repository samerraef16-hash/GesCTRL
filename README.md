# GesCRTL

Control a Windows PC with hand gestures from an ordinary webcam. Four modes, one hand:
**Pointer** (move, click, drag, scroll), **Presentation** (slides and a laser pointer),
**Media/System** (play, volume, brightness, screenshot) and **Keyboard** (an on-screen keyboard you
point at and pinch). Volume and brightness are also one gesture away in every mode. A settings
window, a guided calibration, several monitors, dwell instead of pinch, and your own recorded
gestures make it fit the person and the desk.

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
| Flat hand: upright, palm forward, fingers together, thumb across the palm | Hold the cursor still; make a fist to end the hold |
| Flat hand held still for 1.5 s | Pause |

### Modes

Hold **three fingers** for 0.8 s to open the mode menu, point at a mode and pinch to choose it
(a fist cancels). The tray icon has the same choice under **Mode** if you prefer the mouse.

| Mode | Do this | To get this |
|---|---|---|
| Presentation | Raise only the index finger | Red laser dot on the screen |
| Presentation | Swipe an open hand right or left, quickly | Next or previous slide |
| Presentation | Thumb up (or down), held 1 s | Start the show from this slide (or end it): PowerPoint and Google Slides |
| Media/System | Point at a target and pinch | Play/pause, previous, next, mute, screenshot, switch app |
| Media/System | Hold the pinch on a + or − target | Volume or brightness keeps changing |
| Media/System | Screenshot, switch app | Pinch twice within 3 s to confirm |
| Any mode | "Call me" (thumb and pinky out), held 0.5 s | Volume and brightness sliders: pinch one and move up or down |
| Keyboard | Point at a key and pinch | Type it (Backspace and the arrows repeat while held) |
| Keyboard | Pinch with your other hand | Types the key the first hand points at |
| Keyboard | Shift, Ctrl, Alt, Win | Tap once for the next key, twice to lock, a third time to clear |
| Keyboard | Shortcut row | Copy, Paste, Cut, Undo, Redo, Select all, Alt+Tab, Win, Esc |

Keyboard Mode is for short text. Typing speed is measured in the validation report; it does not
claim to match a physical keyboard.

### Make it yours

Open **Settings** from the tray icon: movement range, smoothing, hold times, dwell, the keyboard
position, which monitor shows the overlays, Start with Windows (off by default; GesCRTL still
starts Paused), what each presentation and Media gesture does, and a reset to the defaults. Under
**Calibrate** a short guided run measures your comfortable reach and pinch.

For people who cannot pinch comfortably, **Confirmation: dwell** chooses a target by holding still
on it, and **Dwell click** (off by default) clicks a cursor held still.

**Custom gestures** (off until turned on): record a hand shape or a movement, give it an allowed
action (media keys, shortcuts, slide changes). They never override clicks, pause, the mode menu or
the emergency stop, and only numbers are stored, never images.
The screenshot action presses Win+PrtSc, so Windows saves a screen capture to
`Pictures\Screenshots`; it is never a camera image. Brightness works on built-in displays only.

Details and the reasoning are in [`docs/interaction/gesture-vocabulary.md`](docs/interaction/gesture-vocabulary.md).

## Safety

- **Emergency stop: `Ctrl+Alt+Esc`.** Lets go of every button and pauses, from any state.
  `Ctrl+Alt+P` pauses or resumes, `Ctrl+Alt+O` turns the app off or on.
- Nothing clicks or presses a key until a gesture has been seen clearly for several frames, and
  every pinch and pose has hysteresis and cooldowns so a wobble is not a click.
- Pause, losing your hand, a camera problem, an error, or exiting always releases held buttons.
- Only one hand controls at a time. A second hand or person in view is ignored, except that in
  Keyboard Mode your own other hand may type too, each hand pointing at and pinching its own
  keys (it can be turned off; see ADR 0007).
- Calibration and recording a gesture send no input at all while they run.
- The tray icon shows the state and offers Pause/Resume, Turn off, Mode, Settings, Calibrate,
  turning custom gestures off, Reload settings, Reset to defaults and the camera preview.

## Privacy

Camera frames stay in memory and are never saved or sent anywhere; the app makes no network calls
when it runs. The optional camera preview only draws on your screen. Recordings (`--record NAME`)
contain hand landmark numbers and timestamps, never images.

## Settings

`%APPDATA%\GesCRTL\settings.json` is created on first run with every value and its default. Use
the **Settings** window, or edit the file and choose **Reload settings** in the tray. Custom
gestures are stored next to it in `custom_gestures.json`. A bad value falls back to its default with a
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
python -m gescrtl.tools.bench --matcher           # custom gesture matcher time per frame
```

To turn a misfire into a regression test, see [`tests/fixtures/README.md`](tests/fixtures/README.md).

## Known limitations

See [`docs/product/known-limitations.md`](docs/product/known-limitations.md). In short: it cannot
control elevated windows or the lock screen, and it needs decent light.

## Project layout

`src/gescrtl/core` is the pure gesture logic (poses, state machine, pointer, smoothing).
`platform/` holds everything Windows-specific (SendInput, hotkeys, HUD, tray, preview) behind
interfaces; `tracking/` is the camera and MediaPipe. The roadmap is in `Plan.md`, the rules in
`.specify/memory/constitution.md`, and each phase has a folder under `specs/`.
