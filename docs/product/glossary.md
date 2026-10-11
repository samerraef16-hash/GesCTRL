# GesCRTL Glossary

> Source: spec.md (FR-005a, FR-018), data-model.md, research.md R8–R11.

Use these terms exactly. Each has one definition.

## States

- **State**: The overall operating condition of the application. Exactly one at a time:
  Inactive, Paused, Active, or Tracking Lost. It decides whether input may be sent and whether
  the camera runs.
- **Inactive**: The camera is fully stopped and released; no input is sent. Entered by "Turn off"
  and left only by keyboard shortcut, tray, or relaunch.
- **Paused**: The camera keeps running at a reduced processing rate and no input is sent. Only a
  deliberate resume gesture, the shortcut, or the tray leaves it. The application starts here.
- **Active**: The camera runs at full rate and input may be sent in the current mode, when
  tracking confidence is sufficient. Has substates Normal, Clutched, and ModeMenuOpen.
- **Tracking Lost**: A state entered when the primary hand is missing (HandMissing) or the camera
  is unavailable (CameraUnavailable). No input is sent and held input is released.

## Modes

- **Mode**: The context that decides what mode-specific gestures mean. Exactly one is current.
- **Pointer Mode**: The default mode; controls the cursor, clicks, drag, and scroll.
- **Scroll (wheel pose)**: A fist with the thumb out sideways. Tilting the thumb up or down scrolls
  up or down, faster the more it is tilted from where the pose started, like a held scroll wheel.
- **Keyboard Mode**: A later-phase mode for text entry and shortcuts.
- **Presentation Mode**: A later-phase mode for slide control and a virtual pointer.
- **Media/System Mode**: A later-phase mode for playback and common system actions.
- **Mode menu**: The on-screen menu, opened by holding the three-finger gesture, for choosing a
  mode by pointing and confirming.

## Gestures

- **Gesture**: A recognized hand form (or hand form held for a time) that maps to an intent.
- **Hand form**: The plain-language shape of the hand, for example a thumb–index pinch.
- **Global gesture**: A gesture available in every mode (pause, resume, mode menu).
- **Mode-specific gesture**: A gesture whose meaning exists only in one mode.
- **Primary hand**: The single hand currently in control; all other hands produce no input.

## Control actions

- **Clutch**: The flat hand (upright, palm toward the camera, fingers together, thumb tucked across
  the palm); the cursor freezes and no action is sent.
- **Pause**: Moving to Paused, by the flat hand held for the pause hold time (1.5 s), shortcut, or tray.
- **Resume**: Leaving Paused to Active, by open palm held for the resume hold time, shortcut, or
  tray.
- **Turn off**: Moving to Inactive (camera released) by shortcut or tray only.
- **Turn on**: Leaving Inactive; goes to Paused.
- **Emergency stop**: An immediate move to Paused with all held input released, by the hotkey or
  the pause gesture.

## Safety

- **Consequential action**: Any action other than cursor movement (clicks, drags, scrolls, state
  and mode changes). Subject to all safety rules.
- **ReleaseAll**: Releasing every held mouse button and key. Happens on every transition that
  stops or changes input.
- **Confidence**: How sure the tracker is that a hand is present and correctly read, from 0 to 1.
- **Hysteresis**: Separate start and release thresholds so a value hovering near one threshold
  does not flicker.
- **Stability time**: How many consecutive frames a gesture must be held before it counts.
- **Cooldown**: The minimum time before the same discrete action can repeat.
- **Loss-confirmation window**: The number of consecutive missing frames (start: 3) before
  Tracking Lost is declared.

## Pointer concepts

- **Active region**: The part of the mirrored camera view (start: central 60% × 60%) that maps to
  the whole primary monitor.
- **Anchor point (palm center)**: The average of the wrist and the four finger-base knuckles; it
  drives the cursor because it barely moves when pinching.
- **Smoothing**: Filtering of the cursor position to remove jitter (One Euro filter).

## Project terms

- **HUD**: The compact on-screen indicator showing state, mode, and hints. Never takes focus or
  blocks clicks.
- **Decision record (ADR)**: A short document recording one technical decision, its options, and
  its evidence.
- **Known limitation**: A documented situation GesCRTL cannot handle, with its user-facing
  explanation.

## Avoid

Do not say "sleep", "standby", "disabled", "gesture mode", or "laser mode". Use the terms above.
