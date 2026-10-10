# GesCRTL — Product Summary and Development Roadmap

## 1. Executive Summary

**GesCRTL** is a webcam-based human-computer interaction system that lets users control common PC tasks with hand gestures, without relying on a physical mouse, touchpad, or presentation remote—and, where practical, perform basic keyboard tasks without touching a keyboard.

The product should feel like a new input device, not a collection of unrelated gestures. Users should be able to move naturally, perform deliberate actions when needed, and switch between a small set of clear interaction modes. The system should communicate its current mode, prevent accidental actions, and stay unobtrusive during normal use.

The initial target platform is **Windows desktop/laptop**, using a standard webcam. The architecture and product decisions should avoid unnecessary Windows-specific coupling where practical, so other operating systems can be considered later.

### Product vision

> Let users interact with their computer naturally through their hands, using a webcam as the primary input device.

### Product goals

- Provide reliable pointer control for everyday computer use.
- Support distinct modes for pointer, keyboard, presentation, and media/system tasks.
- Keep the gesture vocabulary small, memorable, and context-aware.
- Make the system predictable through clear feedback, safe activation, and recovery from tracking interruptions.
- Allow users to customize controls without requiring customization during first-time setup.
- Build toward a useful, maintainable open-source application—not just a computer-vision demo.

### Initial scope boundaries

GesCRTL should aim to replace physical input devices for **common, selected tasks**, rather than promise that gesture control will outperform a physical keyboard for every workflow. High-speed text entry, precision-heavy work, and every possible operating-system interaction are not requirements for the first release.

The first release should prioritize a small end-to-end experience that works consistently over a large collection of unreliable features.

---

## 2. User Experience Principles

1. **Natural interaction over gesture memorization.** Users should learn a few intuitive interactions, not dozens of unrelated gestures.
2. **Modes provide context.** A gesture may have a different meaning in Pointer Mode than in Presentation Mode, but the current mode must always be clear.
3. **One default experience.** On startup, users should be able to enter Pointer Mode quickly without configuring every gesture.
4. **Deliberate activation and pause.** Users need an obvious way to activate, temporarily pause, and resume gesture control.
5. **Prevent accidental actions.** Uncertain tracking or an ambiguous gesture should not trigger consequential actions.
6. **Quiet, useful feedback.** A compact on-screen indicator should show the active mode and relevant gesture hints without constantly interrupting the user.
7. **Progressive disclosure.** Show beginners only the controls relevant to the current mode; keep advanced customization optional.
8. **Graceful recovery.** If the hand or camera is temporarily lost, pause unsafe actions and clearly indicate what happened.
9. **Useful before intelligent.** First deliver dependable built-in gestures; add learned/custom gestures only when they solve a demonstrated user need.
10. **Accessible and configurable.** Sensitivity, movement range, and mappings should be adjustable to suit different users and environments, including left- and right-handed use.
11. **Low fatigue.** Interactions should work from a comfortable, relaxed hand position; a small active region of the camera frame maps to the whole screen, and users can rest without triggering actions.
12. **Private by default.** All camera processing happens on-device and in memory; no camera data leaves the machine or is written to disk.

---

## 3. Development Approach with Spec Kit

GesCRTL should be developed as a sequence of bounded product capabilities. The roadmap below records the overall product direction; it is not one giant implementation specification.

For each substantial capability, follow the Spec Kit workflow appropriate to the installed version:

1. **Specify** the user problem, user journey, requirements, and acceptance scenarios.
2. **Clarify** important ambiguities before committing to a solution.
3. **Plan** the technical approach and architecture for that capability.
4. **Create a checklist** where useful to validate quality and completeness.
5. **Generate tasks** that can be implemented and verified in small increments.
6. **Analyze** the spec, plan, and tasks for gaps or contradictions.
7. **Implement and verify** the feature against its acceptance criteria.
8. **Converge/review** the result, update documentation, and capture lessons before moving on.

Use the exact command names and generated file layout supported by the Spec Kit version and coding agent configured in the repository. Do not create all detailed specifications up front: keep the roadmap broad, then develop the next capability when it is ready to start.

A project constitution should be established first. It should encode the product principles above along with engineering expectations such as modularity, testability, configuration, privacy-conscious camera handling, and measurable acceptance criteria.

---

## 4. Phased Roadmap

### Phase 0 — Product Foundation and Interaction Model

**Outcome:** A shared definition of what GesCRTL is and how it should feel to use.

