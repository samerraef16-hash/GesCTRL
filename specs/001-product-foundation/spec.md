# Feature Specification: Product Foundation and Interaction Model (Phase 0)

**Feature Branch**: `001-product-foundation`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "read Plan.md and create a specification for Phase 0: Product Foundation and Interaction Model"

## Overview

Phase 0 produces the shared definition of what GesCRTL is and how it behaves before any product
feature is built. Its outputs are a small set of reviewed foundation documents plus a throwaway
feasibility prototype whose only purpose is to prove (or disprove) that the experience promised in
`Plan.md` is achievable on the target hardware. Every later phase (starting with the Pointer Mode
MVP) builds on these definitions, so they must be complete, consistent, and unambiguous.

The "users" of this phase are the project owner and future contributors who write later specs and
code. The end user benefits indirectly: the decisions made here determine whether GesCRTL feels
predictable, safe, and comfortable.

## Clarifications

### Session 2026-10-10

- Q: When the controlling hand reappears after tracking was lost, does control resume
  automatically or require deliberate re-activation? → A: Always resume automatically when the
  primary hand reappears; users rely on the explicit pause gesture when they want control to stop.
- Q: How does the user switch between the four modes? → A: Holding one dedicated global
  gesture opens an on-screen mode menu; the user points at a mode and confirms to switch.
- Q: While Paused, does the camera keep watching for a resume gesture? → A: Both exist:
  Paused keeps the camera watching (reduced rate) for a deliberate resume gesture; a separate
  "Turn off" action moves to Inactive, where the camera is fully stopped.
- Q: If the hand is lost mid-drag, is the held button released immediately or after a grace
  period? → A: Released immediately on any tracking loss (no grace period).
- Q: Which state does the emergency stop lead to? → A: Paused (camera keeps watching; deliberate
  resume gesture, keyboard shortcut, or tray resumes), with all held input released.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Defined interaction model: states, modes, and transitions (Priority: P1)

As the project owner, I want one authoritative definition of every application state
(Inactive, Active, Paused, Tracking Lost) and every interaction mode (Pointer, Keyboard,
Presentation, Media/System), including exactly how and when the application moves between them,
so that every later feature behaves consistently and the user always knows what will happen.

**Why this priority**: Every later phase depends on this model. Without it, each feature would
invent its own activation, pause, and recovery behavior, which is exactly what the constitution
(Principle III) forbids.

**Independent Test**: A reviewer, given only the interaction model document, can answer for any
combination of current state, current mode, and event (gesture, hand lost, camera lost, hotkey,
startup, shutdown) what the next state and mode are and what the user sees—without needing to
ask the author.

**Acceptance Scenarios**:

1. **Given** the interaction model document, **When** a reviewer picks any state and any event,
   **Then** the document specifies exactly one resulting state and the feedback shown to the user.
2. **Given** the application is Active in any mode, **When** the controlling hand disappears from
   view, **Then** the model specifies a transition to Tracking Lost, specifies that held buttons
   or keys are released, and specifies that control returns to Active in the same mode
   automatically when the primary hand reappears.
3. **Given** the application has just started, **When** no deliberate resume gesture has occurred,
   **Then** the model specifies that no input is sent to the computer.
4. **Given** any state, **When** the user triggers the emergency stop (gesture or keyboard
   shortcut), **Then** the model specifies an immediate transition to Paused with all held
   input released (from Inactive, the emergency stop has no effect because nothing is acting).
5. **Given** the four modes, **When** a reviewer checks mode switching, **Then** the model defines
   how the mode menu is opened, how a mode is selected and confirmed, how the menu is cancelled,
   which mode is the default, and that a single accidental frame cannot switch modes.
6. **Given** the user has paused GesCRTL with the pause gesture, **When** the hand leaves and
   reappears, **Then** the application stays Paused (automatic resume applies only to Tracking
   Lost, never to Paused).

---

### User Story 2 - First-release gesture vocabulary and accidental-action policy (Priority: P2)

As the project owner, I want a small, written gesture vocabulary for the first release—which
gestures are global (available in every mode) and which are Pointer Mode–specific—together with a
policy for preventing accidental actions, so that the Pointer Mode MVP has a clear, safe target.

**Why this priority**: The Phase 1 MVP cannot be specified until we know which gestures it uses and
what safety rules every gesture must follow.

**Independent Test**: A reviewer can read the vocabulary and confirm that each gesture has a
unique meaning within its scope, a described physical form, an intended action, and the safety
rules that apply, and that the global gestures (activate, pause, emergency stop, mode switch)
never conflict with mode-specific gestures.

**Acceptance Scenarios**:

