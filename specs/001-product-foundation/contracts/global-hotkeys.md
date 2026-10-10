# Contract: Global Keyboard Shortcuts (defaults)

These are the non-gesture control paths required by FR-005 and FR-005a. All of them are
configurable in later phases. These are the defaults the Phase 0 documents and the spike use.

| Action | Default shortcut | Effect (see data-model transition table) |
|---|---|---|
| Emergency stop | `Ctrl + Alt + Esc` | Any state except Inactive → Paused; ReleaseAll |
| Pause / Resume toggle | `Ctrl + Alt + G` | Active/TrackingLost → Paused; Paused → Active |
| Turn off / Turn on toggle | `Ctrl + Alt + Shift + G` | Any → Inactive (camera released); Inactive → Paused |

Tray menu items mirror these: **Resume / Pause**, **Turn off / Turn on**, **Exit**.

Rules:
- Shortcuts work whatever application has focus (registered globally).
- They must not collide with Windows-reserved combinations (`Ctrl+Alt+Del`, `Ctrl+Shift+Esc`,
  `Win+L`). The spike verifies registration succeeds and reports collisions.
- The spike implements at least **Emergency stop**, which stops cursor control and exits.
