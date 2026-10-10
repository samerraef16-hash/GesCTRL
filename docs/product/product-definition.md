# GesCRTL Product Definition

> Source: Plan.md §1, §5, §6; spec.md Assumptions (specs/001-product-foundation).

## Vision

> Let users interact with their computer naturally through their hands, using a webcam as the primary input device.

## Primary users

Everyday Windows laptop and desktop users with a built-in or standard USB webcam. People with
motor impairments are an important secondary audience; they are served through configurability
and the Phase 9 accessibility work rather than a separate first-release design.

## Key use cases

- Browse the web and click links.
- Open, move, and arrange files and windows.
- Scroll documents.
- Pause control quickly to talk or type.
- Present slides (later phase).

## First release includes

A new user can:

1. Start GesCRTL and understand whether gesture control is active.
2. Move the cursor, click, drag, and scroll with the webcam.
3. Pause control quickly and resume intentionally.
4. Understand when the camera or hand tracking is unavailable.
5. Complete a short everyday desktop demonstration without unexpected actions.

## First release excludes

- High-speed typing.
- Two-handed air typing (Phase 5b, research).
- Custom gestures (Phase 8).
- Multiple monitors (Phase 9).
- macOS and Linux.
- Controlling administrator windows and secure system screens (see `known-limitations.md`).

## Success criteria

The first milestone is successful when a new user can:

1. Start GesCRTL and understand whether gesture control is active.
2. Move the cursor, click, drag, and scroll with the webcam.
3. Pause control quickly and resume intentionally.
4. Understand when the camera or hand tracking is unavailable.
5. Complete a short everyday desktop demonstration without unexpected actions.

Initial measurable targets:

| Metric | Initial target |
|---|---|
| End-to-end latency (camera frame → OS input) | ≤ 80 ms at p95 |
| Hand-tracking frame rate | ≥ 25 FPS |
| Unintended clicks during 10 minutes of visible but non-controlling hands | 0 |
| CPU usage when no hand is present | Reduced via lower processing rate (budget set in Phase 0) |

## See also

- [known-limitations.md](./known-limitations.md)
- [glossary.md](./glossary.md)
- [interaction-model.md](../interaction/interaction-model.md)
