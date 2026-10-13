# Feature Specification: Keyboard Mode, Personalization, Custom Gestures, and Calibration

**Feature Branch**: `004-keyboard-personalization`

**Created**: 2026-10-13

**Status**: Implemented; the manual validation session is pending

**Input**: User description: "Spec 004: follow Plan.md phases 5 (Keyboard Mode, 5a only; 5b
two-handed air typing deferred), 7 (Settings and Personalization), 8 (Custom Gesture Learning),
and 9 (Calibration, Multi-Monitor, and Accessibility Improvements), as written in Plan.md §4."

## Overview

Specs 002 and 003 delivered Pointer, Presentation, and Media/System modes, a settings file with
validation, reload, and reset, and a tray menu. This spec completes the product's input range
and lets users adapt it to themselves:

- **Keyboard Mode** (Phase 5a): an on-screen keyboard for short text entry and common shortcuts.
  Two-handed air typing (5b) is deferred.
- **Settings and personalization** (Phase 7): a settings window for the key values, gesture to
  action mapping, and reset to defaults, without editing files.
- **Custom gestures** (Phase 8): the user records their own gesture and assigns it to an allowed
  action. Custom gestures never override safety controls.
- **Calibration, multi-monitor, accessibility** (Phase 9): a guided calibration, cursor control
  across several monitors with mixed scaling, and alternatives for users who cannot comfortably
  pinch or make large movements.

It must satisfy the constitution, in particular Principle I (Safety First), Principle II
(learned gestures must not destabilize the release), and Principle IV (Deterministic, Testable
Core).

**Dependency**: specs 002 and 003 (state machine, modes and mode menu, HUD, settings file, tray,
replay and benchmark tools).

## Clarifications

### Session 2026-10-13

- Q: Should a custom gesture be a still hand shape only, or can it also be a movement? → A: Both: still hand shapes (held briefly) and movements (for example a circle, a wave, a zigzag).
- Q: With two or more monitors, does the hand's movement range cover all monitors as one area, or one monitor at a time? → A: All monitors as one area; no switching step and no new gesture.
- Q: In which modes are custom movement gestures recognized? → A: Movements and shapes in every mode, including Pointer; in Pointer Mode the cursor moves while a movement gesture is performed, and that is accepted.
- Q: How is a key pressed on the on-screen keyboard by default? → A: Pinch by default; dwell as a setting. In addition, two-handed pressing: one hand points at keys while the user's other hand pinches to press (Keyboard Mode only; requires amending the one-primary-hand rule, Principle I).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type short text and use shortcuts (Priority: P1)

A user picks Keyboard from the mode menu. An on-screen keyboard appears. They point at a key and
confirm it, and the character goes to the application they were using. A row of shortcut keys
gives copy, paste, undo, Alt+Tab, and the Windows key in one action.

**Why this priority**: Keyboard Mode is the last of the four planned modes and has been shown as
"Later" since spec 003. It is the largest user-visible gap.

**Independent Test**: With a text editor focused, switch to Keyboard Mode and type a short phrase,
correct a mistake with Backspace, press Enter, and copy and paste a word with the shortcut row,
without touching the physical keyboard.

**Acceptance Scenarios**:

1. **Given** Keyboard Mode, **When** it opens, **Then** an on-screen keyboard appears that never
   takes focus or clicks away from the foreground application, and the mode menu no longer shows
   Keyboard as unavailable.
2. **Given** Keyboard Mode, **When** the user moves the hand, **Then** a highlight moves over the
   keys. Hand movement covers only the keyboard area, so a small movement reaches every key.
3. **Given** a key is highlighted, **When** the user confirms it, **Then** exactly one key press
   goes to the foreground application and the key flashes. A held confirmation never repeats a
   key, except Backspace and the arrow keys, which repeat after a delay.
4. **Given** the user selects a modifier (Shift, Ctrl, Alt, Win), **When** they then select
   another key, **Then** the combination is sent once and the modifier clears. Selecting the
   modifier twice locks it until it is selected again. Its state is always visible.
