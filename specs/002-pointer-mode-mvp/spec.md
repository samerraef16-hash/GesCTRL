# Feature Specification: Pointer Mode MVP + Reliability Hardening (Phases 1–2)

**Feature Branch**: `002-pointer-mode-mvp`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "create a specification for Phase 1: Pointer Mode MVP". Extended
during planning to include roadmap Phase 2 (Interaction Reliability Hardening), per `Plan.md` §3
(spec 002 = Phases 1 + 2); see FR-033–FR-038 and SC-011–SC-013.

## Overview

Phase 1 delivers the first usable GesCRTL: a user sitting at a Windows laptop or desktop can turn
on gesture control, move the cursor, click, double-click, right-click, drag, and scroll using one
hand in front of the webcam, and can pause or stop control instantly at any time. It replaces the
physical mouse or touchpad for everyday desktop tasks on the primary monitor.

This phase implements the interaction model, gesture vocabulary, safety policy, and feedback
concept defined in Phase 0 (`specs/001-product-foundation/`) for **Pointer Mode only**. It must
satisfy the constitution, in particular Principle I (Safety First) and Principle IV
(Deterministic, Testable Core), which are non-negotiable.

**Dependency**: Phase 0 outputs are inputs to this spec: the interaction model, gesture
vocabulary (G1–G7), safety policy values, HUD concept, feasibility report, and decision records.
Where Phase 0 values are still provisional, this spec uses them and the plan must take the final
measured values from `docs/measurements/feasibility-report.md`.

## Clarifications

### Session 2026-10-10

- Q: Does scrolling move the page only while the hand moves, or continuously like a joystick? →
  A (superseded 2026-10-11, see below): Only while the hand moves.
- Q: Should a visual cue appear at the cursor when gestures are recognized? → A: Yes, always on:
  ready ring, pinch progress, click flash, and distinct drag/scroll/clutch looks.
- Q: How do settings file edits take effect? → A: Via a "Reload settings" tray item; settings are
  also loaded at startup. No automatic file watching.
- Q: Should GesCRTL start automatically at Windows sign-in in Phase 1? → A: No; manual launch
  only. Auto-start is deferred to Phase 7/10.

### Session 2026-10-11 (after the first live tests)

- Q: How should scrolling work? → A: Like holding a mouse scroll wheel. A fist with the thumb out
  sideways is the "wheel click"; tilting the thumb up or down scrolls up or down, faster the more
  it is tilted, and stops when the thumb returns to where it started. Moving the hand does not
  scroll. (Hand-travel scrolling was awkward and the two-finger pose was confused with pinching.)
- Q: What is neutral (no scrolling)? → A: The thumb angle at the moment the pose is recognized.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn on control and move the cursor safely (Priority: P1)

A user launches GesCRTL, sees that it is paused, shows an open palm to start, and moves the cursor
across the whole primary screen by moving one relaxed hand within a comfortable area in front of
the camera. They can freeze the cursor with a flat hand (upright, palm toward the camera, fingers together,
thumb tucked across the palm), pause control by holding that flat hand longer, and stop everything instantly with
a keyboard shortcut.

**Why this priority**: Cursor movement with safe on/off is the smallest experience that proves
GesCRTL works as an input device. Every other action builds on it, and the constitution requires
safety controls from the first usable release.

**Independent Test**: Launch the app, resume with an open palm, reach all four screen corners and
the center, freeze with a flat hand, pause with a longer flat hand, resume again, and use the emergency
shortcut—all without touching the mouse or touchpad.

**Acceptance Scenarios**:

1. **Given** GesCRTL has just launched, **When** the user does nothing, **Then** it is Paused, the
   indicator shows "Paused" with the hint to show an open palm, and the cursor does not move.
2. **Given** GesCRTL is Paused, **When** the user holds an open palm toward the camera for the
   resume hold time, **Then** it becomes Active in Pointer Mode and the indicator shows "Pointer".
3. **Given** GesCRTL is Active, **When** the user moves their relaxed hand within the active
   region, **Then** the cursor follows smoothly and can reach every edge and corner of the primary
   screen.
