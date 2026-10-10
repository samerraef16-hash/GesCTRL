# Contract: Landmark Recording Format (JSONL)

Produced by the feasibility spike (`spikes/feasibility/measure.py --record`). Consumed by Phase 1
replay tests (Constitution IV). **No images, ever** (FR-020).

## File
- Extension `.jsonl`, UTF-8, one JSON object per line.
- Line 1 is a **header** object. Every later line is a **frame** object.

## Header (line 1)
```json
{
  "type": "header",
  "format_version": 1,
  "recorded_at": "2026-10-10T14:03:00Z",
  "tracker": {"name": "mediapipe-hand-landmarker", "version": "<x.y.z>", "running_mode": "VIDEO"},
  "camera": {"width": 640, "height": 480, "fps_requested": 30},
  "mirrored": true,
  "scenario": "idle-hand | pointing | pinch-clicks | typing-nearby | two-people | dim-light | free",
  "notes": "free text"
}
```

## Frame (lines 2…N)
```json
{
  "type": "frame",
  "t_ns": 123456789000,
  "hands": [
    {
      "handedness": "Left|Right",
      "handedness_score": 0.97,
      "presence": 0.99,
      "landmarks": [[x, y, z], "... 21 entries ..."],
      "world_landmarks": [[x, y, z], "... 21 entries (optional) ..."]
    }
  ],
  "timing_ms": {"capture": 0.0, "inference": 0.0, "filter": 0.0, "inject": 0.0}
}
```

## Rules
- `t_ns` is a monotonic timestamp (`perf_counter_ns`) relative to an arbitrary origin, strictly
  increasing.
- `landmarks` holds normalized image coordinates (x, y in [0, 1] after mirroring; z is relative
  depth), in MediaPipe landmark index order 0–20.
- `hands` may be empty (no hand detected). This must be recorded so loss behavior can be replayed.
- `timing_ms` is optional in replay; it is required in measurement sessions.
- Consumers must ignore unknown fields. Breaking changes increment `format_version`.