5. **Given** the shortcut row, **When** the user selects Copy, Paste, Cut, Undo, Redo, Select
   all, Alt+Tab, Win, or Esc, **Then** that shortcut is sent once.
6. **Given** keys were typed, **When** the user looks at the keyboard, **Then** a strip shows the
   last characters sent, so they can see what was typed without looking away.
7. **Given** Keyboard Mode with a modifier active or a key held, **When** the user pauses, loses
   tracking, uses emergency stop, or changes mode, **Then** every key and modifier is released
   and locked modifiers clear.
8. **Given** Keyboard Mode and the user's second hand in view, **When** the pointing hand rests
   on a key and the second hand pinches, **Then** that key is pressed exactly once; the
   pointing hand's own pinch also still presses keys. A hand from another person never presses.
9. **Given** the keyboard covers the text the user is typing into, **When** they select the
   move key, **Then** the keyboard moves between the top and bottom of the screen.

---

### User Story 2 - Adjust GesCRTL without editing files (Priority: P2)

A user opens Settings from the tray. They change cursor speed and smoothing, movement range,
hold times, and the confirmation method, see the effect right away, and can reset everything to
defaults. They can also choose which allowed action certain gestures trigger.

**Why this priority**: Phase 7 exit criterion: users adjust the key experience and restore
defaults without editing source code or files.

**Independent Test**: From the tray, open Settings, change the movement range and a hold time,
confirm the change in Pointer Mode, remap a presentation swipe, then reset to defaults and
confirm the original behavior returns, without opening the settings file.

**Acceptance Scenarios**:

1. **Given** the app is running, **When** the user picks Settings from the tray, **Then** a
   settings window opens with grouped, labelled controls showing the current values and their
   allowed ranges.
2. **Given** the settings window, **When** the user changes a value and applies it, **Then** it
   takes effect without restarting and is saved for the next launch.
3. **Given** an invalid or out-of-range value, **When** the user tries to apply it, **Then** it
   is rejected with a message naming the field, and the previous value is kept.
4. **Given** the remapping page, **When** the user assigns an allowed action to a remappable
   gesture, **Then** that gesture triggers the new action from then on. Safety gestures (pause,
   resume, emergency stop, mode menu) do not appear as remappable.
5. **Given** any changed settings, **When** the user chooses Reset to defaults and confirms,
   **Then** all values, mappings, and calibration return to defaults. Custom gestures are kept
   but disabled.
6. **Given** the settings window, **When** the user turns on "Start with Windows", **Then**
   GesCRTL starts paused at the next sign-in. It is off by default.

---

### User Story 3 - Calibrate to my hand, camera, and reach (Priority: P2)

A first-time user, or someone with limited movement, runs a short guided calibration. It checks
lighting and hand distance, asks them to reach comfortably to each screen corner, and records an
open hand and a pinch. The movement range and pinch sensitivity are then set to fit them.

**Why this priority**: The defaults were measured on one laptop and one person. Calibration
makes the product work for other people and setups, and it is the main reduced-movement option.

**Independent Test**: Run calibration from the tray. After it finishes, all four screen corners
can be reached with the user's comfortable movement, and pinch clicks work at the measured
thresholds. Cancel a second run halfway and confirm nothing changed.

**Acceptance Scenarios**:

1. **Given** calibration starts, **When** the camera is too dark, too slow, or the hand is too
   far or too close, **Then** the user is told what is wrong and how to fix it before continuing.
2. **Given** the reach step, **When** the user points to each corner as comfortably as they can,
   **Then** the movement range is set so those positions reach the screen corners.
3. **Given** the pinch step, **When** the user shows an open hand and several pinches, **Then**
   the pinch thresholds are set from their samples, keeping hysteresis (enter below release).
4. **Given** calibration finishes, **When** the user reviews the result, **Then** they can keep
   it or discard it; kept values appear in Settings and can be reset.
