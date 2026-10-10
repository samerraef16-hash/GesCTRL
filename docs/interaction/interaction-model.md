# GesCRTL Interaction Model

> Source: spec.md FR-001–FR-006, FR-001a, FR-002a, FR-005a; data-model.md (State Transition Table, Invariants);
> research.md R9, R10, R11; contracts/hud-feedback.md, contracts/global-hotkeys.md.

## Purpose

This document is the single authority on what state GesCRTL is in, what mode it is in, and what
happens when an event occurs. Every later feature must follow it. If a feature needs different
behavior, this document is amended first.

## States

| State | Camera | Input allowed | Processing rate | Entered by | Left by |
|---|---|---|---|---|---|
| Inactive | Stopped and released | No | None | Turn off (E6) | Turn on (E7) by shortcut or tray; relaunch |
| Paused | Running | No | Reduced (start: 10 FPS) | Launch (E1); pause (E3/E4); emergency stop (E5); Turn on (E7) | Resume (E2/E3); Turn off (E6) |
| Active | Running | Yes, only in `Normal` and when confidence ≥ threshold | Full | Resume (E2/E3); automatic return from Tracking Lost (E9) | Pause, emergency stop, Turn off, hand loss, camera loss |
| Active · Normal | Running | Yes | Full | Entering Active; mode confirmed or cancelled; clutch ended | Clutch (E16); mode menu (E12) |
| Active · Clutched | Running | No (cursor frozen) | Full | Fist detected (E16) | Fist opened before 1.5 s (E17); fist reaches 1.5 s (E4 → Paused) |
| Active · ModeMenuOpen | Running | No (menu only) | Full | Mode-menu gesture (E12) | Mode confirmed (E13); cancelled (E14); hand loss; pause |
| Tracking Lost · HandMissing | Running | No | Full | Primary hand loss confirmed (E8) | Hand reappears (E9) automatic; pause; Turn off |
| Tracking Lost · CameraUnavailable | Not available | No | None | Camera becomes unavailable (E10) | Camera available again (E11) → HandMissing; pause; Turn off |

## Startup

The application always starts in **Paused** (E1). No input is sent until the user performs the
resume gesture or uses the resume shortcut or tray item (FR-005a).

## Modes

- **Pointer** (default), **Keyboard**, **Presentation**, **Media/System**.
- Exactly one mode is current at any time.
- The current mode is kept through Paused and Tracking Lost and restored on return to Active.
- Only Pointer has gestures in the first release. The other modes are named placeholders.

## Events

1. **E1** Launch
2. **E2** Resume gesture (G6, open palm held ≥ 1 s)
3. **E3** Resume/pause hotkey or tray "Resume"
4. **E4** Pause gesture (G5, fist held ≥ 1.5 s)
5. **E5** Emergency-stop hotkey
6. **E6** Turn off (hotkey or tray)
7. **E7** Turn on (hotkey or tray)
8. **E8** Primary hand loss confirmed
9. **E9** Primary hand reappears
10. **E10** Camera becomes unavailable
11. **E11** Camera available again
12. **E12** Mode-menu gesture (G7 held ≥ 0.8 s)
13. **E13** Mode confirmed (pinch on a menu item)
14. **E14** Mode menu cancelled (fist, or 5 s with no selection)
15. **E15** Exit or crash
16. **E16** Fist detected while Active · Normal (clutch start)
17. **E17** Fist opened before 1.5 s (clutch end)

## Transition matrix

Rows are the current state; columns are events E2–E17 (E1 is described under Startup).

Cell format: `→ <New state> · RA · "<HUD text>"`. `RA` means ReleaseAll happens. `no-op` means
nothing happens. `n/a` means the event cannot occur in that state.

State abbreviations: **I** Inactive · **P** Paused · **AN** Active · Normal · **AC** Active · Clutched ·
**AM** Active · ModeMenuOpen · **TH** Tracking Lost (HandMissing) · **TC** Tracking Lost (CameraUnavailable).
The mode is unchanged unless the cell says otherwise.

| State \ Event | E2 | E3 | E4 | E5 | E6 | E7 | E8 | E9 |
|---|---|---|---|---|---|---|---|---|
| **Inactive** | n/a (camera off) | no-op | n/a (camera off) | no-op | no-op | → P · "Paused" | no-op | no-op |
| **Paused** | → AN · "Pointer" (previous mode) | → AN · "Pointer" (previous mode) | no-op · RA | no-op · RA | → I · RA · HUD hidden | no-op | no-op | no-op |
| **Active · Normal** | no-op | → P · RA · "Paused" | → P · RA · "Paused" | → P · RA · "Stopped", then "Paused" | → I · RA · HUD hidden | no-op | → TH · RA · "Hand not visible" | no-op |
| **Active · Clutched** | no-op | → P · RA · "Paused" | → P · RA · "Paused" | → P · RA · "Stopped", then "Paused" | → I · RA · HUD hidden | no-op | → TH · RA · "Hand not visible" | no-op |
| **Active · ModeMenuOpen** | no-op | → P (menu closed) · RA · "Paused" | → P (menu closed) · RA · "Paused" | → P (menu closed) · RA · "Stopped", then "Paused" | → I · RA · HUD hidden | no-op | → TH (menu closed, mode unchanged) · RA · "Hand not visible" | no-op |
| **Tracking Lost (HandMissing)** | n/a (no hand) | → P · RA · "Paused" | n/a (no hand) | → P · RA · "Stopped", then "Paused" | → I · RA · HUD hidden | no-op | no-op | → AN (same mode, automatic) · "Pointer" |
| **Tracking Lost (CameraUnavailable)** | n/a (no camera) | → P · RA · "Paused" | n/a (no camera) | → P · RA · "Stopped", then "Paused" | → I · RA · HUD hidden | no-op | no-op | n/a (no camera) |

