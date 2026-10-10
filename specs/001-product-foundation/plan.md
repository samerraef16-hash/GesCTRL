# Implementation Plan: Product Foundation and Interaction Model (Phase 0)

**Branch**: `001-product-foundation` | **Date**: 2026-10-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-product-foundation/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Phase 0 produces GesCRTL's foundation documents and a throwaway feasibility prototype:

- **Documents.** Product definition, known limitations, glossary, interaction model (states,
  modes, transitions), first-release gesture vocabulary, accidental-action (safety) policy,
  HUD/feedback concept, and five decision records (ADRs).
- **Feasibility prototype.** It tracks one hand from the laptop webcam and moves the system
  cursor. Measurements from it validate the `Plan.md` §6 targets: ≤ 80 ms p95 hand-to-cursor
  delay and ≥ 25 FPS, and they set the idle CPU budget. The prototype also gives the evidence
  for the ADRs, especially pointer mapping (absolute active region vs. relative + clutch).

The technical approach comes from [research.md](./research.md):

- MediaPipe Hand Landmarker (Tasks API) for tracking, with OpenCV capture.
- Win32 `SendInput` via `ctypes` for cursor movement.
- One Euro filter smoothing.
- An internal timestamp pipeline plus a slow-motion video cross-check for latency.

The prototype sends **cursor movement only**. Its pinch/click detection for the target task is
handled inside its own window and never injects OS clicks.

## Technical Context

**Language/Version**: Python 3.11 or 3.12. Use whichever is newest with official MediaPipe Windows wheels at spike time; record the exact version in the measurement report.

**Primary Dependencies**:

- Prototype: `mediapipe` (Hand Landmarker task + `hand_landmarker.task` model), `opencv-python`, `numpy`, `psutil` (CPU/memory sampling), and stdlib `ctypes` for `SendInput` and DPI awareness.
- Optional packaging trial: `pyinstaller`.
- Documents: Markdown only.

**Storage**: Files only. Markdown documents under `docs/`. Landmark recordings as JSONL and measurement results as CSV/JSON under `spikes/feasibility/out/` (git-ignored). No images are ever stored (FR-020).

**Testing**: The prototype is throwaway, so it is exempt from replay tests (see Complexity Tracking). It does produce landmark recordings in the [landmark recording contract](./contracts/landmark-recording.md) so Phase 1 can start with real fixtures. Documents are validated with the review checklist in [quickstart.md](./quickstart.md).

**Target Platform**: Windows 10/11 on the project owner's laptop with its built-in webcam (reference hardware recorded in the report).

**Project Type**: Desktop application (foundation phase: documentation + throwaway spike).

**Performance Goals**:

- Hand-to-cursor delay ≤ 80 ms at p95.
- Tracking ≥ 25 FPS.
- Idle CPU budget to be set from measurements (FR-015).

**Constraints**:

- Camera frames stay in memory only, with no network use.
- The spike must release the camera and stop cursor control on its kill hotkey and on exit.
- The spike must be per-monitor DPI aware so cursor coordinates are correct at 125–150% scaling.

**Scale/Scope**:

- One user, one hand, one monitor.
- About 10 documents plus 5 ADRs.
- The spike is ≤ ~500 lines across a few scripts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How Phase 0 complies | Status |
|---|---|---|
| I. Safety First | The interaction model and safety policy codify hysteresis, confidence gating, cooldowns, release-on-loss, emergency stop (gesture + hotkey → Paused), and primary-hand lock. The spike injects cursor moves only, has a kill hotkey, and stops on exit. | ✅ |
| II. Reliability Before Breadth | Vocabulary is capped at 8 gestures (7 proposed). Keyboard, Presentation, and Media modes get only names and entry/exit rules. | ✅ |
| III. Predictable, Visible State | Full state × event transition table in [data-model.md](./data-model.md); HUD contract in [contracts/hud-feedback.md](./contracts/hud-feedback.md). | ✅ |
| IV. Deterministic, Testable Core | Applies to product code. The spike is disposable and exempt, but emits replayable landmark JSONL per contract. | ⚠️ Justified (see Complexity Tracking) |
| V. Measured Performance | The spike instruments per-stage timings, FPS, and CPU; the slow-motion video cross-check validates true end-to-end delay. | ✅ |
| VI. Privacy by Design | Landmarks and numbers only, no images and no network. Inactive fully releases the camera. | ✅ |
| VII. Modular, Platform-Isolated | Documented for Phase 1. The spike keeps Win32 calls in one module (`winput.py`) to rehearse the boundary. | ✅ |
| VIII. Simplicity, Ergonomics, Defaults | Active-region mapping, either-hand gestures, relaxed posture, and starting in Paused with no setup. | ✅ |
| Tech Standards: ADRs in `docs/adr/` | Five ADRs are required (FR-014) using [contracts/adr-template.md](./contracts/adr-template.md). | ✅ |

