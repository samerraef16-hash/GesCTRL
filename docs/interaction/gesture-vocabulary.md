# GesCRTL Gesture Vocabulary (first release)

> Source: spec.md FR-007, FR-008, FR-010; research.md R5, R10; interaction-model.md.

Ten hand forms and one motion (the open-hand swipe). Each works with either hand. Thresholds are in `safety-policy.md`.

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
| G9 | Call me | Index, middle and ring curled; pinky extended; thumb out and away from the index fingertip | Global | Active · Normal | 0.5 s | Open the volume / brightness panel (any mode) | Yes |
| G10 | Index point | Index extended alone; middle, ring and pinky curled; thumb tucked and clear of the index | Presentation; moves the cursor like G1 in Pointer | Active · Normal | none (stable frames) | Presentation: show the laser dot | Yes |
| Swipe | Open-hand swipe (motion) | All four fingers extended; fast, mostly horizontal move of at least 1.5 hand sizes within 350 ms | Presentation | Active · Normal and Clutched | 3 open-hand frames | Right = next slide, left = previous slide | Yes |

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

## Presentation Mode actions

| Action | Gesture |
|---|---|
| Laser dot | G10 (the dot stays 0.3 s if the pose slips, then hides) |
| Next / previous slide | Open-hand swipe right / left (also works with the flat hand G8) |
| Start show from current slide | G4 with the thumb up (tilt at least 50°, held 1 s) |
| End show | G4 with the thumb down (tilt at most −50°, held 1 s) |
| Pause | G8 held still 1.5 s |

Thumb direction uses hysteresis: "up" starts at 50° and lasts until the tilt drops below 35°.
Start/end is supported in PowerPoint and in Google Slides (Edge or Chrome); elsewhere only the
slide changes work. The real cursor never moves in Presentation Mode.

## Media/System Mode and the level panel

| Action | Gesture |
|---|---|
| Choose a target | Point with G1 (a ring follows the hand), then G2 on it |
| Repeat volume / brightness | Hold the G2 on a + or − target (every 150 ms, 2 % per step) |
| Screenshot, switch app | G2 on the target, then G2 on it again within 3 s |
| Cancel a waiting confirmation | G5 |
| Level panel (all modes) | G9 held 0.5 s, then G2 on a slider and move the hand up or down (100 % per slider height, at most 40 %/s); G5 or 5 s idle closes it |

## Global and mode-specific gestures

Global (same meaning in every mode): G6 resume, G7 mode menu, G9 level panel, G8 clutch / pause,
and the emergency stop. Mode-specific: G1–G5 in Pointer Mode, G10 / swipe / G4 thumb in
Presentation Mode, G1 + G2 + G5 on the grid in Media/System Mode. A gesture that a mode does not
define does nothing in that mode. G7 and G9 are ignored while a gesture of the mode is in progress
(mid-pinch, drag, scroll, swipe, pending confirmation).

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

**Active · Normal · Presentation**

| Gesture | Meaning |
|---|---|
| G10 | Laser dot |
| Open-hand swipe | Next / previous slide |
| G4 thumb up / down held 1 s | Start / end show |
| G7 / G9 held | Mode menu / level panel |
| Everything else | Ignored |

**Active · Normal · Media/System**

| Gesture | Meaning |
|---|---|
| G1 | Point at a grid target |
| G2 on a target | Run it (twice for screenshot / switch app) |
| G5 | Cancel a waiting confirmation |
| G7 / G9 held | Mode menu / level panel |
| Everything else | Ignored |

**Active · LevelPanelOpen**

| Gesture | Meaning |
|---|---|
| G1 | Point at a slider |
| G2, then move up / down | Change that level |
| G5 | Close |
| G7 | Close |
| Everything else | Ignored |

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