| State \ Event | E10 | E11 | E12 | E13 | E14 | E15 | E16 | E17 |
|---|---|---|---|---|---|---|---|---|
| **Inactive** | no-op | no-op | n/a (camera off) | n/a (camera off) | n/a (camera off) | → exit · RA | n/a (camera off) | n/a (camera off) |
| **Paused** | no-op (flag set) · "Paused · Camera unavailable" | no-op (flag cleared) · "Paused" | no-op | no-op | no-op | → exit · RA | no-op | no-op |
| **Active · Normal** | → TC · RA · "Camera unavailable" | no-op | → AM · RA · mode menu shown | no-op | no-op | → exit · RA | → AC · RA · "Pointer · Hold" | no-op |
| **Active · Clutched** | → TC · RA · "Camera unavailable" | no-op | no-op | no-op | no-op | → exit · RA | no-op | → AN · "Pointer" |
| **Active · ModeMenuOpen** | → TC (menu closed, mode unchanged) · RA · "Camera unavailable" | no-op | no-op | → AN (new mode) · RA · "Active · \<new mode\>" | → AN (mode unchanged) · menu closes | → exit · RA | no-op (a fist inside the menu means E14, not clutch) | no-op |
| **Tracking Lost (HandMissing)** | → TC · "Camera unavailable" | no-op | n/a (no hand) | n/a (no hand) | n/a (no hand) | → exit · RA | n/a (no hand) | n/a (no hand) |
| **Tracking Lost (CameraUnavailable)** | no-op | → TH · "Hand not visible" | n/a (no camera) | n/a (no camera) | n/a (no camera) | → exit · RA | n/a (no camera) | n/a (no camera) |

Notes:
- In Active · Clutched, E4 (fist held until it reaches 1.5 s) leads to Paused with RA; this row
  entry is shown under E4.
- Gestures that occur while a transition is completing are ignored.
- Any event not listed as acting is a no-op; adding a new event requires a new column here.

## ReleaseAll

ReleaseAll releases every held mouse button and key. It happens on:

- entering Paused (pause, emergency stop);
- entering Tracking Lost (hand loss or camera loss);
- entering Inactive (Turn off);
- opening the mode menu, and any mode change;
- entering Active · Clutched (E16);
- shutdown (E15) and unhandled failure (exit handlers).

## Emergency stop

The emergency stop always moves the application to **Paused** and performs ReleaseAll. It has two
independent paths (FR-005):

1. The global hotkey `Ctrl+Alt+Esc` (see `contracts/global-hotkeys.md`), which works with any
   application focused.
2. The pause gesture G5 (fist held ≥ 1.5 s).

The tray menu offers Pause as a mouse-based third path. From Inactive the emergency stop has no
effect, because nothing is acting.

## Paused vs Inactive

- **Paused**: the camera keeps running at a reduced processing rate, no input is sent, and only a
  deliberate resume gesture (held for a minimum time) or the keyboard shortcut / tray returns to
  Active.
- **Inactive**: the camera is fully stopped and released. It is entered via a "Turn off" action
  (shortcut or tray) and left only via shortcut, tray, or relaunch, since no gestures can be seen.
- On launch the application starts in Paused.

## Primary hand

1. The hand that performs the resume gesture becomes the primary hand.
2. While Active, the primary hand is kept by nearest-wrist-position continuity between frames.
3. On automatic resume from Tracking Lost, a single hand appearing in the active region is
   accepted. If several appear, the one nearest the last known primary position is chosen.
4. Non-primary hands never produce input.

## Mode menu

- Opened by holding the three-finger gesture G7 for 0.8 s (E12).
- The user points at a mode and confirms with a thumb–index pinch (E13).
- Cancelled with a fist or after 5 s with no selection (E14); the mode is unchanged.
- While the menu is open, no other input is sent (FR-002a).
- A single accidental frame cannot switch modes: opening needs the hold time, and switching needs
  an explicit confirmation.
- In the first release the menu lists all four modes, but only Pointer has gestures.

## Tracking loss

- Tracking Lost is declared after the **loss-confirmation window**: 3 consecutive frames
  without the primary hand or below the confidence threshold *(provisional)*.
- When it is declared, ReleaseAll happens immediately, with no extra grace period.
- A drag does not continue after the hand returns; the user starts a new drag.
- When the primary hand reappears, control returns automatically to Active in the same mode
  (FR-001a). Paused is never left automatically.

## Spec coverage

| Scenario / edge case | Where answered |
|---|---|
| US1 scenario 1: any state × event has one result | Transition matrix |
| US1 scenario 2: hand disappears in Active | Transition matrix (E8 column); Tracking loss |
| US1 scenario 3: nothing sent at startup | Startup |
| US1 scenario 4: emergency stop from any state | Emergency stop; transition matrix (E5 column) |
| US1 scenario 5: mode switching defined | Mode menu |
| US1 scenario 6: Paused stays Paused when hand leaves and returns | Transition matrix (Paused row, E8/E9) |
| Edge: several hands or people in view | Primary hand |
| Edge: hand briefly lost during a drag | Tracking loss; ReleaseAll |
| Edge: camera unplugged or taken | Transition matrix (E10/E11 columns) |
| Edge: stop while the hand is not visible | Emergency stop (hotkey and tray) |
| Edge: gesture while switching modes | Notes under the transition matrix |
| Edge: poor lighting or partial hand | Tracking loss (confidence threshold) |
| Edge: feasibility targets missed | Not an interaction-model topic; see `docs/measurements/feasibility-report.md` |
| Edge: contradiction between documents | Not an interaction-model topic; see `docs/phase0-review.md` |
