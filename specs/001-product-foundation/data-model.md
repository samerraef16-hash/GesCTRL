# Data Model: Product Foundation and Interaction Model (Phase 0)

This is the conceptual model that `docs/interaction/*.md` must express and that Phase 1 code will
implement. It contains no implementation types.

## Entities

### ApplicationState
| Field | Values / rules |
|---|---|
| `state` | `Inactive` \| `Paused` \| `Active` \| `TrackingLost` (exactly one at a time) |
| `substate` | Active only: `Normal` \| `ModeMenuOpen` \| `Clutched` |
| `lost_reason` | TrackingLost only: `HandMissing` \| `CameraUnavailable` |
| `camera_running` | `false` only in `Inactive` |
| `processing_rate` | Full in Active/TrackingLost; reduced (start at 10 FPS) in Paused |
| `input_allowed` | `true` only when `state = Active`, `substate = Normal`, and confidence ≥ threshold |

Invariants:
- Entering any state other than Active, any change of `mode`, opening the mode menu, emergency
  stop, shutdown, and failure all trigger **ReleaseAll** (every held button and key is released).
- On launch the state is `Paused` (FR-005a).

### InteractionMode
| Field | Values / rules |
|---|---|
| `mode` | `Pointer` (default) \| `Keyboard` \| `Presentation` \| `MediaSystem` |
| `previous_mode` | Used when the mode menu is cancelled (mode unchanged) |

Exactly one mode is current. It is kept across Paused and TrackingLost and restored on return to
Active. Only Pointer has gestures in the first release; the other modes are placeholders until
their phases.

### PrimaryHand
| Field | Rules |
|---|---|
| `last_position` | Last smoothed palm-center position (normalized frame coordinates) |
| `confidence` | Tracker presence/landmark confidence for the current frame |
| `missing_frames` | Consecutive frames without the primary hand or below confidence |

Rules (research R11):
- The hand performing the resume gesture becomes primary.
- Continuity is kept by the nearest wrist position.
- On reappearance after TrackingLost, a single hand in the active region is accepted; if several
  appear, the one nearest `last_position` is chosen.

### Gesture
| Field | Rules |
|---|---|
| `id` | G1–G7 (see research R10) |
| `hand_form` | Plain-language description (either hand) |
| `scope` | `Global` or `Mode:<mode>`; may be restricted to specific states (e.g., G6 Paused-only) |
| `min_hold_ms` | Hold time before it counts (e.g., resume 1000, mode menu 800, pause 1500) |
| `enter_threshold` / `exit_threshold` | Separate start/release values (hysteresis); exit is looser than enter |
| `cooldown_ms` | Minimum time before the same discrete action can repeat |

Validation: within one scope and state, no two gestures share a hand form (SC-002). There are at
most 8 gestures in total (SC-003).

### Action
| Field | Rules |
|---|---|
| `kind` | `CursorMove` \| `LeftClick` \| `DoubleClick` \| `DragStart` \| `DragEnd` \| `RightClick` \| `Scroll` \| `StateChange` \| `ModeChange` |
| `consequential` | `false` only for `CursorMove`; all others are consequential and subject to SafetyRules |

### SafetyRule
| Field | Rules |
|---|---|
| `min_confidence` | Below this, no consequential action is emitted |
| `min_stable_frames` | Gesture must be held consistently for N frames before it counts |
| `hysteresis` | Separate enter/exit thresholds per gesture |
| `cooldown_ms` | Per discrete action |
| `loss_confirmation_frames` | Frames missing before TrackingLost is declared (start: 3, research R9) |
| `click_stabilization_ms` | Cursor frozen or snapped back at pinch onset (start: 100 ms) |

### FeedbackIndicator
See [contracts/hud-feedback.md](./contracts/hud-feedback.md). It shows `state`, `mode`,
`lost_reason`, and up to 4 hints for the current mode. It never takes focus and never intercepts
clicks.

### DecisionRecord
Fields: id, title, status (`Proposed` | `Accepted` | `Superseded`), context, options, decision,
evidence, consequences. The format is in [contracts/adr-template.md](./contracts/adr-template.md).

### KnownLimitation
Fields: situation, user-visible effect, reason, workaround (if any). There must be at least three
entries: elevated windows, secure desktop, camera in exclusive use by another app.