5. **Given** calibration is running, **When** the user cancels, pauses, or tracking is lost for
   more than a few seconds, **Then** calibration stops and no setting changes.
6. **Given** calibration is running, **Then** no clicks, keys, or cursor moves are sent.

---

### User Story 4 - Use GesCRTL across several monitors (Priority: P3)

A user with a laptop and an external monitor at different scaling moves the cursor onto either
screen and clicks precisely on both. Overlays appear on a predictable screen.

**Why this priority**: Multi-monitor is a common desk setup and a known limitation since spec
002, but single-monitor use already works.

**Independent Test**: With two monitors at different scaling (for example 150% and 100%), reach
all four corners of each monitor and click a 48 px target near the middle and near each corner
of both screens.

**Acceptance Scenarios**:

1. **Given** two or more monitors, **When** the user moves the hand, **Then** the cursor can
   reach every monitor: the movement range covers all monitors as one area, so moving the hand
   across the range sweeps across every screen, with no switching step.
2. **Given** monitors with different scaling, **When** the cursor crosses between them, **Then**
   it lands where expected, with no jump or offset, and clicks hit 48 px targets on each.
3. **Given** a monitor is connected, disconnected, or its scaling changes while running, **When**
   the layout changes, **Then** the mapping updates within 2 s, and the cursor never goes to an
   area that no longer exists.
4. **Given** several monitors, **When** the HUD, mode menu, level panel, or on-screen keyboard
   opens, **Then** it appears on the monitor chosen in Settings (default: the primary monitor).

---

### User Story 5 - Teach GesCRTL my own gesture (Priority: P4)

A user records a gesture of their own, gets feedback on recording quality, assigns it to an
allowed action (for example "play/pause" or "copy"), and later retrains, disables, or deletes it.

**Why this priority**: Phase 8 is advanced and, by the constitution, must not block or
destabilize the other stories. It ships only if it meets its measured reliability; otherwise it
stays disabled and documented.

**Independent Test**: Enroll a custom gesture, assign it to play/pause, trigger it 20 times in
Media/System Mode, then replay 10 minutes of non-control recordings and count false triggers.
Then disable and delete it.

**Acceptance Scenarios**:

1. **Given** the custom gestures page in Settings, **When** the user starts recording, **Then**
   they are guided through several short takes, with live feedback on whether the hand is fully
   visible and the takes are consistent.
2. **Given** the takes are recorded, **When** the gesture is too similar to a built-in gesture
   or another custom gesture, **Then** enrollment is refused with an explanation, and the user
   can record again.
3. **Given** a gesture was enrolled, **When** the user assigns an action, **Then** only allowed
   actions can be chosen. Clicks, pause, resume, emergency stop, mode menu, and Turn off are
   never assignable.
4. **Given** an enabled custom gesture, **When** the user performs and holds it, **Then** its
   action runs once, with the same confidence, stable-frame, hold, and cooldown rules as built-in
   gestures, and the HUD names it.
5. **Given** a custom gesture, **When** the user retrains, disables, or deletes it, **Then** the
   change takes effect at once.
6. **Given** a custom gesture is enrolled, **Then** only hand landmark data is stored, never
   camera images.
7. **Given** the recording step, **When** the user records a gesture, **Then** they choose its
   kind: a still hand shape (held briefly) or a movement (for example a circle, a wave, a
   zigzag). A movement too similar to an open-hand swipe is refused like any other conflict.

---

### Edge Cases

- A modifier is locked when the app pauses, crashes, or exits: it is released (ReleaseAll covers
  modifiers sent from Keyboard Mode).
- In Keyboard Mode a second person's hand appears next to the user: it is ignored unless it
  passes the same-person check in FR-003a; if both hands of the user pinch at once, one key
  press is sent.
- Two hands overlap or cross in the image: tracking may swap or lose them; nothing is pressed
  until both are seen stably again.
- The foreground window is elevated or on the secure desktop: keys are ignored by Windows; the
  existing known limitation applies.
