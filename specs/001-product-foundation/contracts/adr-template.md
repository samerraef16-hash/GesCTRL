# Contract: Decision Record (ADR) Template

Files: `docs/adr/NNNN-short-title.md`, numbered sequentially. Required for FR-014.

```markdown
# ADR NNNN: <Title>

- **Status**: Proposed | Accepted | Superseded by ADR XXXX
- **Date**: YYYY-MM-DD
- **Related**: spec FR-xxx, research Rx, other ADRs

## Context
What problem or decision is being made, and which constraints apply (constitution principles,
spec requirements, platform limits).

## Options Considered
1. **Option A**: summary; pros; cons
2. **Option B**: summary; pros; cons
3. ...

## Decision
The chosen option, stated in one or two sentences.

## Evidence
At least one concrete item: a measurement (link to feasibility report row), an observation from
the spike, or a documented comparison. (SC-005)

## Consequences
What this enables, what it costs, which limitations it introduces, and what would trigger
revisiting it.
```

Required ADRs for Phase 0:
- 0001 hand tracking
- 0002 input injection
- 0003 HUD overlay
- 0004 packaging
- 0005 pointer mapping (including the final smoothing parameters and anchor point)
