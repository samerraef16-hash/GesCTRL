# Feature Specification: Mode System, Presentation Mode, and Media/System Controls

**Feature Branch**: `003-modes-presentation-media`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Spec 003 (roadmap phases 3 + 4 + 6): the mode system with HUD guidance, Presentation Mode, and Media/System controls", per `Plan.md` §3.

## Overview

Spec 002 delivered Pointer Mode: one hand moves the cursor, clicks, drags, and scrolls. This spec
turns GesCRTL from "one set of gestures" into a **coherent input system with modes**. The user
can open a mode menu with a deliberate gesture, pick a mode, always see which mode they are in,
and see only the gestures that matter in that mode. It then adds two new modes that use it:

- **Presentation Mode**: move between slides and point at slide content with a stabilized
  on-screen pointer, from a few metres away, without a remote.
- **Media/System Mode**: play and pause, skip tracks, change volume and screen brightness, mute,
  take a screenshot, and switch application, hands-free, with disruptive actions kept deliberate
  and easy to cancel.

It also adds **quick level controls**: volume and screen brightness can be adjusted from Pointer
Mode (and every other mode) without switching to Media/System Mode.

It builds on the interaction model, gesture vocabulary, safety policy, and HUD concept in
`docs/interaction/` (the mode menu, events E12–E14, and the opening gesture G7 are already
defined there) and must satisfy the constitution, in particular Principle I (Safety First) and
Principle IV (Deterministic, Testable Core).

**Dependency**: spec 002 (state machine, pointer pipeline, HUD, replay and benchmark tools).
Keyboard Mode is spec 004; here it only appears in the menu as unavailable.

## Clarifications

### Session 2026-10-11

- Q: How does the user move to the next or previous slide? → A: Swipe: a fast horizontal hand motion, right = next, left = previous (screen direction, mirrored view).
- Q: How does the user start and steer a volume or brightness change in Pointer Mode? → A: New global "call me" hand (thumb and pinky out, other fingers curled) held 0.5 s opens a level panel with Volume and Brightness sliders side by side; point at one, pinch and move up/down to adjust, release to stop, fist or 5 s idle to close. Either hand works the same way (no left/right meaning).
- Q: Which gesture starts and ends a slide show in Presentation Mode? → A: Thumbs-up held 1 s starts the show from the current slide; thumbs-down held 1 s ends it; separate poses with a cooldown.
- Q: Which presenter apps must Presentation Mode be tested and documented against? → A: PowerPoint and Google Slides (browser) fully; Edge PDF viewer for slide changes only, start/end documented as unsupported.
- Q: In Presentation Mode, when does the pointer show and which pose counts as a swipe? → A: Pointer shows only while the index finger is raised alone (hides ~300 ms after it is lowered); swipes count only with an open hand (four fingers extended), never in the index pose.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open the mode menu and switch modes (Priority: P1)

A user in Pointer Mode holds a three-finger gesture. A menu lists the modes. They point at one and
pinch to choose it, or make a fist to cancel. The indicator then shows the new mode and a few hints
for it. The mode is never changed by accident.

**Why this priority**: Without a deliberate, safe way to switch modes, neither new mode can be
reached, and the product stays "a collection of gestures". Everything else depends on this.

**Independent Test**: With only Pointer and the menu implemented, replay a recording that opens
the menu, selects and cancels, and check the mode, the indicator text, and that nothing is sent
while the menu is open.

**Acceptance Scenarios**:

1. **Given** Active in any mode, **When** the three-finger gesture is held for 0.8 s, **Then** the
   mode menu opens, all held buttons are released, and no pointer, click, or key input is sent
   while it is open.
2. **Given** the menu is open, **When** the user points at a mode and pinches, **Then** that mode
   becomes current, the menu closes, and the indicator shows the mode name and its hints.
3. **Given** the menu is open, **When** the user makes a fist, or 5 s pass with no selection,
   **Then** the menu closes and the mode is unchanged.
4. **Given** the menu is open, **When** the hand is lost, the app is paused, or emergency stop is
   used, **Then** the menu closes, the mode is unchanged, and the usual state rules apply.
5. **Given** the menu is open, **When** a single frame shows a pinch or a fist, **Then** nothing
   is chosen or closed; the existing confidence and stable-frame rules apply.
6. **Given** Keyboard Mode is not available yet, **When** the menu opens, **Then** it is listed
   but shown as unavailable and cannot be chosen.
7. **Given** a mode was chosen, **When** the app is paused or tracking is lost and then returns,
   **Then** it returns to the same mode.