- Establish the project constitution and product principles.
- Define primary users, key use cases, first-release boundaries, and success criteria.
- Define application states: Inactive, Paused, Active, and Tracking Lost (the application starts in Paused).
- Define the four planned interaction modes: Pointer, Keyboard, Presentation, and Media/System.
- Establish the gesture vocabulary rules, mode-switching concept, visual feedback, and accidental-action policy.
- Decide the pointer mapping model (absolute active-region mapping vs. relative movement with a clutch).
- Run a technical spike and record decisions as ADRs: language/stack, hand-tracking library, input injection method, HUD overlay approach, and packaging.
- Measure end-to-end latency, frame rate, and CPU usage of the spike on a real laptop to validate the performance budget.
- Document known platform limits: Windows UIPI blocks input to elevated windows, the secure desktop (UAC prompts, lock screen, Ctrl+Alt+Del) cannot be controlled, and the webcam may be held exclusively by video-call apps.
- Record the roadmap and prioritize the first usable release.

**Exit criterion:** The user journey, core terminology, mode model, release boundaries, key technical decisions, and known platform limits are documented and internally consistent.

### Phase 1 — Pointer Mode MVP

**Outcome:** Users can perform essential mouse/touchpad tasks through the webcam.

- Move the cursor.
- Left-click, right-click, and double-click.
- Click-and-drag.
- Scroll vertically; consider horizontal scrolling if it fits the first usable release.
- Provide a minimal engage/clutch, pause/resume, and kill switch (gesture plus global hotkey) so the cursor does not follow every visible hand movement.
- Smooth cursor motion (adaptive filter such as One Euro) and stabilize the cursor at the moment of a click so clicks land where the user aimed.
- Anchor the cursor to a stable hand point (palm center or knuckle), not a fingertip.
- Handle display scaling (per-monitor DPI awareness) on the primary monitor.
- Offer basic cursor sensitivity and precision adjustment through a simple configuration file.
- Release any held mouse button when tracking is lost or control is paused.
- Provide enough visual feedback to communicate pointer readiness and action recognition.
- Build a landmark record-and-replay harness so gesture and state logic can be tested automatically without a camera.

**Exit criterion:** A user can complete a small set of everyday desktop tasks without reaching for a physical mouse, can pause and resume control at will, and behavior is stable enough for a practical demo.

### Phase 2 — Interaction Reliability Hardening

**Outcome:** Users trust the system not to act unexpectedly.

- Refine activation, pause, and resume interactions based on Phase 1 usage.
- Handle hand loss, camera interruption (including the camera being taken by another app), and uncertain tracking safely.
- Lock control to one primary hand and ignore other hands or people in the frame.
- Prevent repeated triggers and accidental clicks using confidence gating, hysteresis, and cooldowns.
- Give clear feedback when GesCRTL is active, paused, or unable to track the hand.
- Measure the false-trigger rate on recorded sessions (idle hand, typing, talking) and tune until it meets the target.

**Exit criterion:** The system's active state is obvious, interruptions are handled predictably, unsafe actions are not issued when tracking is unreliable, and the measured false-trigger rate meets the target.

### Phase 3 — Mode System and On-Screen Guidance

**Outcome:** GesCRTL becomes a coherent input system instead of a collection of gestures.

- Add mode selection and mode switching.
- Show the current mode in a compact heads-up display (HUD).
- Display only the relevant gesture hints for the active mode.
- Define which gestures are global and which are mode-specific.
- Keep mode transitions deliberate and easy to understand.

**Exit criterion:** Users can identify their current mode, switch modes reliably, and understand what the available gestures will do.

### Phase 4 — Presentation Mode

**Outcome:** Users can present without a physical presentation remote.

- Move to the next and previous slide.
- Provide a presentation pointer or virtual laser pointer.
- Stabilize the pointer enough for practical pointing.
- Start and end presentation actions where reliably supported.
- Validate tracking at typical presenting distances (about 2–4 m from a laptop webcam) and document the supported range.
- Consider on-screen annotation, erasing, and clearing annotations as an extension.

**Exit criterion:** A user can deliver a basic slide presentation from a documented distance and point to slide content without touching a remote or mouse.

### Phase 5 — Keyboard Mode

**Outcome:** Users can complete common text-entry and keyboard tasks without a physical keyboard.

**5a — On-screen keyboard and shortcuts (first-release candidate)**

- Provide a virtual on-screen keyboard.
- Support selecting and confirming keys.
- Include essential keys and actions: letters, numbers, space, backspace, enter, and modifiers.
- Evaluate dwell-to-type and pinch-to-type interactions.
- Provide gesture access to common keyboard shortcuts (for example copy, paste, undo, Alt+Tab, Windows key).
- Add text-entry feedback.
- Consider word suggestions or other methods to reduce repetitive selection.

**5b — Two-handed air typing (research, deferred)**

- Investigate typing with both hands on a virtual keyboard in the air. This is research-grade with a single RGB webcam (no depth, fingers hide each other) and must not block the first release.

