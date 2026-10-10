# Contract: HUD / Feedback Indicator

The indicator satisfies FR-011 and Constitution III.

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