8. **Given** the app is running (Active, Paused, or Tracking Lost), **When** the user picks a mode
   from the tray icon's Mode submenu, **Then** that mode becomes current exactly as if chosen in
   the gesture menu (held inputs released, open menu or panel closed, indicator and hints
   updated); the current mode is shown checked and Keyboard is greyed out.

---

### User Story 2 - Present slides from a distance (Priority: P2)

A user in Presentation Mode moves to the next or previous slide with a gesture and points at slide
content with a stabilized on-screen pointer, standing or sitting a few metres from the laptop.

**Why this priority**: It is the first mode that is useful away from the desk and the main
reason for modes. It depends on User Story 1 and is independent of Media/System.

**Independent Test**: With a slide deck open in a common presenter app, change slides forward and
back, move the pointer across the slide, and start and end the show, all without touching a mouse
or keyboard, from the documented distance.

**Acceptance Scenarios**:

1. **Given** Presentation Mode, **When** the user performs the next-slide action, **Then** the
   presenter app advances exactly one slide; the previous-slide action goes back exactly one.
2. **Given** Presentation Mode, **When** the user raises only the index finger and holds the hand
   still, **Then** the pointer appears and stays still enough to point at a line of text; when
   they move, it follows without jitter; when they lower the index, it hides.
3. **Given** Presentation Mode, **When** the user swipes with an open hand, **Then** the slide
   changes and the pointer does not appear or move; a fast move in the index pose never changes
   the slide.
4. **Given** Presentation Mode, **When** the pointer moves, **Then** no clicks, drags, or scrolls
   are sent, and the pointer is clearly visible on the slide and is hidden outside this mode.
5. **Given** Presentation Mode and a supported presenter app, **When** the user performs the
   start or end action, **Then** the slide show starts or ends; a slide change or start/end
   action cannot repeat from a single held gesture (cooldown).
6. **Given** the user is at a distance from the camera, **When** tracking becomes unreliable,
   **Then** the app stops acting rather than guessing, and the distance range that works is
   documented from measurement.
7. **Given** Presentation Mode, **When** the user pauses with the flat hand, loses tracking, or
   changes mode, **Then** all pointer and key input stops at once.

---

### User Story 3 - Control media and common system actions (Priority: P3)

A user in Media/System Mode plays, pauses, skips tracks, changes volume, mutes, takes a screenshot,
or switches application. Each action is chosen deliberately, and anything that could disrupt the
user's work is easy to cancel.

**Why this priority**: Useful and low-risk once modes exist, and it reuses the same menu and
feedback style. It is last because it does not unlock other work.

**Independent Test**: With a media player and a few windows open, trigger each action once and
verify the effect; verify that a cancelled or unconfirmed action does nothing.

**Acceptance Scenarios**:

1. **Given** Media/System Mode, **When** the indicator opens, **Then** the available actions are
   shown as large targets: play/pause, next, previous, volume up, volume down, mute, brightness
   up, brightness down, screenshot, switch application.
2. **Given** the actions are shown, **When** the user points at one and pinches, **Then** exactly
   that action runs once and the indicator confirms it.
3. **Given** a volume or brightness action, **When** the user keeps the pinch held, **Then** the
   level keeps changing in small steps until release, and never jumps to full, silence, or a
   black screen by itself.
4. **Given** a screenshot or application-switch action, **When** the user selects it, **Then** it
   needs a second confirmation within 3 s and does nothing if the confirmation does not come or
   the user cancels with a fist.
5. **Given** any action, **When** it has just run, **Then** the same action cannot run again until
   a cooldown has passed and the pinch has been released.
6. **Given** Media/System Mode, **When** the hand is lost, the app is paused, or the mode changes,
   **Then** no action is pending and no input is held.

---

### User Story 4 - Adjust volume and brightness without leaving the current mode (Priority: P2)

A user working in Pointer Mode (or any other mode) wants to turn the volume or screen brightness
up or down. They do it with a deliberate gesture and see the level change on the indicator,
without switching to Media/System Mode and without clicking anything by accident.

**Why this priority**: Volume and brightness are the most frequent system adjustments and are
needed while working, not only in a media session. It depends on User Story 1 (gesture
classification and indicator) and is independent of Presentation Mode.

**Independent Test**: In Pointer Mode, raise and lower the volume and the brightness of the
built-in display, watch the levels on the indicator, then cancel mid-adjustment and verify the
change stops at once and no click, drag, or scroll was sent.

**Acceptance Scenarios**:

