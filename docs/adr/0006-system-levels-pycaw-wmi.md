# ADR 0006: System volume and brightness through pycaw and WMI

- **Status**: Accepted (read and no-change write checked on the author's laptop, 2026-10-12)
- **Date**: 2026-10-12
- **Related**: spec 003 FR-021 to FR-024, plan D8 and D10

## Context
The level panel and the Media grid change the system volume and the display brightness in small,
bounded steps. The HUD must show the real level, and a level that cannot be controlled must say so.

## Options Considered
1. **Volume media keys** (`VK_VOLUME_UP/DOWN`): no new dependency, but each press is a blind 2 % step
   and the real level cannot be read back.
2. **pycaw (Windows Core Audio endpoint) for volume, WMI for brightness**: exact levels, both can be read.
3. **A DDC/CI library for external monitors**: reaches more screens, but adds a dependency and is
   unreliable across monitors.
4. **PowerShell CIM calls**: needs no library, but spawns a process per step, far too slow for a drag.

## Decision
Option 2. Volume uses `IAudioEndpointVolume` through pycaw (`GetMasterVolumeLevelScalar` and
`SetMasterVolumeLevelScalar`, clamped 0..1). Brightness uses `WmiMonitorBrightness` (read) and
`WmiMonitorBrightnessMethods.WmiSetBrightness` (write) through comtypes. All COM calls run on one
daemon thread that coalesces the steps that arrive while it is busy, so a fast drag never queues
work. If the WMI class is missing or a call fails, that level is "unavailable" and the panel says so.

## Consequences
- New dependency: `pycaw` (comtypes comes with it).
- Brightness works on built-in displays only; desktops and most external monitors show "Unavailable".
- The core never knows an absolute level: it emits relative `LevelStep` events, which keeps it
  free of COM and replayable.
- Verified on the author's laptop: both levels were read (volume 100 %, brightness 88 %) and a
  no-change brightness write succeeded. Real stepping is part of the manual session.
