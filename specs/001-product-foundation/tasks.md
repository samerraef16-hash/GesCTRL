---

description: "Task list for Phase 0 — Product Foundation and Interaction Model"
---

# Tasks: Product Foundation and Interaction Model (Phase 0)

**Input**: Design documents from `/specs/001-product-foundation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: The spec does not ask for automated tests. The spike is throwaway and exempt from tests
(plan.md, Complexity Tracking). Instead, each spike module ends with a small
`if __name__ == "__main__":` self-check, and each document task has an **Acceptance** line.

**Organization**: Tasks are grouped by user story so each story can be done and checked on its
own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 from spec.md
- Indented lines under a task are **required details**, not optional hints.

---

## ⚠️ Rules for the implementer (read before every task)

1. **Read the referenced source sections first.** Every task names the files it copies values
   from. Copy values exactly. Do not invent new thresholds, names, gestures, or states.
2. **Code lives only in `spikes/feasibility/`.** Do NOT create `src/`, `tests/`, `pyproject.toml`,
   or any product package. Do NOT import spike code from anywhere else.
3. **Privacy (FR-020):** never write camera frames or images to disk (`cv2.imwrite`,
   `VideoWriter`, `np.save` of frames, screenshots). Never open network connections in spike
   code. Only numbers and landmark coordinates may be saved.
4. **Safety:** spike code may only *move* the cursor. NEVER send mouse button or keyboard events
   (no `MOUSEEVENTF_LEFTDOWN/UP`, `RIGHTDOWN/UP`, `WHEEL`, `KEYEVENTF_*`).
5. **`HUMAN:` tasks** need a person in front of the webcam. An LLM may prepare commands and
   templates for them but MUST NOT fill in measured numbers itself. Leave `TBD` until the human
   provides results.
6. **Never invent measurements.** Every number in `docs/measurements/` or `docs/adr/` must come
   from files in `spikes/feasibility/out/` or from the human.
7. Values marked *(provisional)* are starting points; T039 replaces them with measured values.
8. Write documents in plain English Markdown, use the glossary terms from T005 exactly, and add a
   `> Source:` line under each document title listing the spec/research sections used.
9. Windows paths and PowerShell are the target environment. Python 3.11 or 3.12, 64-bit.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create folders and spike project files.

- [x] T001 Create the folder skeleton: `docs/product/`, `docs/interaction/`, `docs/adr/`, `docs/measurements/`, `spikes/feasibility/models/`, `spikes/feasibility/out/`. Put an empty `.gitkeep` file in `spikes/feasibility/models/` and `spikes/feasibility/out/`.
  - Acceptance: all six folders exist. No `src/` folder exists.
- [x] T002 [P] Create or append to the repository root `.gitignore` (D:\Portfolio\gescrtl\.gitignore), keeping existing lines, with exactly these entries: `spikes/feasibility/out/*`, `!spikes/feasibility/out/.gitkeep`, `spikes/feasibility/models/*.task`, `spikes/feasibility/.venv/`, `spikes/feasibility/build/`, `spikes/feasibility/dist/`, `spikes/feasibility/*.spec`, `__pycache__/`.
  - Acceptance: `git status` does not show `.venv`, `.task` files, or `out/` contents.
- [x] T003 [P] Create `spikes/feasibility/requirements.txt` with one package per line, unpinned: `mediapipe`, `opencv-python`, `numpy`, `psutil`. Add a comment line at the top: `# Throwaway Phase 0 spike. After install run: pip freeze > requirements.lock.txt`.
- [x] T004 [P] Create `spikes/feasibility/README.md` with these sections:
  - **"⚠️ Disposable"**: this code is a throwaway feasibility spike (spec FR-012). It must never become product code. Phase 1 starts fresh in `src/`.
  - **"Setup"**: the PowerShell commands:
    ```
    cd spikes\feasibility
    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    pip freeze > requirements.lock.txt
    Invoke-WebRequest -Uri https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task -OutFile models\hand_landmarker.task
    ```
    Note that `py -3.11` also works if 3.12 has no MediaPipe wheel.
  - **"Files"**: one line per module from T017–T025.
  - **"Safety"**: `Ctrl+Alt+Esc` stops the spike. The spike only moves the cursor and never clicks.
  - **"Privacy"**: no images are saved and there is no network use after the model download.
  - Acceptance: the README contains the model URL and all three warnings.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared vocabulary and design-doc fixes that every later task depends on.

**⚠️ CRITICAL**: Finish this phase before Phases 3–6.

- [x] T005 Create `docs/product/glossary.md` (FR-018). Give a one- or two-sentence definition for each term, in this order:
  - State; Inactive; Paused; Active; Tracking Lost
  - Mode; Pointer Mode; Keyboard Mode; Presentation Mode; Media/System Mode; Mode menu
  - Gesture; Hand form; Global gesture; Mode-specific gesture; Primary hand
  - Clutch; Pause; Resume; Turn off; Turn on; Emergency stop
  - Consequential action; ReleaseAll; Confidence; Hysteresis; Stability time; Cooldown;
    Loss-confirmation window
  - Active region; Anchor point (palm center); Smoothing; HUD; Decision record (ADR);
    Known limitation

  Sources:
  - State definitions: data-model.md "ApplicationState" and spec FR-005a. Paused = camera on at
    reduced rate, no input. Inactive = camera off.
  - Emergency stop: spec FR-005. It leads to Paused.
  - Clutch and Pause: research.md R10, G5. Fist held < 1.5 s = clutch; ≥ 1.5 s = pause.
  - Loss-confirmation window: research.md R9.
  - Anchor point: research.md R8.

  Add an **"Avoid"** list: do not say "sleep", "standby", "disabled", "gesture mode", or
  "laser mode". Use the canonical terms instead.
  - Acceptance: 33 terms are defined, each with exactly one definition, and no definition
    contradicts spec.md.
- [x] T006 [P] Edit `specs/001-product-foundation/data-model.md` to add the clutch events.
  - In the "State Transition Table" events paragraph, add **E16 Fist detected while Active·Normal
    (clutch start)** and **E17 Fist opened before 1.5 s (clutch end)**.
  - Add these table rows:
    - `Active + E16 | Active / Clutched (cursor frozen) | yes | HUD "<Mode> · Hold"`
    - `Active·Clutched + E17 | Active / Normal | n/a | HUD "<Mode>"`
    - `Active·Clutched + E4 (fist reaches 1.5 s) | Paused | yes | HUD "Paused"`
  - Change nothing else.
- [x] T007 [P] Edit `specs/001-product-foundation/plan.md`, section "Source Code (repository root)". Inside the `spikes/feasibility/` tree:
  - Add `hotkey.py  # Global emergency-stop hotkey (RegisterHotKey thread)`,
    `tracking.py  # Latest-frame camera grabber, HandLandmarker wrapper, hand geometry`,
    `mapping.py  # Absolute-region and relative+clutch mappers`, and
    `overlay_check.py  # Optional click-through window check (ADR 0003)`.
  - Change nothing else.
- [x] T008 [P] Edit `specs/001-product-foundation/quickstart.md`, section "A4. End-to-end delay".
  - Replace step 1 with: "Make the cursor easy to see on video: Windows Settings →
    Accessibility → Mouse pointer and touch → set Size to 5 or more. Then run
    `python spike.py --mapping absolute`."
  - Remove every mention of `--show-marker` from the file.

**Checkpoint**: Glossary exists and the design docs are consistent with the spike layout.

---

## Phase 3: User Story 1 - Interaction model: states, modes, transitions (Priority: P1) 🎯 MVP

**Goal**: One authoritative document defining every state, mode, event, and transition
(FR-001–FR-006).

**Independent Test**: A reviewer picks any state row and any event column in the matrix and finds
exactly one result plus user feedback, without asking anyone (SC-001).

- [x] T009 [US1] Create `docs/interaction/interaction-model.md` with these sections, in order:
  1. **Purpose**: 2–3 sentences.
  2. **States**: a table with columns State | Camera | Input allowed | Processing rate |
     Entered by | Left by. Rows: Inactive, Paused, Active (substates Normal, Clutched,
     ModeMenuOpen), Tracking Lost (reasons HandMissing, CameraUnavailable). Copy the values from
     data-model.md "ApplicationState" and spec FR-005a.
  3. **Startup**: the application always starts in Paused (FR-005a).
  4. **Modes**: Pointer (default), Keyboard, Presentation, Media/System. Exactly one is current.
     The mode is kept through Paused and Tracking Lost. Only Pointer has gestures in the first
     release.
  5. **Events**: a numbered list E1–E17 with the exact wording from data-model.md (including
     E16/E17 from T006).
- [x] T010 [US1] In `docs/interaction/interaction-model.md`, add the section **"Transition matrix"**.
  - Build one Markdown table. Rows (7): `Inactive`, `Paused`, `Active·Normal`, `Active·Clutched`,
    `Active·ModeMenuOpen`, `TrackingLost(HandMissing)`, `TrackingLost(CameraUnavailable)`.
    Columns: E2–E17 (E1 is described in the Startup section only).
  - Cell format: `→ <NewState> · RA · "<HUD text>"`. Write `RA` only when ReleaseAll happens.
    Write `no-op` when nothing happens. Write `n/a` when the event cannot occur in that state.
  - Fill every cell using data-model.md "State Transition Table" plus these exact rules:
    - **Inactive**: E7 → Paused. E15 → exit · RA. E5 → no-op. Every gesture event (E2, E4, E12,
      E13, E14, E16, E17) → `n/a (camera off)`. Everything else → no-op.
    - **Paused**: E2/E3 → Active·Normal (previous mode). E4/E5 → no-op · RA. E6 → Inactive · RA.
      E8/E9 → no-op. E10/E11 → toggle the camera-unavailable flag (HUD per hud-feedback
      contract). E12, E13, E14, E16, E17 → no-op. E15 → exit · RA.
    - **Active·Normal**: E3/E4/E5 → Paused · RA. E6 → Inactive · RA. E8 →
      TrackingLost(HandMissing) · RA. E10 → TrackingLost(CameraUnavailable) · RA. E12 →
      Active·ModeMenuOpen · RA. E16 → Active·Clutched · RA. E2, E7, E9, E11, E13, E14, E17 →
      no-op. E15 → exit · RA.
    - **Active·Clutched**: same as Active·Normal for E3, E5, E6, E8, E10, E15. E4 → Paused · RA.
      E17 → Active·Normal. E2, E7, E9, E11, E12, E13, E14, E16 → no-op.
    - **Active·ModeMenuOpen**: E13 → Active·Normal with the new mode · RA. E14 → Active·Normal,
      mode unchanged. E8 → TrackingLost(HandMissing), menu closed, mode unchanged · RA.
      E3/E4/E5 → Paused, menu closed · RA. E6 → Inactive · RA. E10 →
      TrackingLost(CameraUnavailable), menu closed · RA. E16/E17 → no-op (inside the menu a
      fist means E14 cancel, not clutch). E2, E7, E9, E11, E12 → no-op. E15 → exit · RA.
    - **TrackingLost(HandMissing)**: E9 → Active·Normal in the same mode (automatic, spec
      FR-001a). E3/E5 → Paused · RA. E6 → Inactive · RA. E10 →
      TrackingLost(CameraUnavailable). Gesture events E2, E4, E12, E13, E14, E16, E17 →
      `n/a (no hand)`. E7, E8, E11 → no-op. E15 → exit · RA.
    - **TrackingLost(CameraUnavailable)**: E11 → TrackingLost(HandMissing). E3/E5 → Paused · RA.
      E6 → Inactive · RA. All gesture events and E9 → `n/a (no camera)`. E7, E8, E10 → no-op.
      E15 → exit · RA.
  - HUD texts must match `specs/001-product-foundation/contracts/hud-feedback.md` exactly.
  - Below the table, add: "Gestures that occur while a transition is completing are ignored."
  - Acceptance: 7 rows × 16 columns, no empty cell.
- [x] T011 [US1] In `docs/interaction/interaction-model.md`, add these sections:
  - **"ReleaseAll"**: a bullet list of every trigger, copied from the data-model.md Invariants
    plus E16.
  - **"Emergency stop"**: two independent paths (hotkey `Ctrl+Alt+Esc` from
    contracts/global-hotkeys.md, and the pause gesture G5 held ≥ 1.5 s), plus the tray. The
    result is always Paused with ReleaseAll (FR-005).
  - **"Paused vs Inactive"**: the FR-005a text.
  - **"Primary hand"**: the 4 rules from research.md R11, word for word in meaning.
  - **"Mode menu"**: opened by G7 held ≥ 0.8 s. Point at a mode and confirm with a thumb–index
    pinch. Cancel with a fist or after 5 s with no selection. No other input while open
    (FR-002a).
  - **"Tracking loss"**: declared after the loss-confirmation window (3 frames, *provisional*,
    research R9). Then ReleaseAll happens immediately with no grace period. A drag does not
    continue after resume.
- [x] T012 [US1] Self-review `docs/interaction/interaction-model.md` against spec.md US1 acceptance scenarios 1–6 and edge cases.
  - Append a section **"Spec coverage"**: a table with Scenario/Edge case | Where answered
    (section name). Every row must point to an existing section.
  - Fix any gap found.
  - Acceptance: all 6 scenarios and all 8 edge cases are listed with a location.

**Checkpoint**: US1 is complete. The interaction model can be reviewed on its own.

---

## Phase 4: User Story 2 - Gesture vocabulary and accidental-action policy (Priority: P2)

**Goal**: A ≤ 8-gesture first-release vocabulary, safety policy, and HUD concept (FR-007–FR-011).

**Independent Test**: A reviewer confirms there is no hand form with two meanings in the same scope
and state, each gesture has its safety rules, and every gesture works with either hand (SC-002,
SC-003).

- [x] T013 [P] [US2] Create `docs/interaction/gesture-vocabulary.md`.
  - Main table with columns: ID | Hand form (plain words) | How it is recognized (plain words) |
    Scope | Valid in states | Min hold | Meaning | Either hand?
  - Rows: exactly G1–G7 from research.md R10, using these recognition descriptions:
    - G1 Relaxed hand: any detected hand that is not G2–G7.
    - G2 Thumb–index pinch: thumb tip close to index tip relative to hand size.
    - G3 Thumb–middle pinch: thumb tip close to middle fingertip.
    - G4 Index + middle extended together, ring and pinky curled.
    - G5 Closed fist: all four fingertips closer to the wrist than their middle joints.
    - G6 Open palm facing the camera: all five fingers extended.
    - G7 Index, middle, and ring extended; thumb and pinky curled.
  - Section **"Pointer Mode actions"**: map each of move, left click, double click (two G2 taps
    within the Windows double-click time, default 500 ms), drag (G2 held > 300 ms), right click,
    vertical scroll (G4 + hand moving up/down), clutch (G5 < 1.5 s) to exactly one gesture.
  - Section **"Not gestures"**: Turn off and Turn on are keyboard shortcut / tray only (research
    R10).
  - Section **"Active region"**: the central 60% × 60% of the mirrored camera view maps to the
    whole primary monitor (*provisional*, research R5). The user can rest the hand outside it.
  - Acceptance: 7 gestures (≤ 8). Every Pointer action is mapped once. Every row says "Yes" for
    either hand.
- [x] T014 [P] [US2] Create `docs/interaction/safety-policy.md` (FR-009). Use one table with columns Rule | Value | Applies to | Why, containing exactly these *(provisional)* values:
  - Minimum tracker confidence for consequential actions: 0.5.
  - Minimum stable frames before a gesture counts: 3.
  - Pinch start ratio < 0.25 and pinch release ratio > 0.35. The ratio is thumb-tip-to-fingertip
    distance ÷ wrist-to-middle-knuckle distance (hysteresis).
  - Hold times: G6 resume 1000 ms; G7 mode menu 800 ms; G5 pause 1500 ms; drag 300 ms.
  - Cooldowns: right click 300 ms; mode switch 1000 ms; resume/pause 1000 ms.
  - Click stabilization: cursor frozen for 100 ms at pinch start.
  - Loss-confirmation window: 3 consecutive frames.
  - Paused processing rate: 10 FPS.

  Then add sections:
  - **"Uncertain tracking"**: below the confidence threshold, no consequential action is emitted
    and the cursor does not move. Nothing is guessed.
  - **"ReleaseAll"**: link to the interaction-model.md section.
  - **"Primary hand only"**: other hands produce nothing.
  - **"What may never be overridden"**: emergency stop, pause, and ReleaseAll cannot be remapped
    or disabled (spec US2, Plan Phase 8).

  Add a note at the top: "Values marked provisional are updated from
  docs/measurements/feasibility-report.md in T039."
- [x] T015 [P] [US2] Create `docs/interaction/feedback-hud.md` (FR-011).
  - Copy the three sections of `specs/001-product-foundation/contracts/hud-feedback.md` (Window
    behavior, Content per state, Rules) exactly.
  - Add **"Mode menu layout"**: four items in a row (Pointer, Keyboard, Presentation,
    Media/System), the current one highlighted, the hovered one outlined. Footer text:
    "Pinch to choose · Fist to cancel". It closes automatically after 5 s.
  - Add **"Hints per mode"**. Pointer: "Pinch: click", "Hold pinch: drag", "Two fingers: scroll",
    "Fist: hold · keep fist: pause". Other modes: "Coming in a later phase".
- [x] T016 [US2] Append a section **"Conflict check"** to `docs/interaction/gesture-vocabulary.md`.
  - Add one table per state (Paused, Active·Normal, Active·Clutched, Active·ModeMenuOpen) listing
    which gestures are recognized there and what they mean. Use T010's matrix and T013's table.
  - Confirm, in writing, that no hand form has two meanings in the same state. Example: G6 only
    acts in Paused; in Active it is just G1 movement. G5 in ModeMenuOpen means cancel, not clutch.
  - Acceptance: one table per state, and a one-line "No conflicts found" statement (or a fix).

**Checkpoint**: US1 and US2 are complete. The Phase 1 Pointer MVP has a clear, safe target.

---

## Phase 5: User Story 3 - Feasibility validated against performance targets (Priority: P3)

**Goal**: A throwaway spike that moves the cursor, measurements against Plan.md §6, and five ADRs
(FR-012–FR-015, FR-020).

**Independent Test**: Running `measure.py` on the reference laptop produces a summary JSON. The
report shows pass/fail for delay (≤ 80 ms p95) and FPS (≥ 25).

### Spike code (all files in `spikes/feasibility/`)

- [x] T017 [P] [US3] Create `spikes/feasibility/winput.py`. This is the ONLY file with Win32 cursor code.
  - Use `import ctypes` and `from ctypes import wintypes`.
    `user32 = ctypes.WinDLL("user32", use_last_error=True)`. `ULONG_PTR = ctypes.c_size_t`.
  - Define structures exactly:
    - `MOUSEINPUT(dx LONG, dy LONG, mouseData DWORD, dwFlags DWORD, time DWORD, dwExtraInfo ULONG_PTR)`
    - `KEYBDINPUT(wVk WORD, wScan WORD, dwFlags DWORD, time DWORD, dwExtraInfo ULONG_PTR)`
    - `HARDWAREINPUT(uMsg DWORD, wParamL WORD, wParamH WORD)`
    - `class _INPUTUNION(ctypes.Union)` with fields `mi`, `ki`, `hi`
    - `INPUT(type DWORD, u _INPUTUNION)`
  - Module-level check: `assert ctypes.sizeof(INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)`.
  - Constants: `INPUT_MOUSE = 0`, `MOUSEEVENTF_MOVE = 0x0001`, `MOUSEEVENTF_ABSOLUTE = 0x8000`,
    `MOUSEEVENTF_VIRTUALDESK = 0x4000`, `SM_CXSCREEN = 0`, `SM_CYSCREEN = 1`,
    `SM_XVIRTUALSCREEN = 76`, `SM_YVIRTUALSCREEN = 77`, `SM_CXVIRTUALSCREEN = 78`,
    `SM_CYVIRTUALSCREEN = 79`.
  - Set `user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]` and
    `restype = wintypes.UINT`.
  - Functions:
    - `set_dpi_awareness() -> str`: try `user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))`
      (per-monitor v2) and return `"per-monitor-v2"` if it returns nonzero. Otherwise try
      `ctypes.windll.shcore.SetProcessDpiAwareness(2)` and return `"per-monitor"`. Otherwise
      return `"unaware"`. It must be called before anything else.
    - `primary_screen_rect() -> tuple[int, int, int, int]` returns `(left=0, top=0, width, height)`
      from `GetSystemMetrics(0)` and `(1)`.
    - `virtual_screen_rect()` uses metrics 76–79.
    - `get_cursor_pos() -> tuple[int, int]` via `GetCursorPos` with `wintypes.POINT`.
    - `move_cursor_abs(x: int, y: int) -> None`: clamp to the virtual rect.
      `nx = round((x - vx) * 65535 / max(vw - 1, 1))`, same for y. Send one INPUT with
      `dwFlags = MOVE | ABSOLUTE | VIRTUALDESK`. If the return value is not 1, raise
      `ctypes.WinError(ctypes.get_last_error())`.
  - **Do NOT** define any button, wheel, or keyboard sending function.
  - `__main__` self-check: print the DPI mode and screen rects, move the cursor to the screen
    center, sleep 0.2 s, and assert `get_cursor_pos()` is within 2 px of the center.
- [x] T018 [P] [US3] Create `spikes/feasibility/hotkey.py` with `class HotkeyListener(threading.Thread)` (daemon=True).
  - Constructor: `__init__(self, hotkeys: dict[int, tuple[int, int]], on_hotkey: Callable[[int], None])`,
    mapping hotkey id → `(modifiers, virtual_key)`.
  - Constants: `MOD_ALT = 0x0001`, `MOD_CONTROL = 0x0002`, `MOD_SHIFT = 0x0004`,
    `MOD_NOREPEAT = 0x4000`, `VK_ESCAPE = 0x1B`, `WM_HOTKEY = 0x0312`, `WM_QUIT = 0x0012`,
    `EMERGENCY_ID = 1`, and `EMERGENCY_HOTKEY = (MOD_CONTROL | MOD_ALT, VK_ESCAPE)`.
  - `run()`: call `user32.RegisterHotKey(None, id, mods | MOD_NOREPEAT, vk)` for each hotkey
    (registration MUST happen inside `run()`, on the listener thread). Store the ids that failed
    in `self.failed`. Set `self.ready` (a `threading.Event`). Then loop on
    `GetMessageW(ctypes.byref(msg), None, 0, 0) > 0` using `wintypes.MSG`. When
    `msg.message == WM_HOTKEY`, call `on_hotkey(msg.wParam)`. In `finally`, call
    `UnregisterHotKey(None, id)` for every registered id.
  - `stop()`: `user32.PostThreadMessageW(self.native_id, WM_QUIT, 0, 0)` and then `join(1.0)`.
  - `__main__`: register Ctrl+Alt+Esc, print "Press Ctrl+Alt+Esc", and exit when it is pressed
    or after 15 s.
- [x] T019 [P] [US3] Create `spikes/feasibility/one_euro.py` (research R7).
  - `class OneEuroFilter(min_cutoff=1.0, beta=0.007, d_cutoff=1.0)` with
    `__call__(x: float, t: float) -> float`, where `t` is in seconds.
  - Algorithm, exactly:
    - `alpha(cutoff, dt) = 1 / (1 + (1 / (2*pi*cutoff)) / dt)`.
    - On the first call, store `x` and `t`, set `dx_hat = 0`, and return `x`.
    - Otherwise: `dt = t - t_prev`; if `dt <= 0`, set `dt = 1e-3`.
      `dx = (x - x_prev_hat) / dt`.
      `dx_hat = dx_hat + alpha(d_cutoff, dt) * (dx - dx_hat)`.
      `cutoff = min_cutoff + beta * abs(dx_hat)`.
      `x_hat = x_prev_hat + alpha(cutoff, dt) * (x - x_prev_hat)`.
      Store `x_hat` and `t`, and return `x_hat`.
  - `class OneEuro2D` wraps two filters: `__call__(x, y, t) -> tuple[float, float]`, plus
    `reset()`.
  - `__main__`: (1) a constant input of 0.5 for 60 samples at 1/30 s returns 0.5 (abs error
    < 1e-9). (2) A step from 0 to 1, fed for 2 s at 30 Hz, ends within 0.01 of 1.0. Print "OK".
- [x] T020 [US3] Create `spikes/feasibility/tracking.py`.
  - **`class LatestFrameGrabber(threading.Thread)`** (daemon):
    - Constructor: `__init__(camera_index=0, width=640, height=480, fps=30)`. Open
      `cv2.VideoCapture(index, cv2.CAP_MSMF)`; if it is not opened, retry with `cv2.CAP_DSHOW`;
      if it is still not opened, raise `RuntimeError("Camera unavailable")`. Set
      `CAP_PROP_FOURCC = cv2.VideoWriter_fourcc(*"MJPG")`, width, height, FPS, and
      `CAP_PROP_BUFFERSIZE = 1`. Store the actual values from `cap.get(...)` in
      `self.actual = {"width", "height", "fps"}`.
    - `run()` loops `ok, frame = cap.read()`. When ok, under a lock, store `frame`,
      `t_capture_ns = time.perf_counter_ns()` (taken immediately after `read` returns), and
      `seq += 1`.
    - `latest(last_seq: int) -> tuple[int, np.ndarray, int] | None` returns
      `(seq, frame, t_capture_ns)` only if `seq != last_seq`.
    - `stop()` sets the stop flag, joins, and calls `cap.release()`.
    - It NEVER writes frames anywhere.
  - **`@dataclass Hand`**: `landmarks: list[tuple[float, float, float]]` (21 entries),
    `world_landmarks: list[tuple[float, float, float]] | None`, `handedness: str`,
    `handedness_score: float`.
  - **`class HandTracker`**:
    - Constructor: `__init__(model_path="models/hand_landmarker.task", num_hands=2)`, using
      `import mediapipe as mp`, `from mediapipe.tasks import python as mp_python`, and
      `from mediapipe.tasks.python import vision`. Build
      `vision.HandLandmarkerOptions(base_options=mp_python.BaseOptions(model_asset_path=model_path), running_mode=vision.RunningMode.VIDEO, num_hands=num_hands, min_hand_detection_confidence=0.5, min_hand_presence_confidence=0.5, min_tracking_confidence=0.5)`
      and call `vision.HandLandmarker.create_from_options(...)`.
    - `detect(frame_bgr, t_ns) -> list[Hand]`:
      - `frame = cv2.flip(frame_bgr, 1)` (mirror).
      - `rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)`.
      - `mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)`.
      - `ts_ms = t_ns // 1_000_000`, forced strictly increasing (`if ts_ms <= last: ts_ms = last + 1`).
      - Call `detect_for_video(image, ts_ms)` and build `Hand` objects from
        `result.hand_landmarks[i]` (x, y, z), `result.hand_world_landmarks[i]`, and
        `result.handedness[i][0].category_name` / `.score`.
    - `close()`.
  - **Geometry functions**, using 2D distance on (x, y) only:
    - `palm_center(lms) -> (x, y)`: mean of indices 0, 5, 9, 13, 17.
    - `hand_size(lms)`: distance 0→9.
    - `pinch_ratio(lms, tip=8)`: distance(4, tip) / hand_size.
    - `is_fist(lms)`: True if distance(tip, 0) < distance(pip, 0) for all of
      (8, 6), (12, 10), (16, 14), (20, 18).
  - **`class PrimaryHandSelector`**: `select(hands) -> Hand | None`.
    - No hands → None (keep `last`).
    - If `last` is None, pick the highest `handedness_score`.
    - Otherwise pick the hand whose `palm_center` is nearest `last`.
    - Update `last`. Also provide `reset()`.
  - `__main__`: open the camera and tracker, run 150 frames, print FPS and the number of frames
    with a hand. No window.
- [x] T021 [P] [US3] Create `spikes/feasibility/mapping.py` (research R5).
  - **`class AbsoluteMapper(screen_rect, region=0.6)`** with `map(x, y) -> tuple[int, int]`:
    - `edge = 0.5 - region / 2`.
    - `u = clamp((x - edge) / region, 0, 1)`, `v = clamp((y - edge) / region, 0, 1)`.
    - Return `(left + round(u * (width - 1)), top + round(v * (height - 1)))`.
  - **`class RelativeMapper(screen_rect, gain=2.5)`** with
    `map(x, y, clutched: bool, cursor: tuple[int, int]) -> tuple[int, int] | None`:
    - If `last` is None or `clutched`: set `last = (x, y)` and return None.
    - Otherwise compute `nx = cursor_x + (x - last_x) * gain * width`, same for y. Clamp to the
      screen, update `last`, and return the rounded position.
    - `reset()` sets `last = None`.
  - `__main__` asserts:
    - Absolute: (0.5, 0.5) → screen center ±1 px; (0.2, 0.2) → (left, top); (0.8, 0.8) →
      (right − 1, bottom − 1); (0.0, 1.0) clamps.
    - Relative: the first call returns None; a clutched call returns None; a 0.01 move with gain
      2.5 on a 1920-wide screen moves 48 px.
- [x] T022 [US3] Create `spikes/feasibility/spike.py` (depends on T017–T021).
  - **`@dataclass FrameResult`**: `seq`, `t_capture_ns`, `t_pickup_ns`, `t_infer_ns`,
    `t_filter_ns`, `t_inject_ns: int | None`, `hands: list[Hand]`, `primary: Hand | None`,
    `cursor: tuple[int, int] | None`, `clutched: bool`.
  - **`class Pipeline(args)`** owns the HandTracker, PrimaryHandSelector, OneEuro2D, and mapper.
    `step(frame, t_capture_ns, seq) -> FrameResult` does the following:
    1. Record `t_pickup = perf_counter_ns()`.
    2. Detect hands; set `t_infer`.
    3. Select the primary hand.
    4. If there is no primary hand: reset nothing and leave the cursor unchanged.
    5. Otherwise: `clutched = is_fist(primary)`; smooth `palm_center` with OneEuro2D using
       `t = t_capture_ns / 1e9`; map with the chosen mapper. In absolute mode, if clutched, do not
       move.
    6. Set `t_filter`.
    7. If a position was produced and `args.no_inject` is False, call
       `winput.move_cursor_abs`; set `t_inject`.
  - **`main()`**:
    1. `winput.set_dpi_awareness()` first.
    2. Start the HotkeyListener with `{EMERGENCY_ID: EMERGENCY_HOTKEY}`. Wait on `ready` for 2 s.
       **If registration failed, print an error and exit with code 2 without moving the cursor.**
    3. Start the LatestFrameGrabber.
    4. Loop until the stop event is set (set by the hotkey callback or `KeyboardInterrupt`): get
       the latest frame; if none, `time.sleep(0.001)`; respect `--max-rate N` (skip frames so at
       most N are processed per second; 0 = unlimited); call `step`; print FPS once per second.
    5. In `finally`, stop the grabber, close the tracker, and stop the hotkey listener.
  - **CLI (argparse)**: `--mapping {absolute,relative}` (default absolute), `--region 0.6`,
    `--gain 2.5`, `--camera 0`, `--width 640`, `--height 480`, `--fps 30`, `--min-cutoff 1.0`,
    `--beta 0.007`, `--d-cutoff 1.0`, `--model models/hand_landmarker.task`, `--no-inject`,
    `--max-rate 0`.
  - No preview window by default; there is no option to save images.
- [x] T023 [US3] Create `spikes/feasibility/measure.py` (depends on T022). Follow the [landmark-recording contract](./contracts/landmark-recording.md) and the [measurement-report contract](./contracts/measurement-report.md).
  - **CLI**: all `spike.py` args, plus `--duration 60`,
    `--scenario {idle-hand,pointing,pinch-clicks,typing-nearby,two-people,dim-light,free}`
    (default free), `--record`, `--no-hand` (label only: sets scenario suffix `nohand`), and
    `--paused-rate N` (sets `--max-rate N` and `--no-inject`).
  - Same hotkey safety as spike.py. It runs the Pipeline for `--duration` seconds.
  - **Output prefix**: `out/<YYYYMMDD-HHMMSS>_<scenario>[_nohand][_rateN]`.
  - **`<prefix>_frames.csv`** columns: `seq, t_capture_ns, n_hands, capture_ms, inference_ms,
    filter_ms, inject_ms, total_ms`. Definitions:
    - `capture = (t_pickup - t_capture) / 1e6`
    - `inference = t_infer - t_pickup`
    - `filter = t_filter - t_infer`
    - `inject = t_inject - t_filter`, or 0 if there was no injection
    - `total = (t_inject or t_filter) - t_capture`
  - **`<prefix>_summary.json`** keys:
    - `scenario`, `duration_s`, `frames_processed`, `fps_avg`
    - `stage_ms`: for each of capture, inference, filter, inject, total, the `{p50, p95, max}`
      computed with `numpy.percentile`
    - `cpu_percent_machine_avg` and `cpu_percent_one_core_avg`: `p = psutil.Process()`, prime
      `p.cpu_percent(None)` at start, sample once per second; one-core = the raw value,
      machine = raw / `psutil.cpu_count(logical=True)`
    - `rss_mb_max`
    - `frames_with_hand_pct`
    - `dropout_runs`: counts of interior gaps (runs of 0-hand frames that have hand frames on
      both sides), keyed `"1"`, `"2"`, `"3"`, `"4+"`
    - `single_frame_drop_fraction` = runs of length 1 ÷ all runs (null if there are no runs)
    - `env`: Python version, `mediapipe.__version__`, `cv2.__version__`, camera `actual`, primary
      screen rect, DPI mode
  - **`<prefix>.jsonl`** (only with `--record`): a header line, then one frame line per processed
    frame, exactly per the contract. `presence` = `handedness_score` (the Hand Landmarker does
    not expose per-hand presence; say so in the header `notes`). Round coordinates to 5
    decimals. Include `timing_ms`.
  - At the end, print the summary JSON path and the key numbers.
- [x] T024 [US3] Create `spikes/feasibility/target_task.py` (depends on T020, T021, T019). It sends **no** OS input at all; do not import `winput.move_cursor_abs`.
  - **Window**: a fullscreen OpenCV window `"GesCRTL target task"`
    (`cv2.namedWindow(name, cv2.WND_PROP_FULLSCREEN)` plus
    `cv2.setWindowProperty(name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)`). The canvas
    is a black `numpy` array the size of `winput.primary_screen_rect()`. Call
    `winput.set_dpi_awareness()` first.
  - **Cursor**: a white dot computed with the same OneEuro2D + mapper. For relative mapping,
    start at the canvas center and keep an internal cursor.
  - **Pinch** (hysteresis): becomes True when `pinch_ratio < 0.25` and False when `> 0.35`.
  - **Trials** (`--trials 30`, `--seed 1`):
    - Target diameters cycle through 24, 48, 96 px.
    - Positions are uniformly random with a 100 px margin.
    - On a pinch start: if the dot is inside the target circle, record success with
      `time_ms` = time since the target appeared; otherwise count a miss for that trial.
  - Draw the target (green circle), the dot, the trial counter, and a help line:
    "Pinch on the green circle · Esc to quit".
  - Esc (`cv2.waitKey(1) & 0xFF == 27`) ends early.
  - **Outputs**:
    - `out/<ts>_target_<mapping>.csv` with columns `trial, size_px, time_ms, misses`.
    - `out/<ts>_target_<mapping>_summary.json` with, per size: `n`, `mean_time_ms`,
      `median_time_ms`, `miss_rate` (= misses ÷ (misses + successes)); plus overall values.
  - **CLI**: `--mapping`, `--trials`, `--seed`, `--region`, `--gain`, smoothing args, `--camera`,
    `--model`.
- [x] T025 [P] [US3] Create optional `spikes/feasibility/overlay_check.py` (ADR 0003 evidence). It requires `pip install PySide6`, which is not in requirements.txt; note this in the module docstring.
  - Show a small semi-transparent label "Click-through test — Ctrl+C in terminal to quit" in the
    top-right corner.
  - Window flags: `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool |
    Qt.WindowTransparentForInput`. Attributes: `Qt.WA_TranslucentBackground` and
    `Qt.WA_ShowWithoutActivating`.
  - No camera and no input injection.

### Human measurement runs (prepare commands; do not fabricate results)

- [x] T026 [US3] HUMAN: Follow `spikes/feasibility/README.md` setup. Run each module's self-check: `python one_euro.py`, `python mapping.py`, `python winput.py`, `python hotkey.py`, `python tracking.py`. Then run `python spike.py` for 1 minute and confirm the cursor follows the palm and `Ctrl+Alt+Esc` stops it. Record pass/fail notes in `spikes/feasibility/out/smoke-notes.txt`.
- [x] T027 [US3] HUMAN: Run the four measurement sessions from `specs/001-product-foundation/quickstart.md` A3, plus `python measure.py --duration 60 --scenario dim-light --record` in dim light, and `python measure.py --duration 60 --scenario two-people --record` with a second person's hand in view. The files land in `spikes/feasibility/out/`.
- [x] T028 [US3] SKIPPED by owner 2026-10-10 (risk accepted, see feasibility report section 4). HUMAN: Do the slow-motion video check from quickstart.md A4 (10 flicks). Write the per-flick frame counts, the phone FPS, and the computed delays to `spikes/feasibility/out/video-delay.csv` with columns `flick, frames, phone_fps, delay_ms`.
- [x] T029 [US3] HUMAN: Run `python target_task.py --mapping absolute --trials 30` and `python target_task.py --mapping relative --trials 30` (quickstart A5). Optionally repeat the absolute run with `--min-cutoff 0.5` and `--beta 0.02`, and note which feels better in `spikes/feasibility/out/smoke-notes.txt`.
- [ ] T030 [P] [US3] HUMAN (optional): Do the packaging trial (quickstart A6) and the overlay check (`python overlay_check.py`, quickstart A7). Record build success, `dist/gescrtl-spike` folder size (MB), cold-start seconds, and whether clicks pass through the overlay in `spikes/feasibility/out/smoke-notes.txt`.

### Report and decision records

- [x] T031 [US3] Create `docs/measurements/feasibility-report.md` with the 6 required sections from `specs/001-product-foundation/contracts/measurement-report.md`.
  - Fill every number ONLY from `spikes/feasibility/out/*_summary.json`, `video-delay.csv`, and
    `smoke-notes.txt`. The p95 delay is from `video-delay.csv` (`numpy.percentile(delay_ms, 95)`).
  - Section 5 **"Derived values"**:
    - Idle CPU budget = the `_nohand_rate10` session's `cpu_percent_machine_avg`, rounded UP to
      the nearest 5% (research R13).
    - Loss-confirmation window = the smallest N such that runs of length < N make up ≥ 95% of
      all dropout runs (research R9). If there are fewer than 20 runs, keep 3 and say so.
    - One Euro parameters = the values the human preferred in T029 (default 1.0 / 0.007).
  - Any missed target goes in section 4 with the decision cell set to "Awaiting owner".
  - Do not invent missing data; write `TBD (missing: <file>)`.
- [x] T032 [P] [US3] Create `docs/adr/0001-hand-tracking.md` using `specs/001-product-foundation/contracts/adr-template.md`. Copy options and rationale from research.md R1. Evidence = tracking FPS, inference p95, and dim-light dropout from the report. Status `Accepted` if FPS ≥ 25 in normal light, otherwise `Proposed` with the gap stated.
- [x] T033 [P] [US3] Create `docs/adr/0002-input-injection.md` from the template. Copy from research.md R2, including the UIPI and secure-desktop limits under Consequences. Evidence = inject p95 from the report plus the `winput.py` self-check result from smoke notes.
- [x] T034 [P] [US3] Create `docs/adr/0003-hud-overlay.md` from the template. Copy from research.md R3. Evidence = the overlay check result from T030. If T030 was skipped, set Status `Proposed` and Evidence "Comparison only (research R3); overlay check pending in Phase 1".
- [x] T035 [P] [US3] Create `docs/adr/0004-packaging.md` from the template. Copy from research.md R4. Evidence = build result, size, and cold start from T030, or `Proposed` with "pending" if T030 was skipped.
- [x] T036 [P] [US3] Create `docs/adr/0005-pointer-mapping.md` from the template. Copy from research.md R5, R7, and R8.
  - Evidence = a target-task table (per size: mean time and miss rate, absolute vs relative)
    from the T029 summaries.
  - Decision: choose the mapping with the lower overall miss rate. If the miss rates are within
    5 percentage points, choose the one with the lower mean time. If they are still tied, choose
    absolute (simpler, no clutch needed).
  - Record the final region, gain, One Euro parameters, and anchor point.

**Checkpoint**: US3 is complete. Feasibility is proven (or the gaps are documented) and all five
ADRs exist.

---

## Phase 6: User Story 4 - Product definition, release boundaries, known limits (Priority: P4)

**Goal**: An honest, short product definition and a list of known limitations (FR-016, FR-017).

**Independent Test**: A newcomer reads both files and answers 5/5 questions about users, scope,
exclusions, and limits within 10 minutes (SC-006).

- [x] T037 [P] [US4] Create `docs/product/product-definition.md` with these sections, in order:
  - **Vision**: copy the quote from Plan.md §1.
  - **Primary users**: from spec.md Assumptions — everyday Windows laptop/desktop users with a
    webcam, with users with motor impairments as an important secondary audience (served through
    configurability and Phase 9).
  - **Key use cases**: exactly 5 bullets. Browse the web and click links; open, move, and arrange
    files and windows; scroll documents; pause control quickly to talk or type; present slides
    (later phase).
  - **First release includes**: Plan.md §6 items 1–5.
  - **First release excludes**: high-speed typing; two-handed air typing (Phase 5b); custom
    gestures (Phase 8); multi-monitor (Phase 9); macOS/Linux; controlling admin windows and
    secure screens.
  - **Success criteria**: copy the Plan.md §6 numbered list and target table.
  - **See also**: links to known-limitations.md, glossary.md, and interaction-model.md.
  - Acceptance: max ~1 page. Every claim traces to Plan.md or spec.md.
- [x] T038 [P] [US4] Create `docs/product/known-limitations.md` (FR-017). Use one table with columns Situation | What the user sees | Why | Workaround. The rows, in this order:
  1. Administrator (elevated) windows such as Task Manager ignore GesCRTL input (Windows UIPI).
     Workaround: run GesCRTL as administrator (not recommended) or use the keyboard.
  2. Sign-in screen, lock screen, Ctrl+Alt+Del, and UAC prompts cannot be controlled (secure
     desktop). Workaround: physical input.
  3. Camera in use by Teams/Zoom/Camera app: GesCRTL shows "Camera unavailable". Workaround:
     close the other app; camera sharing is a future item.
  4. Poor lighting or a strong backlight lowers tracking reliability; GesCRTL stops acting rather
     than guessing.
  5. Hand farther than about 1 m from a laptop webcam may not be tracked (presenting distance is
     validated in Phase 4).
  6. Only one hand controls at a time; other people's hands are ignored.
  7. First release supports the primary monitor only.
  8. Typing by gesture will be slower than a physical keyboard.

  Add a source note citing research.md R2 and the constitution, Principle VII.

**Checkpoint**: All four user stories are complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Replace provisional values, sync Plan.md, and run the final consistency review.

- [x] T039 Update provisional values from `docs/measurements/feasibility-report.md` section 5 "Derived values".
  - Edit the loss-confirmation window, One Euro parameters, and Paused processing rate in
    `docs/interaction/safety-policy.md`, `docs/interaction/interaction-model.md` (Tracking loss
    section), and `docs/interaction/gesture-vocabulary.md` (Active region, if ADR 0005 changed
    the region).
  - Remove the word *(provisional)* only from values that now have measured evidence.
- [x] T040 Edit `Plan.md` §6 table, row "CPU usage when no hand is present": replace "Reduced via lower processing rate (budget set in Phase 0)" with the measured budget from the report (for example "≤ 10% of total CPU at 10 FPS processing"). If the report missed the 80 ms or 25 FPS targets and the owner accepted a revised target, update that row too and add "(revised in Phase 0, see docs/measurements/feasibility-report.md)".
- [x] T041 Create `docs/phase0-review.md`.
  - Copy the "Part B: Document validation" table from
    `specs/001-product-foundation/quickstart.md`, adding columns **Result (Pass/Fail)** and
    **Evidence**.
  - Fill every row by checking the actual files. For SC-007, search all of `docs/`, `Plan.md`,
    and `.specify/memory/constitution.md` for contradictions about state names, startup state,
    emergency stop target, gesture count, hotkeys, and targets. List anything found and fix it.
  - Add a **"Requirement coverage"** table mapping FR-001…FR-020 to the file(s) that satisfy each.
  - Rows needing a person (SC-006, owner sign-off) are marked "Pending HUMAN".
- [ ] T042 HUMAN: Newcomer test (SC-006). Give someone unfamiliar with the project `docs/product/product-definition.md` and `docs/product/known-limitations.md` for up to 10 minutes. Then ask:
  1. Who is GesCRTL for?
  2. What can the first release do?
  3. Name two things it will not do.
  4. Can it control the Windows lock screen?
  5. What happens if Zoom is using the camera?

  Record the answers and the score in `docs/phase0-review.md`. Pass = 5/5.
- [ ] T043 HUMAN: Owner sign-off. Review `docs/phase0-review.md` and decide every "Awaiting owner" item in `docs/measurements/feasibility-report.md` section 4. Then set `**Status**: Complete` in `specs/001-product-foundation/spec.md` and add the sign-off date to `docs/phase0-review.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup. Blocks all stories (the glossary is used everywhere).
- **US1 (Phase 3)**, **US2 (Phase 4)**, **US4 (Phase 6)**: docs only. They can start after Phase 2
  and run in parallel. T016 (US2) reads T010's matrix, so do US1 first if working alone.
- **US3 (Phase 5)**: can start after Phase 2. The code tasks (T017–T025) do not depend on the
  docs. T026–T030 need the code. T031 needs T026–T029. The ADRs T032–T036 need T031.
- **Polish (Phase 7)**: after all stories. T039 and T040 need T031. T041 needs everything. T042
  and T043 come last.

### Within US3 (code order)

```
T017 winput ─┐
T018 hotkey ─┤
T019 one_euro┼─► T020 tracking ─► T022 spike ─► T023 measure
T021 mapping ┘                └────────────► T024 target_task
T025 overlay_check (independent)
```

### Parallel Opportunities

- Setup: T002, T003, T004.
- Foundational: T006, T007, T008 (after T005, or in parallel with it).
- US2: T013, T014, T015.
- US3 code: T017, T018, T019, T021, T025. The ADRs T032–T036 can all run in parallel once T031
  is done.
- US4: T037, T038.
- US1, US2, and US4 can be written in parallel with US3's code tasks.

---

## Parallel Example: User Story 3

```text
# After Phase 2, launch the independent spike modules together:
Task: "T017 Create spikes/feasibility/winput.py"
Task: "T018 Create spikes/feasibility/hotkey.py"
Task: "T019 Create spikes/feasibility/one_euro.py"
Task: "T021 Create spikes/feasibility/mapping.py"

# After T031, write all decision records together:
Task: "T032 docs/adr/0001-hand-tracking.md"
Task: "T033 docs/adr/0002-input-injection.md"
Task: "T034 docs/adr/0003-hud-overlay.md"
Task: "T035 docs/adr/0004-packaging.md"
Task: "T036 docs/adr/0005-pointer-mapping.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational.
2. Phase 3 (US1): the interaction model.
3. **Stop and validate**: a reviewer checks the matrix for completeness (SC-001).

### Incremental Delivery

1. US1 → interaction model reviewed.
2. US2 → vocabulary and safety policy reviewed. The Phase 1 spec could already be drafted here.
3. US3 → spike plus measurements plus ADRs. This is the biggest risk retired.
4. US4 → product definition and limitations.
5. Polish → measured values replace provisional ones, Plan.md is synced, review and sign-off.

### Working with a cheaper model

- Give the model **one task at a time**, with the task text plus the files it names.
- After each code task, run that module's `__main__` self-check before moving on.
- Never let the model do `HUMAN:` tasks or fill in numbers without the `out/` files.

---

## Notes

- [P] = different files, no dependency on unfinished tasks.
- Commit after each task or logical group.
- If a task's instructions conflict with the constitution, the constitution wins. Stop and ask
  the owner.