4. **Given** GesCRTL is Active, **When** the user shows a flat hand (upright, palm toward the
   camera, fingers together, thumb tucked across the palm), **Then** the cursor stays frozen while
   the flat hand is held and resumes following when it is released (clutch). A fist also freezes the cursor
   but is neither a clutch nor a pause.
5. **Given** GesCRTL is Active, **When** the user holds the flat hand for the pause hold time, **Then**
   GesCRTL becomes Paused and stops moving the cursor.
6. **Given** any state except Inactive, **When** the user presses the emergency-stop shortcut,
   **Then** GesCRTL becomes Paused immediately with all held input released, and the indicator
   shows "Stopped" then "Paused".
7. **Given** GesCRTL is Active, **When** the user's hand leaves the camera view, **Then** the
   indicator shows "Hand not visible" within 1 second, and when the hand returns control resumes
   automatically in Pointer Mode.
8. **Given** any state, **When** the user chooses "Turn off" (shortcut or tray), **Then** the
   camera is released and the indicator is hidden; "Turn on" returns to Paused.

---

### User Story 2 - Click, double-click, and right-click (Priority: P2)

A user points at an item and pinches thumb and index finger to left-click, pinches twice quickly
to double-click, and pinches thumb and middle finger to right-click. The cursor does not jump at
the moment of pinching, so clicks land where the user aimed.

**Why this priority**: Clicking turns cursor movement into useful work (opening files, pressing
buttons, following links).

**Independent Test**: On a test page with targets of three sizes, the user left-clicks,
double-clicks, and right-clicks targets and the click success rate and accidental-click count are
recorded.

**Acceptance Scenarios**:

1. **Given** the cursor is over a button, **When** the user taps a thumb–index pinch, **Then**
   exactly one left click occurs at the position the cursor had when the pinch began.
2. **Given** the cursor is over a file icon, **When** the user makes two thumb–index pinch taps
   within the system double-click time, **Then** one double-click occurs.
3. **Given** the cursor is over an item, **When** the user taps a thumb–middle pinch, **Then**
   exactly one right click occurs and the context menu opens.
4. **Given** the user's fingers hover near pinching distance without clearly pinching, **When**
   the distance fluctuates around the threshold, **Then** no click occurs (separate start and
   release conditions prevent flicker).
5. **Given** a right click just occurred, **When** the user pinches again within the right-click
   cooldown, **Then** no second right click is sent.
6. **Given** GesCRTL is Active, **When** the user slowly closes a thumb–index pinch, **Then** the
   cue around the cursor shows the pinch progressing, flashes when the click is sent, and returns
   to the ready ring after release.

---

### User Story 3 - Drag and scroll (Priority: P3)

A user holds a thumb–index pinch to grab an item and moves their hand to drag it, releasing the
pinch to drop. With a fist and the thumb sticking out sideways, tilting the thumb up or down
scrolls the content under the cursor, faster the more it is tilted (like a held scroll wheel).

**Why this priority**: Dragging and scrolling complete the everyday mouse vocabulary (moving files,
selecting text, reading long pages).

**Independent Test**: The user drags a file from one folder window to another and scrolls a long
document from top to bottom and back, without a physical mouse.

**Acceptance Scenarios**:

1. **Given** the cursor is over a file, **When** the user holds a thumb–index pinch longer than the
   drag hold time and moves their hand, **Then** the file is dragged; **When** they release the
   pinch, **Then** it is dropped at the cursor position.
2. **Given** a drag is in progress, **When** the hand leaves the camera view (loss confirmed),
   **Then** the mouse button is released immediately and the drag does not continue when the hand
   returns.
3. **Given** a drag is in progress, **When** the user triggers pause or the emergency stop,
   **Then** the mouse button is released immediately.
4. **Given** the cursor is over a scrollable page, **When** the user makes a fist with the thumb
   out sideways and holds it level, **Then** nothing scrolls; **When** they tilt the thumb up,
   **Then** the page scrolls up, and **When** they tilt it down, **Then** it scrolls down, in both
   cases faster the more the thumb is tilted from where it started; the cursor does not move while
   scrolling.