**Exit criterion:** Users can enter short text and perform common keyboard actions with a documented, understandable interaction method. Do not claim typing speed parity with a physical keyboard unless measured evidence supports it.

### Phase 6 — Media and Common System Controls

**Outcome:** Users can control common playback and desktop actions hands-free.

- Play/pause, next/previous track, volume, and mute.
- Add selected system actions such as screenshots or application switching where they work reliably.
- Keep potentially disruptive actions deliberate and easy to cancel.
- Reuse the mode and feedback system rather than introducing unrelated gestures for each action.

**Exit criterion:** The supported actions work consistently in the declared environments and users can understand or customize their mappings.

### Phase 7 — Settings and Personalization

**Outcome:** Users can adapt GesCRTL to their preferences without making initial setup complicated.

- Provide settings for sensitivity, movement range, and relevant timing thresholds.
- Allow supported gestures to be mapped to supported actions.
- Save and restore user preferences.
- Offer sensible defaults and a simple reset-to-default option.
- Consider named profiles only if real use cases justify them.

**Exit criterion:** Users can adjust the key experience and restore defaults without editing source code.

### Phase 8 — Custom Gesture Learning (Advanced)

**Outcome:** Users can define a custom gesture for a supported action, where this is more useful than ordinary configuration.

- Record examples of a user-defined gesture.
- Provide clear enrollment guidance and feedback about recording quality.
- Evaluate a gesture-recognition model for custom static or dynamic gestures.
- Let users assign a learned gesture to an allowed action.
- Include a way to remove, retrain, or disable custom gestures.

**Exit criterion:** Custom gestures can be enrolled and recognized with measured reliability and cannot silently override essential safety controls. This phase should begin only after built-in gestures are dependable.

### Phase 9 — Calibration, Multi-Monitor, and Accessibility Improvements

**Outcome:** GesCRTL works across a wider range of setups and user needs.

- Guide users through camera and movement calibration.
- Improve cursor mapping across multiple monitors.
- Handle mixed resolutions and mixed display scaling across monitors (single-monitor scaling is handled in Phase 1).
- Offer configurable sensitivity and reduced-movement options.
- Evaluate alternative controls for users who cannot comfortably perform the default gestures.

**Exit criterion:** Supported hardware/display setups and personalization options are documented and validated.

### Phase 10 — Release Readiness and Open-Source Adoption

**Outcome:** Other people can install, understand, try, and contribute to GesCRTL.

- Package the application for the initial supported platform.
- Provide first-run setup and clear permission/camera-status messaging.
- Document supported operating systems, limitations, controls, and troubleshooting.
- Confirm automated test coverage (unit and landmark-replay tests maintained since Phase 1), plus repeatable manual acceptance tests for camera interactions.
- Include a short demo and contribution guidelines.
- Review privacy implications and avoid retaining camera footage unless a clearly explained feature explicitly requires user-authorized recording.

**Exit criterion:** A new user can install the release, understand its limitations, complete the quick start, and report reproducible issues.

---

## 5. Prioritization Rules

When deciding whether to add or delay a feature, use these rules:

- **Reliability before breadth:** a small number of dependable interactions is better than many unreliable gestures.
- **User value before novelty:** prioritize tasks users actually need to perform.
- **Mode clarity before gesture count:** avoid adding a gesture when a clear mode or existing control solves the problem more simply.
- **Demonstrable increments:** each phase should produce a testable improvement in user experience.
- **Measure before claiming:** validate false-trigger rate, recognition reliability, responsiveness, and usability where relevant.
- **Defer research-heavy capabilities:** learned gestures, advanced typing, complex window manipulation, and broad cross-platform support should not block the first usable release.

## 6. Initial Success Criteria

The first milestone is successful when a new user can:

1. Start GesCRTL and understand whether gesture control is active.
2. Move the cursor, click, drag, and scroll with the webcam.
3. Pause control quickly and resume intentionally.
4. Understand when the camera or hand tracking is unavailable.
5. Complete a short everyday desktop demonstration without unexpected actions.

Initial measurable targets (to be validated in the Phase 0 spike and refined in specs):

| Metric | Initial target |
|---|---|
| End-to-end latency (camera frame → OS input) | ≤ 80 ms at p95 |
| Hand-tracking frame rate | ≥ 25 FPS |
| Unintended clicks during 10 minutes of visible but non-controlling hands | 0 |
| CPU usage when no hand is present | ≤ 5% of total CPU at about 10 FPS processing (measured 1.3% in Phase 0, see docs/measurements/feasibility-report.md) |

Later phases should define their own measurable acceptance criteria during their individual Spec Kit cycles.

---

**Guiding principle:** GesCRTL should feel like a new input device that happens to use a webcam—not like a user being asked to memorize a large set of gestures.
