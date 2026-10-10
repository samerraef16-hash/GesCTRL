# Feasibility Spike (Phase 0)

## ⚠️ Disposable

This code is a throwaway feasibility spike (spec FR-012). It must never become product code.
Phase 1 starts fresh in `src/`.

## Setup

```powershell
cd spikes\feasibility
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip freeze > requirements.lock.txt
Invoke-WebRequest -Uri https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task -OutFile models\hand_landmarker.task
```

`py -3.11` also works if 3.12 has no MediaPipe wheel.

## Files

- `winput.py` — Win32 cursor movement (`SendInput`), DPI awareness, screen rectangles. The only Win32 cursor code.
- `hotkey.py` — global emergency-stop hotkey (`Ctrl+Alt+Esc`) on its own thread.
- `one_euro.py` — One Euro smoothing filter.
- `tracking.py` — latest-frame camera grabber, MediaPipe hand tracker, hand geometry, primary-hand selector.
- `mapping.py` — absolute-region and relative+clutch cursor mappers.
- `spike.py` — camera → tracking → smoothing → mapping → cursor.
- `measure.py` — timed measurement session writing CSV, summary JSON, and optional landmark JSONL.
- `target_task.py` — in-window target-clicking task comparing mapping models (sends no OS input).
- `overlay_check.py` — optional click-through window check (needs `pip install PySide6`).

## Safety

`Ctrl+Alt+Esc` stops the spike. The spike only moves the cursor and never clicks.

## Privacy

No images are saved and there is no network use after the model download.