**Gate result (pre-research)**: PASS, with one justified deviation.
**Gate result (post-design)**: PASS. The design artifacts introduce no new violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-product-foundation/
├── plan.md              # This file
├── research.md          # Phase 0 output: decisions, rationale, alternatives
├── data-model.md        # Phase 1 output: entities + full state/transition model
├── quickstart.md        # Phase 1 output: how to run the spike, measure, and validate docs
├── contracts/
│   ├── landmark-recording.md    # JSONL recording format (spike → Phase 1 fixtures)
│   ├── global-hotkeys.md        # Keyboard shortcut contract
│   ├── hud-feedback.md          # What the indicator shows per state/mode
│   ├── measurement-report.md    # Required content of the feasibility report
│   └── adr-template.md          # Decision record format
├── checklists/requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks - NOT created here)
```

### Source Code (repository root)

```text
docs/
├── product/
│   ├── product-definition.md    # FR-016
│   ├── known-limitations.md     # FR-017
│   └── glossary.md              # FR-018
├── interaction/
│   ├── interaction-model.md     # FR-001..006 (states, modes, transitions)
│   ├── gesture-vocabulary.md    # FR-007, FR-008, FR-010
│   ├── safety-policy.md         # FR-009
│   └── feedback-hud.md          # FR-011
├── adr/
│   ├── 0001-hand-tracking.md
│   ├── 0002-input-injection.md
│   ├── 0003-hud-overlay.md
│   ├── 0004-packaging.md
│   └── 0005-pointer-mapping.md
└── measurements/
    └── feasibility-report.md    # FR-013, FR-015

spikes/
└── feasibility/                 # THROWAWAY (FR-012), never imported by product code
    ├── README.md                # "Disposable" notice + how to run
    ├── requirements.txt
    ├── models/                  # hand_landmarker.task (downloaded, git-ignored)
    ├── winput.py                # SendInput, DPI awareness, cursor pos (only Win32 code)
    ├── hotkey.py                # Global emergency-stop hotkey (RegisterHotKey thread)
    ├── tracking.py              # Latest-frame camera grabber, HandLandmarker wrapper, hand geometry
    ├── mapping.py               # Absolute-region and relative+clutch mappers
    ├── overlay_check.py         # Optional click-through window check (ADR 0003)
    ├── one_euro.py              # Smoothing filter
    ├── spike.py                 # Capture → track → filter → map → cursor; hotkey kill
    ├── target_task.py           # In-window target-acquisition test (no OS clicks)
    ├── measure.py               # Timed session → CSV/JSON metrics, idle vs hand
    └── out/                     # Recordings/metrics (git-ignored)
```

**Structure Decision**: The Phase 0 deliverables are documents under `docs/` (they last beyond Phase 0) plus a quarantined prototype under `spikes/feasibility/`. No `src/` package is created in Phase 0. The product layout from the constitution (`src/gescrtl/...`) starts in Phase 1, which keeps the prototype from becoming the product's foundation (FR-012).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Spike has no replay-based tests (Principle IV) | The spike is disposable code whose only output is measurements and recordings; FR-012 forbids building on it | Writing a tested core now would mean designing Phase 1 architecture before its spec exists. Instead the spike emits contract-conformant landmark JSONL so Phase 1 tests start with real data |
