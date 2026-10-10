# GesCRTL Gesture Vocabulary (first release)

> Source: spec.md FR-007, FR-008, FR-010; research.md R5, R10; interaction-model.md.

Seven hand forms. Each works with either hand. Thresholds are in `safety-policy.md`.

| ID | Hand form (plain words) | How it is recognized (plain words) | Scope | Valid in states | Min hold | Meaning | Either hand? |
|---|---|---|---|---|---|---|---|
| G1 | Relaxed hand | Any detected hand that is not G2–G7 | Pointer | Active · Normal | none | Move the cursor | Yes |
| G2 | Thumb–index pinch | Thumb tip close to index tip, relative to hand size | Pointer; also mode menu | Active · Normal; Active · ModeMenuOpen | tap, or 300 ms for drag | Tap = left click; two taps within the double-click time = double click; hold > 300 ms = drag; in the mode menu = confirm | Yes |
| G3 | Thumb–middle pinch | Thumb tip close to middle fingertip, relative to hand size | Pointer | Active · Normal | none | Right click | Yes |
| G4 | Index and middle fingers extended together | Index and middle extended; ring and pinky curled | Pointer | Active · Normal | none | Vertical scroll by hand motion | Yes |
| G5 | Closed fist | All four fingertips closer to the wrist than their middle joints | Global | Active (all substates); Active · ModeMenuOpen (cancel) | 1.5 s for pause | Held < 1.5 s = clutch; held ≥ 1.5 s = Pause and emergency stop; in the mode menu = cancel | Yes |
| G6 | Open palm facing the camera | All five fingers extended | Global | Paused only | 1 s | Resume | Yes |
| G7 | Three fingers extended | Index, middle, and ring extended; thumb and pinky curled | Global | Active · Normal | 0.8 s | Open the mode menu | Yes |

## Pointer Mode actions

| Action | Gesture |
|---|---|
| Move | G1 (palm-center anchor) |
| Left click | G2 tap |
| Double click | Two G2 taps within the Windows double-click time (default 500 ms) |
| Drag | G2 held > 300 ms, then move; release the pinch to drop |
| Right click | G3 tap |
| Vertical scroll | G4 plus hand moving up or down |
| Clutch | G5 held < 1.5 s |

## Not gestures

Turn off and Turn on are keyboard shortcut or tray only (research R10). This keeps the camera from
being turned off by accident and keeps the vocabulary within 8 gestures.

## Active region

The central 60% × 60% of the mirrored camera view maps to the whole primary monitor
(kept after the Phase 0 target task; all four screen corners were reachable, ADR 0005). The user can rest the hand outside this region without moving the
cursor to a wrong place; a hand outside it simply clamps the cursor to the screen edge.

## Conflict check

No hand form has two meanings in the same state. Each table lists what is recognized in that state.

**Paused**

| Gesture | Meaning |
|---|---|
| G6 held 1 s | Resume |
| All others | Ignored |

**Active · Normal**

| Gesture | Meaning |
|---|---|
| G1 | Move |
| G2 | Click / double click / drag |
| G3 | Right click |
| G4 | Scroll |
| G5 < 1.5 s | Clutch |
| G5 ≥ 1.5 s | Pause |
| G7 held 0.8 s | Open mode menu |
| G6 | Not special; treated as G1 movement |

**Active · Clutched**

| Gesture | Meaning |
|---|---|
| G5 opened < 1.5 s | Back to Active · Normal |
| G5 held to 1.5 s | Pause |
| All others | Ignored (cursor frozen) |

**Active · ModeMenuOpen**

| Gesture | Meaning |
|---|---|
| G1 | Point at a mode |
| G2 | Confirm the pointed mode |
| G5 | Cancel (not clutch) |
| All others | Ignored |

No conflicts found. G6 acts only in Paused; in Active it is ordinary G1 movement. G5 in
ModeMenuOpen means cancel, not clutch.
