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

Four items in a row: Pointer, Keyboard, Presentation, Media/System (all four can be chosen). The current mode is
highlighted and the one being pointed at is outlined. Footer text: "Pinch to choose · Fist to
cancel". The menu closes automatically after 5 s with no selection.

## Hints per mode

- **Pointer**: "Pinch: click · hold: drag", "Thumb out, tilt: scroll", "Three fingers: modes · call me: volume/brightness", "Flat hand 1.5 s: pause".
- **Presentation**: "Index finger: pointer", "Open-hand swipe: next / previous", "Thumb up 1 s: start show · down: end", "Flat hand 1.5 s: pause".
- **Media/System**: "Point + pinch: run action", "Hold pinch on ±: keep changing", "Fist: cancel", "Flat hand 1.5 s: pause".
- **Keyboard**: "Point at a key, pinch to type", "Your other hand's pinch types too", "Three fingers: modes", "Flat hand 1.5 s: pause".
- **Hold (flat hand)**: "Fist: resume", "Flat hand 1.5 s: pause", shown when the hold starts.

## Keyboard layout

Six rows of keys across 96 % of the screen width and 44.5 % of its height, at the bottom (or the
top, with the Move key or the setting): shortcuts (Copy, Paste, Cut, Undo, Redo, All, Alt+Tab, Win,
Esc, Move), digits, letters, punctuation, and a bottom row of Shift, Ctrl, Alt, Win, Space, arrows
and Enter. Every key is at least 48 px at 1280 × 720. The key pointed at is outlined, the key just
pressed flashes green, a one-shot modifier is outlined in blue and a locked one is filled, and a ring
fills while dwelling. A strip above (or below) shows the last characters sent. The window is
click-through and never takes focus.

## Setup guide

A dimmed screen with a centred box: what to do now, a progress bar, and during the reach step a
ring at the screen corner to point at. The pill reads "Setup". A recorded gesture that fires is
named on the pill ("name → action").

## Level panel layout

Two tall sliders side by side (Volume, Brightness), centred, each 10 % of the screen wide and
45 % high, filled to the level the system reports with the percentage inside. The slider pointed
at is outlined. "Unavailable" replaces a level that cannot be controlled. A + target above and a −
target below each slider (10 % × 10 %) let dwell users step the level. Footer: "Pinch and move, or
point at + / −".

## Media grid layout

Ten targets in two rows of five, each 15 % × 14 % of the screen: play/pause, previous, next,
volume −, volume +, mute, brightness −, brightness +, screenshot, switch app. Each has a label
and a simple glyph. The target pointed at is outlined; a target waiting for its second pinch is
filled and says "Pinch again to confirm". Footer: "Point and pinch · Fist to cancel".

## Presentation laser

A red dot with a soft glow at the pointed position, shown only while the index finger is raised
alone. It is an overlay on the screen; the real cursor does not move.