5. **Given** the user is scrolling, **When** they return the thumb to where it started, **Then**
   scrolling stops; **When** they open the fist or make any other pose, **Then** scrolling stops
   at once and normal cursor movement resumes.
6. **Given** the user forms the pose with the thumb already tilted (for example a classic
   thumbs-up), **Then** nothing scrolls until the thumb is tilted away from that starting angle.

---

### User Story 4 - Adjust sensitivity and restore defaults (Priority: P4)

A user who finds the cursor too fast, too slow, or too jittery can adjust the active region size,
smoothing, and gesture timing in a settings file, restart or reload, and reset everything to
defaults if they make a mistake.

**Why this priority**: Different users, cameras, and desks need small adjustments; without them
some users cannot use the MVP. A full settings screen comes in Phase 7.

**Independent Test**: Change the active region size in the settings file, reload, and confirm the
hand travel needed to cross the screen changed; then reset and confirm defaults return.

**Acceptance Scenarios**:

1. **Given** default settings, **When** the user changes the active region size, saves the file,
   and chooses "Reload settings" from the tray, **Then** the hand travel required to reach screen
   edges changes accordingly without restarting; saving the file alone changes nothing.
2. **Given** a settings file with an invalid value (e.g., negative size), **When** GesCRTL loads
   it, **Then** it uses the default for that value, keeps running, and tells the user which value
   was rejected.
3. **Given** modified settings, **When** the user chooses "Reset to defaults" (tray), **Then** all
   values return to defaults and the settings file is rewritten.
4. **Given** the settings file, **When** the user looks for safety controls, **Then** emergency
   stop, pause, and release-on-loss cannot be disabled from settings.

---

### User Story 5 - Record and replay hand sessions for verification (Priority: P5)

A contributor records a session of hand movements (hand-position data only, no images) and
replays it through GesCRTL's gesture logic without a camera, getting the same sequence of
actions every time. This makes every gesture and state change automatically testable.

**Why this priority**: Required by constitution Principle IV; it protects every later change from
regressions. It is P5 only because it does not add end-user value directly—it is still mandatory
for this phase.

**Independent Test**: Record a 30-second session containing clicks, a drag, a scroll, and a hand
loss; replay it twice; both replays produce identical action sequences, and no camera is used.

**Acceptance Scenarios**:

1. **Given** GesCRTL is running, **When** a contributor starts a recording, **Then** hand-position
   data and timestamps are saved in the project's recording format and no images are saved.
2. **Given** a recording, **When** it is replayed, **Then** the produced states and actions are
   identical on every replay and no input is sent to the operating system.
3. **Given** a bug where a gesture misfired, **When** the contributor saves the recording as a
   test case, **Then** it becomes part of the automated test suite.

---

### Edge Cases

- **Second hand or another person in view**: Only the primary hand controls; other hands never
  move the cursor or click, even when the primary hand leaves the view (see FR-033).
- **Pinch held when tracking is lost**: Button released immediately on confirmed loss; on return,
  no automatic re-press.
- **Single-frame tracking flicker**: Brief detection gaps shorter than the loss-confirmation window
  do not end a drag or change state.
- **Hand at the edge of the active region**: Cursor stays at the screen edge (clamped), never jumps.
- **Pinch begins while moving fast**: The click lands where the cursor was at pinch start
  (click stabilization).
- **Display scaling at 125% or 150%**: Cursor reaches all edges and corners accurately.
- **Camera taken by another app or unplugged**: Indicator shows "Camera unavailable"; any held
  button is released; control resumes automatically when the camera and hand return.
- **Emergency shortcut cannot be registered (taken by another app)**: GesCRTL warns the user and
  does not enter Active until a working emergency path exists (tray stop remains available).
- **Mode-menu gesture (three fingers)**: Has no effect in this phase (mode system arrives in
  Phase 3) and must not trigger any other action.
- **Elevated (administrator) window in focus**: Input may be ignored by Windows; GesCRTL does not
  crash and the limitation is documented.
