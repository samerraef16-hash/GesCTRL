# GesCRTL Accidental-Action (Safety) Policy

> Source: spec.md FR-009; constitution Principle I; research.md R7, R9, R10.
>
> Values marked *(provisional)* are updated from `docs/measurements/feasibility-report.md` in T039.

| Rule | Value | Applies to | Why |
|---|---|---|---|
| Minimum tracker confidence for consequential actions | 0.5 *(provisional)* | All consequential actions | Below this the hand reading may be wrong, so nothing is sent |
| Minimum stable frames before a gesture counts | 3 *(provisional)* | All gestures | A single noisy frame must not trigger anything |
| Pinch start ratio | < 0.25 *(provisional)* | G2, G3 | Hysteresis: start threshold |
| Pinch release ratio | > 0.35 *(provisional)* | G2, G3 | Hysteresis: release threshold, looser than start so it cannot flicker |
| Hold time: resume | 1000 ms *(provisional)* | G6 | Deliberate start |
| Hold time: mode menu | 800 ms *(provisional)* | G7 | Deliberate menu opening |
| Hold time: pause | 1500 ms *(provisional)* | G8 | Separates a clutch from a deliberate pause |
| Hold time: drag | 300 ms *(provisional)* | G2 | Separates a click from a drag |
| Cooldown: right click | 300 ms *(provisional)* | G3 | Prevents repeated right clicks |
| Cooldown: mode switch | 1000 ms *(provisional)* | G7 / mode menu | Prevents rapid mode flipping |
| Cooldown: resume / pause | 1000 ms *(provisional)* | G6, G5 | Prevents toggling by accident |
| Click stabilization | Cursor frozen for 100 ms at pinch start *(provisional)* | G2, G3 | The click lands where the user aimed |
| Loss-confirmation window | 3 consecutive frames (kept; only 17 dropout runs measured, fewer than the 20 needed to change it) | Tracking loss | Filters one-frame webcam dropouts |
| Hold time: level panel | 500 ms | G9 | Deliberate opening; a loose-pinky scroll never counts as G9 |
| Menu / panel timeout | 5000 ms | Mode menu, level panel | No choice or pinch means close, nothing changes |
| Swipe | 3 open-hand frames, ≥ 1.5 hand sizes in 350 ms, vertical share ≤ 50 % *(provisional)* | Open-hand swipe | A real swipe is fast and horizontal; anything else is ignored |
| Swipe cooldown, return block, re-arm | 600 ms; 1000 ms opposite direction; speed below 1 hand size/s for 100 ms *(provisional)* | Open-hand swipe | The return stroke and a shaky hand never change a slide twice |
| Show start / end | G4 held 1 s, thumb ≥ 50° to enter and ≥ 35° to stay, cooldown 2 s *(provisional)* | Presentation | Slide shows start or end only on purpose |
| Laser | One Euro 0.3 / 0.002; 300 ms grace *(provisional)* | G10 | A steadier dot than the cursor, no flicker |
| Target pointing margin | 1 % of the screen inside the target, hysteresis on exit | Menus, panel, grid | A pointer on an edge never selects |
| Action cooldown | 400 ms per target | Panel, grid | A pinch cannot fire twice |
| Confirmation window | 3000 ms | Screenshot, switch app | Two pinches on purpose; fist, another target or timeout cancels |
| Level steps | 2 % per step, at most 40 % per second, repeat every 150 ms | Level panel, grid | A level can never jump |
| Paused processing rate | 10 FPS cap (measured: 8.1 FPS achieved, 1.3% of total CPU) | Paused | Saves CPU while still listening for resume |

One Euro smoothing (min_cutoff 1.0, beta 0.007, d_cutoff 1.0) was kept after Phase 0: pointing was
smooth and jitter-free. The remaining *(provisional)* values (confidence, stable frames, pinch
ratios, hold times, cooldowns, click stabilization) were not measured in Phase 0 and are tuned in
Phase 1 and Phase 2 on recorded sessions.

The pinch ratio is the distance from the thumb tip to the fingertip divided by the distance from
the wrist to the middle-finger knuckle, so it does not depend on how far the hand is from the
camera.

## Uncertain tracking

Below the confidence threshold, no consequential action is emitted and the cursor does not move.
Nothing is guessed.

## ReleaseAll

See the ReleaseAll section of `docs/interaction/interaction-model.md`.

## Primary hand only

Other hands and people in the frame produce nothing.

## What may never be overridden

Emergency stop, pause, and ReleaseAll cannot be remapped or disabled by settings or by custom
gestures (spec User Story 2; Plan.md Phase 8).