- The user switches application with Alt+Tab from the shortcut row: the keyboard stays on top and
  keys go to the new foreground window.
- A non-US keyboard layout is active: the keys sent produce the characters shown on the
  on-screen keyboard (the keyboard shows the active layout or sends characters, not scan codes).
- The settings file is edited by hand while the window is open: the window shows the reloaded
  values; invalid values fall back to defaults with a warning, as today.
- A remapping makes two gestures trigger the same action: allowed. A gesture can only have one
  action per mode.
- The custom gestures file is missing or damaged: custom gestures are disabled with a warning;
  everything else works.
- A custom gesture resembles a built-in one only in certain lighting or angles: if it fires a
  built-in gesture's action or a built-in gesture fires it during use, the user can disable it at
  once from Settings or the tray.
- A movement gesture is performed in Pointer Mode: the cursor ends wherever the hand ended; no
  click is sent, and the action runs once. Users who dislike this can disable the gesture or
  limit it to other modes.
- Calibration produces an extreme result (tiny range, thresholds outside allowed limits): values
  are clamped to the allowed ranges and the user is told.
- The monitor with the keyboard or HUD is disconnected: the overlays move to the primary monitor.
- Monitors are arranged with gaps or different heights: the cursor never stops in an area with
  no screen; it clamps to the nearest monitor edge.

## Requirements *(mandatory)*

### Functional Requirements

**Keyboard Mode**

- **FR-001**: Keyboard Mode MUST be selectable from the mode menu and the tray, like the other
  modes, and MUST show an on-screen keyboard that never takes focus or clicks.
- **FR-002**: The keyboard MUST include letters, digits, space, Backspace, Enter, Tab, Esc,
  arrow keys, Shift, Ctrl, Alt, Win, and basic punctuation, with keys at least 48 px.
- **FR-003**: Key selection MUST map hand movement onto the keyboard area only and show a
  highlight on the current key. Key confirmation MUST use the user's chosen confirmation method:
  pinch (default) or dwell (holding still on a key for a set time, default 800 ms).
- **FR-003a**: In Keyboard Mode only, the user's second hand MUST be able to type too
  (two-handed typing, decided 2026-10-13 after the first manual test): each hand points at its
  own key with its own highlight and presses it with its own pinch (or dwell); whichever hand
  presses first sends first, and both hands on the same key together press it once. The primary
  hand still owns every other gesture; the second hand never moves the cursor or changes state
  or mode. It is accepted only if it is the opposite hand
  (left/right) of the primary hand, is seen with the required confidence and stable frames, and
  is consistent with belonging to the same person (for example close to the primary hand in the
  image); any other hand is ignored. Losing the second hand presses nothing and releases
  nothing extra; losing the primary hand releases everything as usual. Two-handed pressing can
  be turned off in Settings.
- **FR-003b**: Before implementation, the constitution's one-primary-hand rule (Principle I)
  MUST be amended to allow this Keyboard-Mode-only typing hand, and the decision MUST be
  recorded in an ADR. Every other mode keeps one controlling hand.
- **FR-004**: A confirmation MUST send exactly one key press. Backspace and the arrow keys MAY
  repeat while held, after an initial delay.
- **FR-005**: Modifiers MUST work as one-shot (apply to the next key) or locked (selected twice),
  and their state MUST be visible.
- **FR-006**: A shortcut row MUST offer Copy, Paste, Cut, Undo, Redo, Select all, Alt+Tab, Win,
  and Esc.
- **FR-007**: The keyboard MUST show the last characters sent, flash each pressed key, and be
  movable between the top and bottom of the screen.
- **FR-008**: Every key and modifier MUST be released, and locked modifiers cleared, on pause,
  loss, emergency stop, mode change, exit, or exception.
- **FR-009**: Global gestures (pause, resume, mode menu, level panel) MUST keep their meaning in
  Keyboard Mode; no new built-in gesture is added for typing.

**Settings and personalization**

