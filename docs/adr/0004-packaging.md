# ADR 0004: Packaging approach

- **Status**: Proposed
- **Date**: 2026-10-10
- **Related**: spec FR-014, research R4

## Context
Non-developer users need to install and run GesCRTL on Windows. The package must carry the Qt UI
and the MediaPipe model file.

## Options Considered
1. **PyInstaller, one-folder (`--onedir`)**: the most common route, handles PySide6 and data files, avoids the per-launch extraction delay of `--onefile`.
2. **Nuitka**: faster startup, harder to reverse engineer, but longer builds and more MediaPipe packaging friction.
3. **MSIX**: good install experience; signing overhead, consider at release time (Phase 10).
4. **Plain `pip install`**: not acceptable for non-developers.

## Decision
Use PyInstaller `--onedir` for early releases; revisit Nuitka if startup time or size is unacceptable.

## Evidence
Pending: packaging trial not yet run (build success, folder size, cold-start time to be recorded in
`spikes/feasibility/out/smoke-notes.txt` by T030). Comparison only until then.

## Consequences
Larger folder size than a single file but predictable startup. Installer and signing are handled in Phase 10.
