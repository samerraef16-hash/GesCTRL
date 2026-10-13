# ADR 0007: A second hand may type in Keyboard Mode

- **Status**: Accepted (decision taken in the spec 004 clarify session, 2026-10-13); implemented, not yet
  measured on the author's laptop
- **Date**: 2026-10-13
- **Related**: spec 004 FR-003a, FR-003b, plan D0 and D3, constitution v1.3.0 Principle I

## Context
Principle I allowed one controlling hand: the primary-hand lock, so that nobody else in view
could produce input. In Keyboard Mode one hand must both point at a key and pinch to press it.
The pinch moves the pointing hand, so pressing can slide the highlight onto a neighbouring key.
The user chose to let their other hand do the pinch.

## Options Considered
1. **Keep one hand only**: no rule change. The existing pinch lookback (`pinch_lookback_frames`)
   already reduces slide, and dwell is available. Rejected by the user's explicit choice.
2. **A second hand that only confirms, in Keyboard Mode only, if it passes a same-person check**:
   a narrow exception to the rule.
3. **Full two-handed air typing (Plan.md Phase 5b)**: research-grade with a single RGB webcam;
   deferred by the constitution (Principle II).

## Decision
Option 2. The second hand is accepted only when all of these hold:
- its handedness label differs from the primary hand's (the tracker mirrors both labels, so only
  "different" matters);
- its confidence is at least `min_confidence`;
- its wrist is within `second_hand_max_dist` hand sizes (default 3.0) of the primary wrist;
- it is not the hand the primary-hand lock currently treats as a bystander;
- it has been continuously accepted for `stable_frames` frames.

Once accepted it is followed by nearest wrist within `max_hand_jump`. Only the onset of its
thumb-index pinch counts: it presses the key the primary hand highlighted `pinch_lookback_frames`
earlier. It never moves the highlight and triggers nothing else. If both hands pinch in the same
episode, one key is pressed. The feature is on by default and can be turned off with
`two_hand_press`. Every other mode keeps one controlling hand.

## Consequences
- The constitution is amended to v1.2.0 (Principle I exception) and `CLAUDE.md` is synced.
- A bystander can still be mistaken for the second hand if they stand very close to the user
  and show the opposite hand. The check reduces this but cannot remove it. A recording of a
  second person pinching nearby (`bystander_pinch`) is a mandatory fixture and must produce 0
  presses (SC-003).
- Two hands in view overlap or cross sometimes. Tracking may swap or lose them; nothing is
  pressed until both are seen stably again.
- Press accuracy with two hands is unmeasured. It is part of the manual session (SC-001).

## Amendment 2026-10-13 (after the first manual test): the second hand types
Confirm-only was too narrow: the user wants to type with both hands, each pinching the key it
points at. The same-person check above is unchanged (the distance limit is now 5 hand sizes
because two hands held naturally are often more than 3 apart). What the accepted hand may do
grows from "confirm the primary hand's key" to "point at and press keys":

- it has its own smoothing, highlight, pinch selector and dwell (a second lane in the keyboard);
- whichever hand presses first sends first; both hands pressing the same key within the key
  cooldown send one stroke;
- it still never moves the cursor, changes state or mode, or makes any other gesture, and the
  primary hand keeps the pause, menu, fist and emergency paths;
- losing it presses nothing; losing the primary hand is the usual loss path (release all).

Option 3 above (full air typing) remains deferred in the sense of finger-level typing; this is
still pointing and pinching, now with two pointers. Constitution v1.3.0.
