# Spec 004 validation report (Keyboard Mode, settings, calibration, monitors, custom gestures)

Status: **automated checks done, manual session not yet run.** Everything under "Measured so
far" was produced by the tools in this repository; everything under "To measure" needs the
camera, a second monitor, or a person, and must be filled in from real runs. Do not copy numbers
into the README or the known limitations until they are measured.

## Measured so far (no camera needed)

| Check | Result | How |
|---|---|---|
| Quality gate | ruff, ruff format, mypy --strict on the core, 623 tests | `ruff check .; ruff format --check .; mypy; pytest` |
| Custom gesture matcher time per frame (10 gestures × 5 samples) | p50 0.18 ms, p95 0.33 ms, max 1.1 ms (budget: p95 ≤ 2 ms) | `python -m gescrtl.tools.bench --matcher` |
| Replay determinism for keyboard, setup, displays, custom gestures | identical events on two runs | the new replay tests |

## To measure in the manual session

Run in your PowerShell venv from the repository folder:

```powershell
.\.venv\Scripts\Activate.ps1
python -m gescrtl --preview
python -m gescrtl --record typing_one_hand      # R1; later: typing_two_hands, bystander_pinch,
                                                # idle_keyboard, custom_shapes, custom_moves,
                                                # all_builtins, calibration (see tasks.md)
python -m gescrtl.tools.bench --replay "recordings\*.jsonl"
python -m gescrtl.tools.bench --live 60         # once in Keyboard Mode with 3 custom gestures
python -m gescrtl.tools.bench --matcher
```

Name idle/typing/talking/second-person recordings with those words so the bench treats them as
"must be silent" (it counts clicks, keys, custom gestures fired, and so on).

| ID | What | Target | Result |
|---|---|---|---|
| SC-001 | Type "hello world 2026" in a text editor after 5 minutes of practice, 5 attempts | under 90 s, at most 1 uncorrected error, at least 4 of 5; record characters per minute | |
| SC-002 | Each shortcut on the shortcut row, 10 attempts each | at least 9 of 10 | |
| SC-003 | 10+ minutes idle, physical typing, talking, a second person pinching nearby, with Keyboard Mode, dwell and dwell click on | 0 keys, 0 clicks, 0 from the other person | |
| SC-004 | Stop, pause, hand loss, mode change with a locked modifier | nothing held within 200 ms, 100% | |
| SC-005 | Change a setting, see the effect, reset to defaults, without opening a file | under 1 minute | |
| SC-006 | Calibration run for at least 3 people or setups, then reach all corners and click a 48 px target (`python -m gescrtl.tools.targets`) | under 2 minutes; 9 of 10 clicks | |
| SC-007 | Enrolled custom gesture, 20 attempts, **shapes and movements separately** | at least 18 of 20 | shape: / movement: |
| SC-008 | 10 minutes of non-control recordings plus a recording of every built-in gesture, with custom gestures enrolled and on | 0 false triggers; built-ins unchanged | shape: / movement: |
| SC-009 | Two monitors with different scaling: all corners of each, a 48 px target on each, unplug and replug while running | 9 of 10 clicks on each; layout picked up within 2 s | |
| SC-010 | Replay each recording twice | identical events | |

Also check by hand: US1–US5 acceptance scenarios; a non-US input language (typed characters
match the keys, shortcuts work); Start with Windows on, sign out and in, the app starts Paused,
then off; the HUD, keyboard and menus appear on the monitor chosen in Settings; calibration
cancel leaves the settings unchanged; performance (the live bench is not worse than spec 003
beyond the allowed margin).

## Things to look at first (likely tuning points)

These are starting values chosen without real hands; the session decides them:

- Keyboard: `key_cooldown_ms` 150, `dwell_ms` 800, `key_repeat_delay_ms` 500, the key size and
  the 96% × 44.5% keyboard area (is a small hand movement really enough? is it too sensitive?).
- Two-handed pressing: the opposite-handedness rule depends on MediaPipe's left/right label, which
  is sometimes wrong. If the second hand is often ignored, the check needs another signal.
- Custom shapes: `SHAPE_FLOOR` 0.25 and the spread limit 0.8 (`core/custom.py`). Custom movements:
  `MOVE_MAX_SPREAD` 0.2 hand sizes is strict; relax it if good recordings are refused as "too
  different". A kind that misses SC-007/SC-008 is switched off in `CUSTOM_KINDS_AVAILABLE`.
- Calibration: the pinch thresholds use the 35% and 65% points between the closed and open
  readings; the movement range uses the smaller side of the reach box.
- Multi-monitor: one movement range over all monitors, so side-by-side monitors need more hand
  movement sideways than up; calibration can widen the range.

## Retrospective

(Fill in after the session: what worked, what was cut, what to do next.)