- **Crash or forced exit during a drag**: Held buttons are released by the exit handler.
- **Low light / low confidence**: No clicks, drags, or scrolls are sent; cursor movement pauses
  rather than jumping.

## Requirements *(mandatory)*

### Functional Requirements

**States and control**

- **FR-001**: The system MUST implement the Phase 0 interaction model for Pointer Mode: states
  Inactive, Paused, Active (Normal, Clutched), and Tracking Lost, with transitions exactly as
  defined in `docs/interaction/interaction-model.md` (or, until it exists,
  `specs/001-product-foundation/data-model.md`).
- **FR-002**: The system MUST start in Paused and MUST NOT send any input until the user performs
  the resume gesture or uses the resume shortcut/tray item.
- **FR-003**: Users MUST be able to pause with the pause gesture (flat hand held for the pause hold
  time), the pause/resume shortcut, or the tray; and resume with the resume gesture (open palm held
  for the resume hold time), the shortcut, or the tray.
- **FR-004**: The system MUST provide an emergency stop via a global keyboard shortcut (default
  `Ctrl+Alt+Esc`) and the pause gesture; it MUST release all held input and move to Paused within
  200 ms.
- **FR-005**: Users MUST be able to turn control off (camera released) and on via shortcut or tray,
  and exit from the tray.
- **FR-006**: When the primary hand is missing for the loss-confirmation window, the system MUST
  enter Tracking Lost, release all held input immediately, and resume automatically in Pointer Mode
  when the primary hand reappears.
- **FR-007**: Only one primary hand MUST control the cursor at a time, selected and kept per the
  Phase 0 primary-hand rules; other hands MUST produce no input.
- **FR-008**: If no emergency path can be registered, the system MUST warn the user and remain
  Paused until one is available.

**Pointer actions**

- **FR-009**: In Active·Normal, the cursor MUST follow the smoothed position of a stable point on
  the hand (palm center), mapped from the active region to the full primary monitor using the
  pointer mapping model chosen in Phase 0 (decision record 0005).
- **FR-010**: Cursor positions MUST be correct at any display scaling on the primary monitor
  (at minimum 100%, 125%, 150%).
- **FR-011**: A thumb–index pinch tap MUST produce one left click; two taps within the system
  double-click time MUST produce one double-click; a thumb–middle pinch tap MUST produce one right
  click.
- **FR-012**: At pinch start, the cursor MUST be held at its pinch-start position for the click
  stabilization time so the click lands where the user aimed.
- **FR-013**: A thumb–index pinch held longer than the drag hold time MUST press and hold the left
  button and move the cursor with the hand; releasing the pinch MUST release the button.
- **FR-014**: A fist with the thumb out and clear of the index fingertip MUST scroll vertically
  like a held scroll wheel: the thumb angle when the pose is recognized is neutral; tilting the
  thumb up scrolls up and tilting it down scrolls down, with speed rising smoothly with the tilt
  (a small dead zone around neutral does nothing, and speed is capped). No scrolling occurs while
  the pose is still settling, when the thumb is at its starting angle, or after the pose ends; hand
  movement MUST NOT scroll and the cursor MUST NOT move during scrolling. Speed per degree of tilt
  and the maximum speed MUST be adjustable.
- **FR-015**: The flat hand (clutch) MUST freeze the cursor without any other action. Held for the pause
  hold time (1.5 s) it MUST pause. A fist MUST also freeze the cursor and release held input, but
  never pauses.
- **FR-016**: The mode-menu gesture MUST have no effect in this phase.

**Safety (constitution Principle I)**

- **FR-017**: No click, drag, or scroll MUST be sent when tracking confidence is below the
  configured threshold or the gesture has not been stable for the minimum number of frames.
- **FR-018**: Every pinch MUST use separate start and release thresholds (hysteresis); repeatable
  discrete actions MUST respect their cooldowns (values from `docs/interaction/safety-policy.md`).
- **FR-019**: All held buttons MUST be released on pause, emergency stop, tracking loss, turn off,
  exit, and unexpected failure.
- **FR-020**: Emergency stop, pause, and release-on-loss MUST NOT be disableable through settings.

