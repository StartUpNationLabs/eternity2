# VOL-37 — canonical-respecting record chase

**Opened**: 2026-05-14 (~16:35 CEST) at vol-36 close.
**Status**: BINDING (autonomous-mode plan).

## Why this volume

Vol-36 discovered the **canonical-compliance tension**: search paths
that reach deep tend to displace canonical hint pieces; ALNS preserves
the displacement; resulting "458 records" are 3/5 hints honored.

Vol-36 also produced the **make-canonical operator** (vol-36 finding):
take a non-canonical record, drop the displaced positions + canonical
positions, add canonical hints, prune_restart fills the 4 gaps with
MaxScore. **Reproduced 458 → canonical-446 in 0.1s of CP**.

Vol-37's binding question: can ALNS from a canonical partial reach
≥458 score under STRICT canonical-hint compliance (5/5)?

## Vol-37 binding items

### T1 — canonical ALNS lottery on 7 canonical partials

For each of the 7 valid records → make-canonical → prune_restart fill →
ALNS 5min × 5 seeds × 4 ops = 140 ALNS runs.

If any yields verified canonical 459+, that's a new canonical record.

**Gate**: ≥1 verified canonical (5/5 hints, piece-unique) board ≥ 458.

Cost: ~50 core-hours sequentially; with -P4 parallel ~12 wall hours.

Script: `ml/vol37_canonical_lottery.sh`.

### T2 — bigger pin-hints CP compute

vanilla_fast 5min × 8 threads pin-hints: depth 208, score 429.
What does 30min × 8 threads achieve? Or 8 hours overnight?
The depth-208 wall might break with more compute on the 5 threads
NOT stuck at depth 34.

Cost: 8 hours wall.

## Out of scope

- No new bin builds.
- No new path modes.
- No engine changes.

## Linked

- [[vol-36]] — predecessor (vanilla_path + canonical-compliance finding)
- [[prune-restart]] — used to make-canonical
- [[score-optimizing-cp]] — MaxScore objective in prune_restart