1. **Given** Active in Pointer Mode, **When** the user holds the "call me" hand (thumb and pinky
   out) for 0.5 s, **Then** a level panel opens with Volume and Brightness sliders, all held
   buttons are released, and each slider shows its current level.
2. **Given** the level panel is open, **When** the user points at a slider, pinches, and moves up
   or down, **Then** that level changes; releasing the pinch stops it, and a fist or 5 s without
   use closes the panel.
3. **Given** a level is being adjusted, **When** the user keeps adjusting, **Then** it changes in
   small bounded steps and never jumps to full, silence, or a black screen by itself.
4. **Given** a level is being adjusted, **When** the user releases, makes a fist, pauses, loses
   the hand, uses emergency stop, or opens the mode menu, **Then** the change stops at once and
   the level stays where it was.
5. **Given** the level panel is open, **When** the hand moves, **Then** no pointer movement,
   click, drag, or scroll is sent.
6. **Given** the display does not support software brightness control (for example an external
   monitor), **When** the user tries to change brightness, **Then** nothing changes and the
   indicator says brightness is unavailable; volume still works.

---

### Edge Cases

- A second hand appears in the menu or in either new mode: it never produces input (one primary
  hand).
- A pinch begins while the user is still moving the hand into the menu: it must be a stable
  pinch on a menu item to count; a pinch outside every item does nothing.
- The three-finger gesture is held while a pinch or drag is in progress: it is ignored until the
  hand is relaxed (no mode menu in the middle of a gesture).
- Mode changes while a media or key action is mid-way: everything is released first.
- The presenter app is not in the foreground: key actions go to whatever has focus; the app does
  not move focus on its own, and the limitation is documented.
- A media key is pressed while no media app is running: nothing happens, and no error is shown
  beyond the confirmation.
- A swipe happens in dim light, where the camera drops to about 10 FPS and the motion spans only
  a few frames: it must either be recognized correctly or ignored, never counted in the wrong
  direction or twice.
- Thumbs-up or thumbs-down is held longer than 1 s: the action fires once only; a sideways
  thumb or a tilt between up and down does nothing.
- Thumbs-up is used when a show is already running, or thumbs-down when none is: the keys sent
  must be harmless in that case (no restart from slide 1); the behaviour per app is documented.
- The index pose flickers for a frame or two at distance: the pointer stays visible through the
  short grace period and does not jump when the pose returns.
- The user moves from pointing straight into a swipe: no slide changes until the hand is open,
  and the pointer hides on the normal grace period.
- The user brings the hand back after a swipe: the return stroke must not change the slide back.
- The user gestures while talking: motions that are too slow, too short, or not horizontal do
  nothing.
- The user is far from the camera and the hand is intermittently tracked: slide changes and
  actions must not fire from flickering detections.
- Brightness is requested on a display that does not support it, or the system refuses the
  change: nothing happens, the indicator says it is unavailable, and no error dialog appears.
- The thumb-out scroll pose is made with a loosely curled pinky: it must stay a scroll and not
  open the level panel; the 0.5 s hold and stable-frame rules apply.
- The "call me" hand is held while a pinch, drag, scroll, or swipe is in progress: it is ignored
  until the hand is relaxed.
- Volume is already at maximum or zero, or brightness at its limit: further steps do nothing.
- The camera is lost or the hotkey is unavailable while in a new mode: the same rules as spec 002
  apply (Paused, Resume refused when emergency stop cannot be registered).

## Requirements *(mandatory)*

### Functional Requirements

**Mode system and guidance**

- **FR-001**: The mode menu MUST open from any mode by holding the three-finger gesture for 0.8 s
  while Active and not mid-gesture, and MUST list Pointer, Presentation, Media/System, and
  Keyboard (Keyboard shown as unavailable).
- **FR-002**: Choosing a mode MUST need an explicit, stable confirmation (thumb–index pinch on a
  menu item); the menu MUST close on a fist or after 5 s without a selection, leaving the mode
  unchanged.
- **FR-003**: Opening the menu and every mode change MUST release all held inputs first, and no
  input MUST be sent to the system while the menu is open.
- **FR-004**: Exactly one mode MUST be current. It MUST be kept through Paused and Tracking Lost
  and restored on return, and the app MUST start in Pointer Mode on every launch.
- **FR-005**: The indicator MUST show the current mode at all times while Active, and on entering
  a mode MUST show at most four hints for that mode only. Hints for other modes MUST NOT appear.