**Feedback (constitution Principle III)**

- **FR-021**: An on-screen indicator MUST show the current state and mode as defined in the Phase 0
  HUD concept, MUST never take focus or block clicks, and MUST update within 200 ms of a state
  change (within 1 second for hand or camera loss).
- **FR-021a**: While Active, a small cursor cue MUST always be shown around the cursor. It MUST:
  - show a ready ring in Active·Normal;
  - show pinch progress as the fingers close;
  - flash briefly when a click is sent;
  - show distinct looks while dragging, scrolling, and clutched.

  It MUST be hidden in Paused, Tracking Lost, and Inactive. Like the indicator, it MUST never take
  focus or intercept clicks, and MUST never show camera imagery. It MUST update within 100 ms of
  the gesture change.
- **FR-022**: On entering Active, the indicator MUST briefly show Pointer Mode hints (at most 4).
- **FR-023**: A tray icon MUST show On/Off state and offer Resume/Pause, Turn off/Turn on, Reload
  settings, Reset to defaults, and Exit.

**Settings (constitution Principle VIII)**

- **FR-024**: Active region size, smoothing strength, scroll speed, hold times, pinch thresholds,
  and cooldowns MUST be adjustable in a human-readable settings file stored in the user's profile.
- **FR-024a**: Settings MUST be loaded at startup and re-applied only when the user chooses
  "Reload settings" from the tray. Reloading MUST release any held input first, and MUST NOT change
  the current state or mode. Saving the file without reloading MUST have no effect.
- **FR-025**: Invalid settings values MUST be replaced by defaults with a user-visible notice; the
  app MUST keep running.
- **FR-026**: Users MUST be able to reset all settings to defaults from the tray.
- **FR-027**: The app MUST work with default settings without any configuration (first launch).

**Verification (constitution Principle IV) and privacy (Principle VI)**

- **FR-028**: Contributors MUST be able to record sessions as hand-position data with timestamps in
  the Phase 0 landmark recording format; images MUST never be saved.
- **FR-029**: Recorded sessions MUST be replayable through the gesture and state logic without a
  camera, producing identical state and action sequences on every replay and sending no OS input.
- **FR-030**: Every gesture and state transition in this phase MUST be covered by at least one
  replay-based automated test.
- **FR-031**: All camera processing MUST happen on-device in memory; the app MUST make no network
  connections.

**Performance (constitution Principle V)**

- **FR-032**: The system MUST record per-stage timing so delay, tracking rate, and CPU use can be
  measured on demand.

**Reliability hardening (roadmap Phase 2)**

- **FR-033** (H1): The primary hand MUST stay locked to the hand that resumed control, followed by
  position continuity. If the primary hand disappears while another hand stays in view, control
  MUST NOT pass to the other hand; the system enters Tracking Lost instead. On return with several
  hands, the hand nearest the last primary position is chosen.
- **FR-034** (H2): When the camera is unplugged or taken by another app, the indicator MUST show
  "Camera unavailable" (with the cause when known) within 1 second and all held input MUST be
  released. The system MUST retry the camera automatically and resume when it and the hand return,
  without restarting the app.
- **FR-035** (H3): Frames with low tracking confidence or an implausible jump of the hand position
  MUST be ignored: no action is started from them, the cursor holds still, and they count toward
  tracking loss.
- **FR-036** (H4): A benchmark tool MUST replay recorded sessions and report the number of
  unintended actions per scenario (idle hand, typing, talking, second person), plus live delay,
  tracking rate, and CPU use.
- **FR-037** (H5): Every safety value still marked provisional in
  `docs/interaction/safety-policy.md` MUST be tuned on recorded sessions, and the measured value
  MUST become the default.
- **FR-038** (H6): Activation, pause, and resume MUST be reviewed after Phase 1 use. Any change
  and its reason MUST be recorded in the phase retrospective.

### Key Entities

- **Application State**: Inactive, Paused, Active (Normal / Clutched), Tracking Lost; governs
  whether input may be sent and whether the camera runs.