- **FR-010**: A settings window, opened from the tray, MUST let the user view and change at
  least: movement range, cursor smoothing and speed, confidence and stability, hold times and
  cooldowns, the confirmation method and dwell time, scroll speed, keyboard position, overlay
  monitor, and Start with Windows.
- **FR-011**: Changes MUST be validated with clear messages, applied without restart, and saved.
  The settings file remains the single stored source; hand edits keep working.
- **FR-012**: Users MUST be able to assign an allowed action to each remappable gesture per mode:
  the presentation swipes and thumb up/down, the targets on the Media/System grid, and custom
  gestures. Safety gestures and the emergency stop MUST NOT be remappable or disableable.
- **FR-013**: Reset to defaults MUST restore all values, mappings, and calibration, after a
  confirmation. Custom gestures are kept but disabled.
- **FR-014**: Start with Windows MUST be off by default; when on, the app starts Paused.

**Calibration and accessibility**

- **FR-015**: A guided calibration, started from the tray or Settings, MUST check lighting
  (camera frame rate) and hand distance, then measure the user's comfortable reach and their
  open-hand and pinch samples.
- **FR-016**: Calibration MUST set the movement range and pinch thresholds from the measurements,
  within allowed ranges and with hysteresis kept, and MUST let the user keep or discard the result.
- **FR-017**: Calibration MUST send no input, and cancelling or interrupting it MUST change
  nothing.
- **FR-018**: For users who cannot comfortably pinch, a dwell confirmation option MUST also be
  available in Pointer Mode (dwell = left click), Media/System targets, the mode menu, and the
  level panel, not only in Keyboard Mode. Dwell clicks MUST need the cursor to stay still and
  MUST NOT repeat without the cursor leaving and coming back.
- **FR-019**: A reduced-movement option MUST be available: a smaller movement range (set by
  calibration or by hand), so that a small hand movement covers the screen.

**Multi-monitor**

- **FR-020**: The movement range MUST map onto all connected monitors as one area (the bounding
  area of the desktop), so the cursor reaches every monitor without a switching step, with
  correct positions on monitors with mixed scaling. Parts of that area with no screen clamp to
  the nearest monitor edge. No new gesture is added.
- **FR-021**: Changes in monitor layout or scaling MUST be picked up while running, within 2 s.
- **FR-022**: Overlays (HUD, menus, level panel, keyboard, presentation pointer) MUST appear on
  the monitor chosen in Settings, falling back to the primary monitor if it is missing.

**Custom gestures**

- **FR-023**: Users MUST be able to enroll a custom gesture of either kind, a still hand shape
  or a movement, by recording several takes with guidance and quality feedback. A shape fires
  after it is held; a movement fires once when it is completed, and it must start and end
  within a bounded time window (no open-ended tracking).
- **FR-024**: Enrollment MUST refuse a gesture too similar to a built-in or existing custom
  gesture.
