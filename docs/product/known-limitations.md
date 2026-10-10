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