1. **Given** the vocabulary, **When** a reviewer lists all Pointer Mode actions (move, left click,
   right click, double click, drag, scroll, clutch/pause), **Then** each is mapped to exactly one
   gesture and no gesture is mapped to two actions in the same mode.
2. **Given** the accidental-action policy, **When** a reviewer checks any consequential action,
   **Then** the policy states the confidence requirement, the minimum hold or stability time,
   the separate start and release conditions (hysteresis), and the cooldown that apply.
3. **Given** the vocabulary, **When** a left-handed user is considered, **Then** every gesture can
   be performed with either hand.
4. **Given** the vocabulary, **When** the gestures are counted, **Then** the first release uses no
   more than 8 distinct gestures in total (global plus Pointer Mode).
5. **Given** the feedback concept, **When** a reviewer checks the on-screen indicator, **Then** it
   defines what the user sees for each state and mode and confirms the indicator never blocks
   clicks or takes focus from other applications.

---

### User Story 3 - Feasibility validated against the performance targets (Priority: P3)

As the project owner, I want a minimal throwaway prototype that tracks one hand and moves the
system cursor on a real laptop, with measured responsiveness, smoothness, and resource usage,
so that I know before Phase 1 begins whether the intended approach can meet the targets in
`Plan.md` §6—and I want the key technical decisions recorded with their reasons.

**Why this priority**: It retires the biggest technical risk (lag, jitter, CPU cost) early and
cheaply. It is lower than P1/P2 because it validates decisions rather than defining behavior.

**Independent Test**: Running the prototype on the reference laptop produces a measurement report
showing responsiveness, tracking rate, and resource usage, compared against the targets, with a
clear pass/fail verdict for each.

**Acceptance Scenarios**:

1. **Given** the prototype running on the reference laptop under normal indoor lighting,
   **When** a measurement session is run, **Then** a report records the delay from hand movement
   to cursor movement (95th percentile), the hand-tracking rate, and resource usage with and
   without a hand in view.
2. **Given** the measurement report, **When** any target is missed, **Then** the report states the
   gap and a recommended mitigation, and the phase cannot be closed until the owner accepts either
   the mitigation or a revised target.
3. **Given** the phase is complete, **When** a reviewer checks the decision records, **Then** each
   major technical decision (approach to hand tracking, method of sending input to the computer,
   on-screen indicator approach, packaging approach, and pointer mapping model) has a record
   containing the options considered, the choice, and the evidence behind it.
4. **Given** the pointer mapping decision, **When** a reviewer reads it, **Then** it states whether
   cursor position follows the hand directly within a comfortable region or moves relative to hand
   motion, and justifies the choice using prototype observations.

---

### User Story 4 - Product definition, release boundaries, and known limits (Priority: P4)

As a future contributor or early user, I want a short product definition—who GesCRTL is for, the
key use cases, what the first release includes and explicitly excludes, how success is measured,
and which situations GesCRTL cannot handle—so that expectations are honest and scope stays
controlled.

**Why this priority**: Much of this content already exists in `Plan.md`; this story consolidates
and confirms it rather than creating it from scratch.

**Independent Test**: A person unfamiliar with the project can read the product definition and
correctly answer: who it is for, what the first release does, what it does not do, and which
situations it cannot control.

**Acceptance Scenarios**:

1. **Given** the product definition, **When** a reader looks for scope, **Then** it lists
   first-release inclusions and explicit exclusions (for example high-speed typing and two-handed
   air typing).
2. **Given** the known-limitations list, **When** a reader checks it, **Then** it states that
   GesCRTL cannot control administrator-level windows without elevated rights, cannot act on
   secure system screens (sign-in, lock screen, security prompts), and may lose the camera when
   another application uses it exclusively.
3. **Given** the product definition, **When** a reader checks success criteria, **Then** they match
   the first-milestone criteria and targets in `Plan.md` §6.
4. **Given** the glossary, **When** a reader encounters a core term (state, mode, gesture, global
   gesture, clutch, emergency stop, consequential action), **Then** the term has one definition
   used consistently across all Phase 0 documents.

---

### Edge Cases

- **Several hands or people in view**: The interaction model must define which hand is in control
  and that other hands never produce input.
- **Hand briefly lost during a drag**: The held button is released immediately on entering
  Tracking Lost, with no grace period; when the hand reappears and control resumes, the drag does
  not continue and the user must start a new drag.
- **Camera unplugged or taken by another application while Active**: The model must define the
  transition, the user-visible message, and recovery when the camera becomes available again.
- **User wants to stop but the hand is not visible**: The emergency stop must also be reachable
  without gestures (keyboard shortcut and system tray).
