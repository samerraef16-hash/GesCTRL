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
| More than one monitor | One hand movement covers all monitors, so a monitor gets a smaller share of the range, and with side-by-side monitors the cursor moves more pixels sideways than up | The movement range keeps the camera's shape and is stretched over the whole desktop | Run Calibrate, or raise the movement range in Settings |
| Overlays on several monitors | Menus, the keyboard and the laser appear on one monitor | They are drawn on the monitor chosen in Settings, not on the one the cursor is on | Choose the monitor in Settings > Displays |
| Typing by gesture | Slower than a physical keyboard (the measured speed is in the validation report) | Gesture typing is limited by selection and confirmation time | Use the physical keyboard for long text |
| Keyboard layout | The on-screen keyboard is a US layout | Keys show US characters | Characters are sent as typed, so any input language works; shortcuts use the active layout |
| Typing into elevated windows | Nothing is typed | Windows blocks input from a normal program (UIPI) | Use the physical keyboard |
| Two-handed key pressing | A second person's hand near yours could be taken for your other hand | The check is a heuristic: opposite hand, close, confident, stable | Turn off two-handed pressing in Settings, or keep others out of view |
| Custom gestures | Off until turned on; a shape must be a "relaxed" built-in pose; movements are ignored while a built-in gesture is in progress | They are matched against your own recordings and must never override a built-in gesture | Record again with clearer takes, or delete the gesture |
| Custom gesture accuracy | Shapes and movements are recognized only as reliably as the measured results in the validation report | Single webcam, no depth, and personal variation | See the report; a kind that missed its target is disabled |
| Dwell click | A cursor held still clicks | This is the point of the option; it is off by default | Turn it off in Settings |
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
