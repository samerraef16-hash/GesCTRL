# GesCRTL Gesture Vocabulary (first release)

> Source: spec.md FR-007, FR-008, FR-010; research.md R5, R10; interaction-model.md.

Eight hand forms. Each works with either hand. Thresholds are in `safety-policy.md`.

| ID | Hand form (plain words) | How it is recognized (plain words) | Scope | Valid in states | Min hold | Meaning | Either hand? |
|---|---|---|---|---|---|---|---|
| G1 | Relaxed hand | Any detected hand that is not G2–G8 | Pointer | Active · Normal | none | Move the cursor | Yes |
| G2 | Thumb–index pinch | Thumb tip close to index tip, relative to hand size | Pointer; also mode menu | Active · Normal; Active · ModeMenuOpen | tap, or 300 ms for drag | Tap = left click; two taps within the double-click time = double click; hold > 300 ms = drag; in the mode menu = confirm | Yes |
| G3 | Thumb–middle pinch | Thumb tip close to middle fingertip, relative to hand size | Pointer | Active · Normal | none | Right click | Yes |
| G4 | Fist with thumb out (scroll wheel) | All four fingers curled and the thumb sticking out, clearly away from the index fingertip | Pointer | Active · Normal | none (250 ms settle) | Vertical scroll: tilt the thumb up or down; speed grows with the tilt from where the pose started | Yes |
| G5 | Closed fist | All four fingers curled and the thumb tucked | Pointer; also mode menu | Active · Normal; Active · ModeMenuOpen (cancel) | none | Cursor frozen, nothing else (never pauses); in the mode menu = cancel | Yes |
| G6 | Open palm facing the camera | Four fingers extended and the thumb out to the side | Global | Paused only | 1 s | Resume | Yes |
| G7 | Three fingers extended | Index, middle, and ring extended; thumb and pinky curled | Global | Active · Normal | 0.8 s | Open the mode menu | Yes |
| G8 | Flat hand | Upright hand, palm toward the camera, four fingers extended together, thumb tucked across the center of the palm | Pointer | Active · Normal | 1.5 s for pause | Held: clutch (cursor frozen, nothing else); held ≥ 1.5 s = Pause and emergency stop | Yes |

## Pointer Mode actions

| Action | Gesture |
|---|---|
| Move | G1 (palm-center anchor) |
| Left click | G2 tap |
| Double click | Two G2 taps within the Windows double-click time (default 500 ms) |
| Drag | G2 held > 300 ms, then move; release the pinch to drop |
| Right click | G3 tap |
| Vertical scroll | G4, then tilt the thumb up (scroll up) or down (scroll down); level = stop |
| Clutch | G8 held |

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
| G4 | Scroll by thumb tilt |
| G5 | Cursor frozen, nothing else |
| G8 | Clutch (cursor frozen) |
| G8 ≥ 1.5 s | Pause |
| G7 held 0.8 s | Open mode menu |
| G6 | Not special; treated as G1 movement |

**Active · Clutched**

| Gesture | Meaning |
|---|---|
| G8 released (any other recognized pose) | Back to Active · Normal |
| G8 held to 1.5 s | Pause |
| All others | Ignored (cursor frozen) |

**Active · ModeMenuOpen**

| Gesture | Meaning |
|---|---|
| G1 | Point at a mode |
| G2 | Confirm the pointed mode |
| G5 | Cancel (not clutch) |
| All others | Ignored |

No conflicts found. G6 acts only in Paused; in Active it is ordinary G1 movement. G6 and G8 differ
only by the thumb (out vs tucked). G5 in ModeMenuOpen means cancel.

## Recognition notes (measured on the Phase 0 recording)

- G8 is strict so a thumb on its way to a pinch never clutches: four fingers clearly straight
  (tip/pip > 1.25), hand upright (within 25° of vertical), thumb deep in the palm (< 0.5 hand sizes
  from its center) and more than 0.45 from both fingertips, seen for 5 frames. A thumb between
  "out" and "tucked", or a tilted hand, stays G1 (pointing). Pause also needs the hand to stay
  still (4% of the frame) for the 1.5 s. On an upright hand with four straight fingers a
  thumb-middle contact is ignored (a real right-click pinch curls the middle finger).
- Pinches are tested before the fist: a natural pinch curls the other fingers.
- Thumb "out" means the thumb tip is more than 0.68 hand sizes from the palm center (tucked 0.35–0.55,
  out 0.77–1.1). Thumbs-up also needs the thumb tip more than 0.8 hand sizes from the index
  fingertip; with that rule no natural pointing or pinching frame in the recording counted as
  thumbs-up, so a click cannot start a scroll.
- Scroll tilt is the angle of the thumb (knuckle to tip) above horizontal in the camera image,
  measured from the angle at which the pose was recognized (like a middle-click autoscroll
  anchor). Dead zone 8°, full speed at 45°, maximum 1800 wheel units per second; a classic vertical
  thumbs-up only anchors there and does not scroll by itself.
- These values are re-checked with real thumb-out, flat-hand and fist recordings in the manual
  session (tasks T055, T051).
