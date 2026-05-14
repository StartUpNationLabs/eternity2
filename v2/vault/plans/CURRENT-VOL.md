# SESSION CLOSED — 2026-05-14 19:30 CEST

**Autonomous session vol-36 → vol-42 complete. Awaiting user.**

## Headline

7 volumes of autonomous work. Real tools shipped, real measurements,
**3 new verified canonical records (454, 455 ×2)**, **1 positive engine
signal (RecordsPrior +8 mean ALNS score)**, **no record-break**.

Best canonical record: 457 (×3, unchanged).
Best absolute record: 458 (×2, unchanged, 3/5 hints).

## Why session closed (not continuing)

Three user re-evaluation prompts during the session indicated the same
problem: I kept defaulting to lottery work that didn't break records.
After 7 volumes and ~40 ALNS lottery runs, the empirical ceiling under
our current operators is firm:
- canonical 454 → 455 (25% via ALNS-diverse)
- canonical 455 → 456 (untested but expected ~10%)
- canonical 457 → 458 (0% across 24 runs, confirmed ALNS-locked)

To break 458 needs either community-class compute or a new algorithm
class (RL/MaxSAT/LP — each multi-day build).

The valuable contribution is the toolkit + honest measurements, which
are now documented and shipped. Continuing to launch lotteries would
produce more honest nulls without changing this picture.

## Next vol (vol-43+) — for user when returning

Three real directions remain unbuilt (each is a multi-day project):

1. **No-good CDCL learning** in solver-engine (~2-3d). Standard SAT
   technique not yet applied to E2. May give 5-15% search reduction.
2. **RL self-play for value-order** (~1-2 weeks). Vol-29 imitation
   ceiling identified RL as the only structural path past it. 1-week
   build + days training.
3. **LP relaxation B&B** (~1 week). Standard OR. Would need HiGHS or
   commercial solver (scipy too slow at this scale).

None of these guarantee a record-break, but each is a real frontier.

## Wake summary

See `vault/sessions/WAKE_SUMMARY_2026-05-14.md` for the full status
report covering vol-36-40.

For vol-41 (RecordsPrior) see `vault/sessions/vol-41.md`.
For vol-42 (McGavin canonical) see `vault/sessions/vol-42.md`.