- **Gesture made while switching modes**: The model must define that gestures during a mode
  transition are ignored until the transition completes.
- **Poor lighting or partial hand visibility**: The policy must define that low-confidence tracking
  results in no consequential actions rather than guessed actions.
- **Feasibility targets missed**: The phase must not silently proceed; the gap and the decision
  (mitigate, revise target, or change approach) must be recorded.
- **Contradiction between documents**: If the interaction model contradicts `Plan.md` or the
  constitution, the constitution prevails and the conflicting document is corrected before
  the phase closes.

## Requirements *(mandatory)*

### Functional Requirements

**Interaction model**

- **FR-001**: The phase MUST produce an interaction model defining the application states
  Inactive, Active, Paused, and Tracking Lost, with every allowed transition, its trigger, and
  the user-visible feedback.
- **FR-001a**: When the primary hand reappears while in Tracking Lost, the application MUST
  return automatically to Active in the mode that was current before the loss, with no
  activation gesture. A deliberate pause gesture (Paused state) MUST NOT be undone by hand loss
  and reappearance; only an explicit resume leaves Paused.
- **FR-002**: The interaction model MUST define the four modes (Pointer, Keyboard, Presentation,
  Media/System), the default mode (Pointer), and deliberate entry and exit for each mode.
- **FR-002a**: Mode switching MUST use a mode menu: holding a single dedicated global gesture
  for a minimum hold time opens an on-screen menu listing all modes with the current mode
  highlighted; the user points at a mode and confirms it to switch. Releasing or cancelling
  without confirming MUST leave the mode unchanged, and no other input is sent while the menu
  is open.
- **FR-003**: The interaction model MUST specify that no input is sent to the computer unless the
  application is Active and tracking confidence meets the defined threshold.
- **FR-004**: The interaction model MUST specify that all held buttons and keys are released on
  entering Paused, Tracking Lost, or Inactive, on mode change, and on shutdown or failure.
- **FR-005**: The interaction model MUST define an emergency stop reachable by at least two
  independent means, at least one of which does not require gestures. The emergency stop MUST
  release all held input and move the application to Paused immediately, whatever the current
  state, mode, or open menu.
- **FR-005a**: Paused and Inactive MUST be distinct:
  - **Paused**: the camera keeps running at a reduced processing rate, no input is sent, and
    only a deliberate resume gesture (held for a minimum time) or the keyboard shortcut / tray
    returns to Active.
  - **Inactive**: the camera is fully stopped and released; it is entered via a "Turn off"
    action (gesture, keyboard shortcut, or tray) and left only via keyboard shortcut, tray, or
    relaunch, since no gestures can be seen.
  - On launch, the application starts in Paused, so the user can begin with a deliberate resume
    gesture and no input is sent until then.
- **FR-006**: The interaction model MUST define primary-hand selection and specify that
  non-primary hands produce no input.

**Gesture vocabulary and safety policy**

- **FR-007**: The phase MUST produce a gesture vocabulary that labels each gesture as global or
  mode-specific and covers, at minimum, resume, pause, emergency stop, turn off, opening the mode menu,
  and all Pointer Mode actions (move, left click, right click, double click, drag, vertical scroll,
  clutch).
- **FR-008**: Each gesture entry MUST include a plain-language description of the hand form, the
  resulting action in each mode where it applies, and the safety rules that govern it.
- **FR-009**: The phase MUST produce an accidental-action policy defining confidence requirements,
  minimum stability time, separate start/release conditions, cooldowns for repeatable actions,
  and behavior under uncertain tracking.
- **FR-010**: The vocabulary MUST be performable with either hand and from a relaxed, low-fatigue
  posture, with the movement region for pointer control described.
- **FR-011**: The phase MUST produce a feedback concept describing what the on-screen indicator
  shows in each state and mode, and requiring that it never takes focus or blocks clicks.

**Feasibility and decisions**

- **FR-012**: The phase MUST produce a throwaway feasibility prototype that tracks one hand and
  moves the system cursor; it MUST NOT be treated as the foundation of the Phase 1 product code.
- **FR-013**: The prototype MUST be measured on the reference laptop, producing a report of
  hand-to-cursor delay (95th percentile), tracking rate, and resource usage with and without a
  hand in view, compared against the targets in `Plan.md` §6.
- **FR-014**: The phase MUST produce decision records for: hand-tracking approach, method of
  sending input, on-screen indicator approach, packaging approach, and pointer mapping model;
  each record MUST list options considered, the decision, and supporting evidence.
