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
- **Media/System Mode**: play and pause, skip tracks, change volume, mute, take a screenshot, and
  switch application, hands-free, with disruptive actions kept deliberate and easy to cancel.

It builds on the interaction model, gesture vocabulary, safety policy, and HUD concept in
`docs/interaction/` (the mode menu, events E12–E14, and the opening gesture G7 are already
defined there) and must satisfy the constitution, in particular Principle I (Safety First) and
Principle IV (Deterministic, Testable Core).

**Dependency**: spec 002 (state machine, pointer pipeline, HUD, replay and benchmark tools).
Keyboard Mode is spec 004; here it only appears in the menu as unavailable.

## Clarifications

### Session 2026-10-11

- Q: How does the user move to the next or previous slide? → A: [NEEDS CLARIFICATION: slide navigation input; see the question below]

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
2. **Given** Presentation Mode, **When** the user holds the hand still, **Then** the pointer
   stays still enough to point at a line of text; when they move, it follows without jitter.
3. **Given** Presentation Mode, **When** the pointer moves, **Then** no clicks, drags, or scrolls
   are sent, and the pointer is clearly visible on the slide and is hidden outside this mode.
4. **Given** Presentation Mode and a supported presenter app, **When** the user performs the
   start or end action, **Then** the slide show starts or ends; a slide change or start/end
   action cannot repeat from a single held gesture (cooldown).
5. **Given** the user is at a distance from the camera, **When** tracking becomes unreliable,
   **Then** the app stops acting rather than guessing, and the distance range that works is
   documented from measurement.
6. **Given** Presentation Mode, **When** the user pauses with the flat hand, loses tracking, or
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
   shown as large targets: play/pause, next, previous, volume up, volume down, mute, screenshot,
   switch application.
2. **Given** the actions are shown, **When** the user points at one and pinches, **Then** exactly
   that action runs once and the indicator confirms it.
3. **Given** a volume action, **When** the user keeps the pinch held, **Then** the volume keeps
   changing in small steps until release, and never jumps to full volume or silence by itself.
4. **Given** a screenshot or application-switch action, **When** the user selects it, **Then** it
   needs a second confirmation within 3 s and does nothing if the confirmation does not come or
   the user cancels with a fist.
5. **Given** any action, **When** it has just run, **Then** the same action cannot run again until
   a cooldown has passed and the pinch has been released.
6. **Given** Media/System Mode, **When** the hand is lost, the app is paused, or the mode changes,
   **Then** no action is pending and no input is held.

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
- The user is far from the camera and the hand is intermittently tracked: slide changes and
  actions must not fire from flickering detections.
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
  this MUST be documented. Resume, clutch, pause, emergency stop, and the mode menu are global;
  no mode may reuse a global gesture for anything else.
- **FR-007**: A gesture that is not defined in the current mode MUST do nothing.

**Presentation Mode**

- **FR-008**: In Presentation Mode the user MUST be able to go to the next and previous slide with
  a deliberate gesture: [NEEDS CLARIFICATION: slide navigation input; swipe motion, held pose or
  zone pinch, or on-screen buttons?]. Each performance MUST move exactly one slide and respect a
  cooldown.
- **FR-009**: Presentation Mode MUST show a visible on-screen pointer that follows the hand with
  stronger stabilization than Pointer Mode, MUST send no clicks, drags, or scrolls, and MUST hide
  the pointer when the mode ends or input stops.
- **FR-010**: The user MUST be able to start and end a slide show with a deliberate gesture where
  the presenter app supports it reliably; supported apps MUST be listed in the documentation.
- **FR-011**: The distance range at which Presentation Mode works reliably MUST be measured on the
  reference laptop and documented, including how it degrades beyond that range. The product MUST
  NOT claim a range that was not measured.

**Media and system controls**

- **FR-012**: Media/System Mode MUST offer: play/pause, next track, previous track, volume up,
  volume down, mute, screenshot, and application switching.
- **FR-013**: Each action MUST be chosen by pointing at a large on-screen target and confirming
  with a pinch, MUST run once per confirmed pinch, and MUST have a cooldown.
- **FR-014**: Volume actions MUST repeat in small steps while the pinch is held, with a bounded
  step size and rate, and stop on release, hand loss, pause, or mode change.
- **FR-015**: Screenshot and application switching MUST need a second confirmation within 3 s and
  MUST be cancellable by a fist; unconfirmed actions MUST do nothing.
- **FR-016**: Actions MUST NOT be sent to the system if the pinch is not stable, confidence is
  low, or the pointed target is not unambiguous.

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
  Mode and sends no clicks.
- **Cooldown**: The minimum time before the same slide or media action can run again.

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

## Assumptions

- Presentation and media actions are delivered to the Windows foreground application using
  standard keys and media keys; the app does not control other programs through their own
  interfaces, and works with common presenter apps (for example PowerPoint, a PDF viewer, or a
  browser-based deck). The tested apps are listed in the documentation.
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
- Platform limits from `docs/product/known-limitations.md` (elevated windows, secure desktop)
  also apply to the keys sent here.