### PerformanceTarget
Fields: metric, target, measured value, method, conditions, pass/fail, and mitigation (if
failed). The format is in [contracts/measurement-report.md](./contracts/measurement-report.md).

## State Transition Table

Events:
- **E1** Launch
- **E2** Resume gesture (G6, open palm ≥ 1 s)
- **E3** Resume/pause hotkey or tray "Resume"
- **E4** Pause gesture (G5, fist ≥ 1.5 s)
- **E5** Emergency-stop hotkey
- **E6** Turn off (hotkey or tray)
- **E7** Turn on (hotkey or tray)
- **E8** Primary hand loss confirmed
- **E9** Primary hand reappears
- **E10** Camera becomes unavailable
- **E11** Camera available again
- **E12** Mode-menu gesture (G7 ≥ 0.8 s)
- **E13** Mode confirmed (pinch on a menu item)
- **E14** Mode menu cancelled (fist, or 5 s with no selection)
- **E15** Exit or crash
- **E16** Fist detected while Active·Normal (clutch start)
- **E17** Fist opened before 1.5 s (clutch end)

| From \ Event | Result | ReleaseAll | User feedback |
|---|---|---|---|
| (none) + E1 | Paused (camera on, reduced rate) | n/a | HUD "Paused — show open palm to start" |
| Paused + E2 / E3 | Active (previous mode, default Pointer) | n/a | HUD "Active · Pointer" |
| Paused + E4 / E5 | Paused (no change) | yes | n/a |
| Paused + E6 | Inactive (camera released) | yes | HUD hidden; tray shows "Off" |
| Paused + E8 / E9 | Paused (no change; auto-resume never applies to Paused) | n/a | n/a |
| Paused + E10 | Paused, camera-unavailable flag set | n/a | HUD "Paused · Camera unavailable" |
| Paused + E11 | Paused, flag cleared | n/a | HUD "Paused" |
| Active + E3 / E4 / E5 | Paused | **yes** | HUD "Paused" (+ "Emergency stop" label for E5) |
| Active + E6 | Inactive | **yes** | HUD hidden; tray "Off" |
| Active + E8 | TrackingLost (`HandMissing`) | **yes** (immediate) | HUD "Hand not visible" |
| Active + E10 | TrackingLost (`CameraUnavailable`) | **yes** | HUD "Camera unavailable" |
| Active + E16 | Active / `Clutched` (cursor frozen) | yes | HUD "\<Mode\> · Hold" |
| Active·Clutched + E17 | Active / `Normal` | n/a | HUD "\<Mode\>" |
| Active·Clutched + E4 (fist reaches 1.5 s) | Paused | yes | HUD "Paused" |
| Active + E12 | Active / `ModeMenuOpen` | **yes** | Mode menu shown, current mode highlighted |
| Active·ModeMenuOpen + E13 | Active / `Normal`, new mode | yes | HUD "Active · \<mode\>" + hints for 3 s |
| Active·ModeMenuOpen + E14 | Active / `Normal`, mode unchanged | n/a | Menu closes |
| Active·ModeMenuOpen + E8 | TrackingLost, menu closed, mode unchanged | yes | HUD "Hand not visible" |
| TrackingLost(HandMissing) + E9 | Active (same mode), automatic | n/a | HUD "Active · \<mode\>" |
| TrackingLost(CameraUnavailable) + E11 | TrackingLost(`HandMissing`) until hand seen | n/a | HUD "Hand not visible" |
| TrackingLost + E3 / E4 / E5 | Paused | yes | HUD "Paused" |
| TrackingLost + E6 | Inactive | yes | HUD hidden |
| Inactive + E7 | Paused (camera on) | n/a | HUD "Paused" |
| Inactive + any gesture event | Ignored (camera off) | n/a | n/a |
| Inactive + E5 | No effect (nothing acting) | n/a | n/a |
| Any + E15 | Process ends | **yes** (exit handler) | n/a |

Rules that apply to every row:
- Gestures that occur while a transition is completing are ignored.
- Every transition not listed above is a no-op. `interaction-model.md` must keep this table
  complete for every state × event pair (SC-001).