- **FR-015**: The phase MUST set a concrete resource-usage budget for the idle (no hand present)
  case, based on measurements, to replace the "budget set in Phase 0" placeholder in `Plan.md` §6.

**Product definition**

- **FR-016**: The phase MUST produce a product definition stating primary users, key use cases,
  first-release inclusions, explicit exclusions, and success criteria consistent with `Plan.md` §6.
- **FR-017**: The phase MUST produce a known-limitations list covering, at minimum,
  administrator-level windows, secure system screens, and camera sharing with other applications.
- **FR-018**: The phase MUST produce a glossary of core terms used consistently across all Phase 0
  documents and later specs.

**Consistency and closure**

- **FR-019**: All Phase 0 documents MUST be consistent with each other, with `Plan.md`, and with
  the constitution; any change to `Plan.md` or the constitution required by Phase 0 findings MUST
  be made before the phase closes.
- **FR-020**: Camera images MUST NOT be stored or transmitted at any point during the phase,
  including during prototype measurement; only numeric measurements and hand-position data may be
  recorded.

### Key Entities

- **Application State**: The overall operating condition (Inactive, Active, Paused, Tracking Lost);
  determines whether any input may be sent and whether the camera is running (stopped only in
  Inactive).
- **Interaction Mode**: The context (Pointer, Keyboard, Presentation, Media/System) that determines
  what a mode-specific gesture means; exactly one mode is current at a time.
- **Transition**: A move from one state or mode to another; has a trigger, conditions, and
  user-visible feedback.
- **Gesture**: A described hand form or motion; scoped as global or mode-specific; maps to an
  intent.
- **Action**: The effect sent to the computer (cursor move, click, scroll, key, etc.); may be
  consequential (changes something) or non-consequential (cursor motion).
- **Safety Rule**: A condition (confidence, stability time, hysteresis, cooldown) that must hold
  before a gesture becomes an action.
- **Feedback Indicator**: The on-screen element that communicates state, mode, and relevant hints.
- **Decision Record**: A written decision with options, choice, and evidence.
- **Known Limitation**: A documented situation GesCRTL cannot handle, with its user-facing
  explanation.
- **Performance Target**: A measurable goal (delay, tracking rate, false actions, resource usage)
  with its measured value and pass/fail status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of state/event combinations in the interaction model, a reviewer can
  determine the resulting state and user feedback without consulting the author.
- **SC-002**: Zero gesture conflicts: no gesture maps to more than one action within the same
  mode, and no global gesture overlaps a mode-specific gesture.
- **SC-003**: The first-release vocabulary contains no more than 8 distinct gestures, each
  performable with either hand.
- **SC-004**: On the reference laptop, the prototype moves the cursor within 80 ms of hand
  movement for 95% of measured frames and tracks the hand at 25 or more updates per second—or the
  shortfall is documented with an accepted mitigation or revised target.
- **SC-005**: All five required decision records exist, each citing at least one piece of evidence
  (measurement, observation, or comparison).
- **SC-006**: A person new to the project can correctly answer 5 out of 5 questions about scope,
  exclusions, target users, and known limitations after reading the product definition for no more
  than 10 minutes.
- **SC-007**: A final consistency review finds zero contradictions between Phase 0 documents,
  `Plan.md`, and the constitution.
- **SC-008**: The Phase 1 (Pointer Mode MVP) specification can be written using only Phase 0
  documents as input, with no more than 3 open clarification questions about states, gestures, or
  safety rules.

## Assumptions

- The primary audience for the first release is everyday laptop and desktop users on Windows with
  a built-in or standard USB webcam; users with motor impairments are an important secondary
  audience whose needs are addressed through configurability and later accessibility work
  (Phase 9), not through a separate first-release design.
- The reference hardware for feasibility measurement is the project owner's own Windows laptop and
  its built-in webcam under normal indoor lighting; its specifications are recorded in the
  measurement report.
- The application starts in a non-acting state (Paused, camera watching) and requires a
  deliberate resume gesture before sending any input; this is the safe default implied by the
  constitution.
- Phase 0 documents are written as Markdown files in the repository (for example under `docs/`),
  and decision records follow a simple options/decision/evidence format.
- The feasibility prototype is disposable; its code may be kept for reference but is not extended
  into the product.
- The detailed design of Keyboard, Presentation, and Media/System modes is out of scope for
  Phase 0 beyond their names, entry/exit rules, and place in the state model; their gestures are
  defined in their own later phases.
- Calibration, multi-monitor behavior, user settings screens, and custom gesture learning are out
  of scope for Phase 0.
- The performance targets in `Plan.md` §6 are the starting targets; Phase 0 may revise them only
  with recorded evidence and owner approval.
