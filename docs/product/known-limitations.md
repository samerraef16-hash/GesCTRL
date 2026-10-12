# GesCRTL Known Limitations

> Source: research.md R2; constitution Principle VII; spec.md FR-017.

| Situation | What the user sees | Why | Workaround |
|---|---|---|---|
| Administrator (elevated) windows such as Task Manager | The cursor moves but the window ignores input | Windows blocks input from a normal program into elevated windows (UIPI) | Run GesCRTL as administrator (not recommended) or use the physical keyboard |
| Sign-in screen, lock screen, Ctrl+Alt+Del, UAC prompts | GesCRTL cannot control them | These run on the secure desktop, which no normal program can reach | Use physical input |
| Camera in use by Teams, Zoom, or the Camera app | "Camera unavailable" | Another application holds the camera exclusively | Close the other app; camera sharing is a future item |
| Poor lighting or a strong backlight | Tracking becomes unreliable; GesCRTL stops acting rather than guessing | The hand cannot be read confidently | Improve the lighting or face the light. Measured in Phase 0: in a dim room the camera itself dropped to about 10 FPS, so the cursor updates less often. |
| Hand farther than about 1 m from a laptop webcam | The hand may not be tracked | Detection range drops with distance (presenting distance is validated in Phase 4) | Move closer |
| Several hands or people in view | Only one hand controls | GesCRTL follows a single primary hand and ignores the others | Keep other hands out of the view |
| More than one monitor | Control covers the primary monitor only | Multi-monitor mapping arrives in Phase 9 | Use the primary monitor |
| Typing by gesture | Slower than a physical keyboard | Gesture typing is limited by selection and confirmation time | Use the physical keyboard for long text |
| Keyboard mode | Listed in the menu as "Later" | Gesture typing arrives in its own spec | Use the physical keyboard |
| Brightness | "Unavailable" in the level panel | Brightness uses the built-in display (WMI); desktop and many external monitors do not support it | Use the monitor's own buttons |
| Slides and media keys | Keys go to whichever window has focus | GesCRTL never changes focus | Click into the presentation or player first |
| Starting and ending a show | "Start/end not supported in this app" | Only PowerPoint and Google Slides (Edge or Chrome) have a known shortcut; the Edge PDF viewer gets slide changes only | Start the show by hand |
| Swipes in dim light | May be missed | The camera drops to about 10 FPS | Add light, or swipe slower and wider |
| Screenshot action | A file appears in Pictures\Screenshots | It sends Win+PrtSc, an OS screen capture (never a camera image) | None needed |
| Scrolling | Vertical only; some apps scroll in coarse steps | Only plain wheel notches are sent, and apps that expect high-resolution wheel deltas may jump | Use the app's own scroll bar for fine positioning |
| Camera unplugged, taken by another app, or asleep | The indicator reads "Camera unavailable" and buttons are released | No frame arrived for 1 s. The app retries every 2 s on its own and returns to tracking when the camera is back | Close the other app or replug the camera; nothing needs restarting |
| Flat-hand clutch and pause | Needs an upright, fully straight hand with the thumb tucked; a tilted hand reads as pointing | Deliberately strict so that a thumb on its way to a pinch never clutches | Hold the hand up straight, palm toward the camera |
| Scroll gesture seen from the side | The thumb-out fist may take a moment to be recognized | The curled fingers look different side-on in a 2D image | Turn the fist a little toward the camera; the preview readout shows what is seen |
| Presentation Mode tuning | Swipe, laser and show start/end use the planned defaults | Presentation Mode was not recorded or tuned: the pointer in PowerPoint and Google Slides covers the same need | Use Pointer Mode for slides; the settings file can still change the defaults |