- **FR-025**: A custom gesture MUST be assignable only to an allowed action (media keys,
  shortcuts, slide changes, mode change requests that still go through the menu's rules), and
  MUST need a hold (shapes) or a completed movement, stable frames, confidence, and a cooldown
  before acting. Both kinds work in every mode, including Pointer Mode. In Pointer Mode the cursor
  keeps following the hand while a movement gesture is performed (accepted); a shape freezes the
  cursor once recognized, like the fist.
- **FR-025a**: A custom gesture MUST NOT be recognized while a built-in gesture is in progress
  (pinch, drag, scroll, swipe, open menu or panel, pending confirmation), and performing one MUST
  never send a click, drag, or scroll.
- **FR-026**: Users MUST be able to retrain, disable, and delete each custom gesture, and disable
  all custom gestures at once from the tray.
- **FR-027**: Custom gesture data MUST be hand landmark features only, stored locally next to the
  settings; never images.
- **FR-028**: Custom gestures MUST be off by default and MUST be disabled in the release (with a
  documented limitation) if they do not meet SC-007 and SC-008.

**General**

- **FR-029**: All new recognition and decision logic (key selection and confirmation, dwell,
  custom gesture matching, calibration computations, multi-monitor mapping math) MUST run in the
  pure core and be covered by landmark-replay or unit tests.
- **FR-030**: The README, gesture vocabulary, and known limitations MUST be updated for the new
  mode, settings, calibration, multi-monitor support, and custom gestures.

### Key Entities

- **On-screen keyboard**: The keys, their layout and rows (including the shortcut row), the
  highlighted key, modifier states (off, one-shot, locked), and the recent-text strip.
- **Confirmation method**: Pinch or dwell, with the dwell time; applies to keys and, as an
  accessibility option, to clicks and on-screen targets.
- **Gesture mapping**: For each mode, which remappable gesture triggers which allowed action.
- **Allowed action**: An action a user may assign; excludes clicks and all safety actions.
- **Custom gesture**: A user-named gesture: its kind (still shape or movement), recorded
  landmark-feature samples (single frames for a shape, short timed sequences for a movement), an
  enabled flag, its assigned action, and the mode(s) where it works.
- **Calibration profile**: Measured movement range, pinch thresholds, and the date measured.
- **Display layout**: The connected monitors, their positions and scaling, and the overlay
  monitor.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who has practised for 5 minutes types the phrase "hello world 2026" into a
  text editor in under 90 s, with at most one uncorrected error, in at least 4 of 5 attempts. The
  measured characters per minute are recorded in the docs. No claim of parity with a physical
  keyboard is made.
- **SC-002**: Each shortcut on the shortcut row works on at least 9 of 10 attempts.
- **SC-003**: Across at least 10 minutes of recordings with the hands not controlling (idle,
  typing on the physical keyboard, talking, a second person), Keyboard Mode sends 0 keys, and
  dwell sends 0 clicks or keys. In recordings where a second person pinches near the user,
  0 keys are pressed by that person's hand.
- **SC-004**: Within 200 ms of pause, loss, emergency stop, or mode change, no key or modifier is
  held (100% of trials).
- **SC-005**: A user changes a setting, sees its effect, and restores defaults in under 1 minute
  without opening any file.
- **SC-006**: Calibration takes under 2 minutes. Afterwards, the user reaches all four corners of
  the screen and hits a 48 px target with at least 9 of 10 clicks, for at least 3 different
  people or setups.
- **SC-007**: An enrolled custom gesture is recognized on at least 18 of 20 intended attempts,
  measured separately for still shapes and for movements. If one kind misses the target, only
  that kind is disabled (FR-028).
- **SC-008**: In 10 minutes of non-control recordings and in recordings of all built-in
  gestures, an enrolled custom gesture fires 0 times, and it never changes how a built-in gesture
  is recognized.
- **SC-009**: On two monitors with different scaling, every corner of each monitor can be reached
  and at least 9 of 10 clicks hit a 48 px target on each monitor.
- **SC-010**: Replaying any recorded session twice produces identical events, and every new
  decision in this spec is covered by at least one replay or unit test.

## Assumptions

- Keyboard Mode is for short text (search boxes, names, short messages), not long documents.
  Word suggestions are out of scope; they can be added later if measured typing is too slow.
- The keyboard shows a US English layout. Characters are sent as characters, so they appear
  correctly whatever input language Windows uses.
- Two-handed air typing (Phase 5b, typing with all fingers of both hands) is out of scope. The
  two-handed pressing in FR-003a (one hand points, the other only pinches) is in scope.
- Named profiles are out of scope (Plan: only if real use cases justify them).
- Dwell confirmation is the alternative control for users who cannot comfortably pinch; no other
  alternative input devices (switches, eye tracking) are in scope.
- The settings window is a desktop window opened from the tray; it is used with the physical
  mouse or with Pointer Mode.
- Calibration results and custom gestures are stored locally next to the settings file.
  Nothing is sent over the network.
- Brightness control stays limited to the built-in display, as in spec 003.
- Platform limits in `docs/product/known-limitations.md` still apply to every key sent here.
