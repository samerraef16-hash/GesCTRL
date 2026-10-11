# Fixtures: turning a misfire into a test

Fixtures are landmark recordings (JSONL, no images). To keep a misfire from coming back:

1. **Record it.** `python -m gescrtl --record misfire`, reproduce the problem, stop the app.
   The file lands in `recordings/<time>_misfire.jsonl` (ignored by git).
2. **Trim it.** Find the time of the misfire with
   `python -m gescrtl.replay recordings/FILE.jsonl --resume`, then cut a few seconds around it:
   `python -m gescrtl.replay recordings/FILE.jsonl --slice START_MS END_MS --out tests/fixtures/NAME.jsonl`
   (the slice starts with a RESUME command, because the engine always starts Paused).
3. **Write the expectation.** Add `tests/fixtures/NAME.expect.json` listing event types that must
   not happen, for example `{"forbidden": ["Click", "ButtonDown"]}`. The test
   `tests/replay/test_fixture_regressions.py` replays every fixture that has this sidecar and fails
   if a forbidden event appears. It should fail now.
4. **Fix the code** until it passes.

Only landmarks are stored, never camera images. Keep fixtures short (a few seconds).
