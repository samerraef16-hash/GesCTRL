# Quickstart: Validating Phase 0

This guide proves Phase 0 is complete. Part A validates the feasibility spike, and Part B validates
the documents. The commands assume the spike is laid out as described in [plan.md](./plan.md).

## Prerequisites
- Windows 10/11 laptop with a built-in webcam (the reference hardware, research R12).
- Python 3.11 or 3.12 (the version with MediaPipe Windows wheels), and `git`.
- A phone that records slow-motion video at ≥ 240 FPS (for the end-to-end delay check).
- Normal indoor lighting, with your hand 40–70 cm from the camera.
- Close other apps that use the camera (Teams, Zoom, Camera app).

## Part A: Feasibility spike

### A1. Setup
```powershell
cd spikes\feasibility
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Download hand_landmarker.task into spikes\feasibility\models\ (see spike README)
```

### A2. Run cursor control (absolute mapping)
```powershell
python spike.py --mapping absolute
```
Expected:
- The cursor follows your palm smoothly within the active region.
- `Ctrl+Alt+Esc` stops control immediately and releases the camera (see
  [global-hotkeys](./contracts/global-hotkeys.md)).
- Closing the script also stops control.
- No OS clicks are ever sent.

### A3. Measurement session
```powershell
python measure.py --duration 120 --scenario pointing --record     # hand moving
python measure.py --duration 60  --scenario idle-hand --record    # hand still in view
python measure.py --duration 60  --no-hand                        # empty frame (CPU budget)
python measure.py --duration 60  --paused-rate 10 --no-hand       # reduced rate (idle budget)
```
Expected outputs in `out\`:
- Per-frame timing CSV, a summary JSON (p50/p95 per stage, FPS, CPU averages, dropout
  run-lengths), and a `.jsonl` recording that conforms to
  [landmark-recording](./contracts/landmark-recording.md).
- Spot-check: open the `.jsonl`; line 1 is a header and every frame has 0–2 hands with 21
  landmarks each. **No image files exist anywhere in `out\`.**

### A4. End-to-end delay (slow-motion video)
1. Make the cursor easy to see on video: Windows Settings → Accessibility → Mouse pointer and
   touch → set Size to 5 or more. Then run `python spike.py --mapping absolute`.
2. Film your hand and the screen together at ≥ 240 FPS. Do 10 quick sideways hand flicks.
3. For each flick, count frames from hand-motion onset to cursor-motion onset; delay =
   frames ÷ fps.
4. Expected: p95 ≤ 80 ms. If it is higher, record the gap and a mitigation in the report.

### A5. Pointer mapping comparison
```powershell
python target_task.py --mapping absolute --trials 30
python target_task.py --mapping relative --trials 30
```
Expected: A summary of time-to-target and miss rate per target size, for each model. This is the
evidence for ADR 0005. Pinches are detected inside the task window only.

### A6. Optional: packaging trial (ADR 0004)
```powershell
pip install pyinstaller
pyinstaller --onedir --name gescrtl-spike spike.py --add-data "models;models"
```
Expected: The build succeeds. Record the folder size and cold-start time in ADR 0004.

### A7. Optional: click-through overlay check (ADR 0003)
Show a minimal always-on-top, click-through window. Expected: clicking "through" it reaches the
app underneath, and focus never moves to the overlay.

## Part B: Document validation

Check each item and record the result in the phase review:

| Check | Pass condition | Spec ref |
|---|---|---|
| Transition table complete | Every state × event pair in `docs/interaction/interaction-model.md` has a result (or an explicit no-op) and feedback, matching [data-model.md](./data-model.md) | SC-001 |
| No gesture conflicts | No hand form has two meanings in the same scope and state | SC-002 |
| Gesture budget | ≤ 8 hand forms; each usable with either hand | SC-003 |
| Performance | Report shows delay and FPS pass, or an owner-accepted mitigation | SC-004 |
| ADRs | 0001–0005 exist, each with ≥ 1 evidence item | SC-005 |
| Product definition | A newcomer answers 5/5 scope questions within 10 minutes | SC-006 |
| Consistency | Zero contradictions among `docs/`, `Plan.md`, and the constitution; §6 idle CPU budget updated | SC-007, FR-015, FR-019 |
| Phase 1 readiness | A draft of the Phase 1 spec can be written with ≤ 3 open questions | SC-008 |
| Privacy | No images stored; no network use observed (e.g., firewall or Resource Monitor) | FR-020 |

Phase 0 is complete when Parts A and B pass and the owner signs off on any gaps.