- **FR-006**: Gestures MUST be classified as global (the same in every mode) or mode-specific, and
  this MUST be documented. Resume, clutch, pause, emergency stop, the mode menu, and the level
  panel ("call me") are global; no mode may reuse a global gesture for anything else.
- **FR-007**: A gesture that is not defined in the current mode MUST do nothing.
- **FR-025**: The tray icon MUST offer a Mode submenu (Pointer, Presentation, Media/System, and
  Keyboard greyed out) as a mouse fallback to the gesture menu. It MUST show the current mode
  checked, MUST work while Active, Paused, or Tracking Lost (in Paused the chosen mode applies on
  resume), and MUST follow the same rules as a gesture mode change (FR-003, FR-004). The gesture
  menu remains the primary way to switch modes.

**Presentation Mode**

- **FR-008**: In Presentation Mode the user MUST be able to go to the next and previous slide with
  a horizontal swipe of an open hand (four fingers extended): right = next, left = previous (screen direction in the mirrored view). A swipe
  MUST only count when the hand travels a minimum horizontal distance (normalized by hand size)
  within a short time window, mostly horizontally, tracked with confidence on every frame of the
  motion. Each swipe MUST move exactly one slide and respect a cooldown; the return motion after a
  swipe MUST NOT trigger the opposite slide. Movement in the index-pointer pose (FR-009) MUST
  never count as a swipe. The global pause (flat hand held still for 1.5 s) keeps working: a swipe
  is fast motion and never pauses, and a held, still flat hand never swipes.
- **FR-009**: Presentation Mode MUST show a visible on-screen pointer only while the index finger
  is raised alone (other fingers and thumb curled). It MUST follow the hand with stronger
  stabilization than Pointer Mode, MUST send no clicks, drags, or scrolls, and MUST hide about
  300 ms after the index pose ends (so a one-frame dropout does not make it blink), and at once
  when the mode ends or input stops.
- **FR-010**: In Presentation Mode, thumbs-up (fist with the thumb pointing up) held 1 s MUST
  start the slide show from the current slide (never from slide 1), and thumbs-down held 1 s MUST
  end it. Each MUST fire once per hold, respect a cooldown, and need the hand to change pose
  before it can fire again. The pointer is hidden while either pose is held. This applies
  where the presenter app supports it reliably; supported apps and the keys used MUST be listed
  in the documentation. The tested set is: PowerPoint and Google Slides in the browser (slide
  changes, start, and end) and the Edge PDF viewer (slide changes only; start and end documented
  as unsupported there).
- **FR-011**: The distance range at which Presentation Mode works reliably MUST be measured on the
  reference laptop and documented, including how it degrades beyond that range. The product MUST
  NOT claim a range that was not measured.

**Media and system controls**

- **FR-012**: Media/System Mode MUST offer: play/pause, next track, previous track, volume up,
  volume down, mute, brightness up, brightness down, screenshot, and application switching.
- **FR-013**: Each action MUST be chosen by pointing at a large on-screen target and confirming
  with a pinch, MUST run once per confirmed pinch, and MUST have a cooldown.
- **FR-014**: Volume and brightness actions MUST repeat in small steps while the pinch is held, with a bounded
  step size and rate, and stop on release, hand loss, pause, or mode change.
- **FR-015**: Screenshot and application switching MUST need a second confirmation within 3 s and
  MUST be cancellable by a fist; unconfirmed actions MUST do nothing.
- **FR-016**: Actions MUST NOT be sent to the system if the pinch is not stable, confidence is
  low, or the pointed target is not unambiguous.

**Quick level controls (all modes)**

- **FR-021**: Volume and brightness MUST be adjustable from Pointer Mode, Presentation Mode, and
  Media/System Mode without changing mode. Holding the "call me" hand (thumb and pinky extended,
  index, middle, and ring curled) for 0.5 s while Active and not mid-gesture MUST open a level
  panel with Volume and Brightness sliders as large targets (at least 48 px). The user adjusts a
  level by pointing at a slider, pinching, and moving up or down; releasing the pinch stops the
  change; a fist or 5 s without use closes the panel. Either hand works identically. "Call me"
  is a global gesture (FR-006) and MUST be distinguished from the thumb-out scroll pose; a
  replay test MUST show it does not trigger during scrolling, pointing, or idle recordings.
- **FR-022**: Level changes MUST use bounded steps and a bounded rate, MUST show the current level
  on the indicator while adjusting, and MUST stop on release, fist, pause, hand loss, emergency
  stop, mode change, or opening the mode menu.
- **FR-023**: While the level panel is open, no pointer movement, click, drag, scroll, or
  slide key MUST be sent.
