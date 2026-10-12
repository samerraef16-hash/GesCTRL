# GesCRTL Feedback Indicator (HUD)

> Source: spec.md FR-011; `specs/001-product-foundation/contracts/hud-feedback.md`; constitution Principle III.

## Window behavior (mandatory)

- Always on top, never takes keyboard focus, never intercepts mouse clicks (click-through).
- Not shown in the taskbar or the Alt+Tab list.
- Default position: top-right corner of the primary monitor, user-movable later; it stays clear
  of the cursor's active area.
- Compact: one pill-shaped element. Expanded hints appear for at most 3 s after a change, then
  collapse.

## Content per state

| State / condition | Pill text | Color cue | Extra |
|---|---|---|---|
| Paused | "Paused" | Grey | First launch: hint "Show open palm to start" |
| Paused + camera unavailable | "Paused · Camera unavailable" | Grey + warning icon | n/a |
| Active | "\<Mode\>" (e.g., "Pointer") | Green | Hints for the current mode on entry (≤ 4 items) |
| Active · Clutched | "\<Mode\> · Hold" | Green, dimmed | n/a |
| Active · Mode menu | Menu with all 4 modes, current one highlighted | Blue | "Pinch to choose · Fist to cancel" |
| Tracking Lost (hand) | "Hand not visible" | Amber | Shown within 1 s of loss |
| Tracking Lost (camera) | "Camera unavailable" | Red | Names the cause if known ("in use by another app") |
| Emergency stop just triggered | "Stopped" | Red flash, then Paused grey | n/a |
| Inactive | HUD hidden | n/a | Tray icon shows "Off" state |

## Rules

- Color is never the only cue: text is always present (accessibility).
- State changes appear on the HUD within 200 ms of the transition. Camera or hand unavailability
  appears within 1 s (Constitution III).
- The HUD never shows camera imagery by default. A camera preview, if added later, is opt-in.

## Mode menu layout

Four items in a row: Pointer, Keyboard, Presentation, Media/System. The current mode is
highlighted and the one being pointed at is outlined. Footer text: "Pinch to choose · Fist to
cancel". The menu closes automatically after 5 s with no selection.

## Hints per mode

- **Pointer**: "Pinch: click · hold: drag", "Thumb out, tilt: scroll", "Three fingers: modes · call me: volume/brightness", "Flat hand 1.5 s: pause".
- **Presentation**: "Index finger: pointer", "Open-hand swipe: next / previous", "Thumb up 1 s: start show · down: end", "Flat hand 1.5 s: pause".
- **Media/System**: "Point + pinch: run action", "Hold pinch on ±: keep changing", "Fist: cancel", "Flat hand 1.5 s: pause".
- **Keyboard**: not available yet.

## Level panel layout

Two tall sliders side by side (Volume, Brightness), centred, each 10 % of the screen wide and
45 % high, filled to the level the system reports with the percentage inside. The slider pointed
at is outlined. "Unavailable" replaces a level that cannot be controlled. Footer: "Pinch and move ·
Fist to close".

## Media grid layout

Ten targets in two rows of five, each 15 % × 14 % of the screen: play/pause, previous, next,
volume −, volume +, mute, brightness −, brightness +, screenshot, switch app. Each has a label
and a simple glyph. The target pointed at is outlined; a target waiting for its second pinch is
filled and says "Pinch again to confirm". Footer: "Point and pinch · Fist to cancel".

## Presentation laser

A red dot with a soft glow at the pointed position, shown only while the index finger is raised
alone. It is an overlay on the screen; the real cursor does not move.