- **Primary Hand**: The single hand currently in control; its smoothed anchor position drives the
  cursor.
- **Gesture Event**: A recognized hand form (relaxed, pinch thumb–index, pinch thumb–middle,
  thumbs-up, fist, open palm, flat hand) with start/end times and confidence.
- **Pointer Action**: Cursor move, left click, double-click, right click, drag start/end, scroll
  amount; consequential actions are subject to safety rules.
- **Settings**: User-adjustable values with defaults and allowed ranges; safety controls excluded.
- **Session Recording**: Timestamped hand-position frames (no images) used for replay tests.
- **Indicator Status**: What the on-screen indicator, the cursor cue (ready, pinch progress, click,
  dragging, scrolling, clutched), and the tray currently show.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can resume control within 30 seconds of launching, guided only by
  the on-screen hint.
- **SC-002**: A user can complete a scripted desktop task set—open a folder, open a document,
  scroll to its end and back, drag a file into another folder, use a right-click menu, and close
  two windows—without touching a mouse, touchpad, or keyboard (except the emergency shortcut if
  needed) in under 5 minutes.
- **SC-003**: The cursor reacts to hand movement within 80 ms for 95% of movements, and tracking
  updates at 25 or more times per second on the reference laptop.
- **SC-004**: Zero unintended clicks, drags, or scrolls occur during a 10-minute session in which
  the user's hands are visible but not controlling (typing, talking, gesturing).
- **SC-005**: At least 90% of left clicks on 48-pixel targets land on the target on the first try.
- **SC-006**: Emergency stop and pause take effect within 200 ms in 100% of trials; held buttons are
  released within 200 ms of confirmed tracking loss in 100% of trials.
- **SC-007**: The cursor can reach all four corners and edges of the primary screen at 100%, 125%,
  and 150% display scaling.
- **SC-008**: CPU use while Paused or with no hand present stays within the idle budget set in
  Phase 0.
- **SC-009**: Every gesture and state transition in this phase has a passing replay-based test, and
  replaying the same recording twice yields identical results.
- **SC-010**: No image file is ever written and no network connection is made during a full test
  session.
- **SC-011**: With a second hand or person in view, the non-primary hand causes zero actions, both
  in replay tests and in a recorded second-person session.
- **SC-012**: In 5 out of 5 camera interruptions (unplug, Windows Camera app taking the camera),
  "Camera unavailable" appears within 1 second, held input is released, and control resumes
  without restarting the app.
- **SC-013**: The replay benchmark reports zero unintended actions over at least 10 minutes of
  recorded idle, typing, and talking sessions using the final tuned defaults, and
  `safety-policy.md` has no provisional values left.

## Assumptions

- Phase 0 is complete or near complete; its interaction model, gesture vocabulary, safety policy,
  HUD concept, and decision records are used as inputs. Provisional Phase 0 values are replaced by
  measured values before or during planning.
- Single user, single primary monitor, Windows 10/11 laptop or desktop with a built-in or standard
  USB webcam; multi-monitor support is Phase 9.
- Horizontal scrolling is out of scope for this phase; only vertical scrolling is supported.
- Settings are adjusted by editing a file plus tray actions; a graphical settings screen is
  Phase 7.
- The mode menu and other modes (Keyboard, Presentation, Media/System) are out of scope; only
  Pointer Mode exists in this phase.
- Reliability hardening (roadmap Phase 2) is part of this spec (FR-033–FR-038). Sharing the
  camera with a video-call app at the same time is not supported; GesCRTL reports the camera as
  unavailable and recovers when it is free.
- Default shortcuts: `Ctrl+Alt+Esc` emergency stop, `Ctrl+Alt+P` pause/resume, `Ctrl+Alt+O`
  turn off/on.
- GesCRTL is launched manually; starting automatically at Windows sign-in is out of scope for
  this phase (deferred to Phase 7 settings / Phase 10 installer).
- Packaging into an installer is not required for this phase; running from a development setup is
  acceptable for the demo (installer is Phase 10).
- "Reference laptop" means the same hardware used for the Phase 0 feasibility measurements.