- **FR-024**: Brightness MUST control the built-in display. If brightness cannot be changed, the
  indicator MUST say so and volume control MUST keep working.

**Safety, privacy, quality**

- **FR-017**: All Spec 002 safety rules MUST hold in every mode: confidence and stable-frame gates,
  hysteresis and cooldowns, ReleaseAll on pause, loss, mode change, exit or error, emergency stop,
  one primary hand, and emergency stop and pause that cannot be disabled by settings.
- **FR-018**: No camera images MUST be saved or sent anywhere, and the app MUST make no network
  calls at runtime. Recordings contain landmark numbers only.
- **FR-019**: New behaviour MUST be covered by landmark-replay tests and MUST be deterministic:
  the same recording replayed twice gives the same events. Settings for the new values (stabilization,
  cooldowns, step sizes, hold times) MUST follow the validated settings file of spec 002.
- **FR-020**: The mode menu, the pointer, and the action targets MUST remain usable at 100%, 125%,
  and 150% display scaling on the primary monitor.

### Key Entities

- **Mode**: One of Pointer, Presentation, Media/System, Keyboard (unavailable). Exactly one is
  current; it decides which gestures are active and which hints are shown.
- **Mode menu**: The temporary selection screen opened by the three-finger gesture; it blocks all
  other input while open.
- **Action target**: A large on-screen button for a media or system action, selected by pointing
  and confirmed by pinch, possibly with a second confirmation.
- **Presentation pointer**: The stabilized on-screen marker that follows the hand in Presentation
  Mode while the index finger is raised alone, and sends no clicks.
- **Cooldown**: The minimum time before the same slide or media action can run again.
- **Level panel**: The temporary panel opened by the "call me" gesture, with Volume and
  Brightness sliders; it blocks all other input while open and does not change the mode.
- **Level control**: An adjustment of system volume or built-in display brightness in bounded
  steps, available in every mode, shown on the indicator while active.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a timed trial, a first-time user opens the menu and switches to a named mode in
  under 10 s, in at least 9 of 10 attempts.
- **SC-002**: Across at least 10 minutes of recordings with the hands not controlling (idle,
  typing, talking, a second person), the mode menu opens and mode or action events fire 0 times.
- **SC-003**: In a 20-slide deck presented from the documented distance, at least 95% of intended
  slide changes happen on the first attempt, with 0 unintended or double slide changes.
- **SC-004**: The presentation pointer rests within 12 pixels of its position for 2 s when the
  hand is held still at the documented distance, measured on a 1080p display.
- **SC-005**: Each media or system action runs correctly on at least 9 of 10 intended attempts,
  and 0 actions run when the user cancels or does not confirm.
- **SC-006**: Within 200 ms of emergency stop, pause, hand loss, or a mode change, no key, button,
  or pointer input is held or still being sent (100% of trials).
- **SC-007**: The current mode is identifiable from the indicator in every state; in a short
  walkthrough, all test users name the correct mode and at least two of its gestures.
- **SC-008**: Replaying any recorded session twice produces identical events, and every mode
  transition and action in this spec is covered by at least one replay test.
- **SC-009**: In Pointer Mode, a user changes volume or brightness to a requested level (within
  one step) in under 5 s in at least 9 of 10 attempts, with 0 clicks, drags, or scrolls sent.

## Assumptions

- Presentation and media actions are delivered to the Windows foreground application using
  standard keys and media keys; the app does not control other programs through their own
  interfaces. The tested presenter apps are PowerPoint, Google Slides in the browser, and the Edge
  PDF viewer (slide changes only), as listed in FR-010.
- The mode menu and the action targets are on the primary monitor only; multiple monitors arrive
  later.
- The presentation pointer is drawn by GesCRTL as a click-through marker, not by the presenter
  app. Annotation (drawing, erasing) is out of scope.
- Keyboard Mode, custom gestures, and per-user remapping are out of scope (spec 004).
- Pointer Mode keeps working exactly as in spec 002; the mode menu adds one global gesture and
  does not change the Pointer gestures.
- A user at a presenting distance of 2–4 m may exceed what a laptop webcam tracks reliably; the
  spec requires measuring and documenting the real range, not reaching 4 m.
- The app starts in Pointer Mode every launch; remembering the last mode across launches is not
  required.
- Brightness control covers the laptop's built-in display only; external monitors (which need
  their own control protocol) are out of scope and documented as a limitation.
- Platform limits from `docs/product/known-limitations.md` (elevated windows, secure desktop)
  also apply to the keys sent here.
