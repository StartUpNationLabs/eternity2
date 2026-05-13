---
tags: [concept, bug, postmortem]
status: fixed
origin-vol: 14
---

# Hint pinning bug (the alns_e2 unpinning bug)

**Status**: `fixed` in commit `afb3dc9` (vol-14)
**Origin**: vol-14 audit
**Files**: `crates/bench-audit/src/bin/alns_e2.rs`

## What happened

`alns_e2` was UNPINNING canonical hints during destroy steps. Destroy operators (RandomCells, etc.) selected hint cells alongside regular cells. The repair then placed *different* pieces there. ALNS was effectively running on a **different puzzle** than canonical 5-clue E2.

## Impact

All vol-12 and early-vol-14 ALNS-fill scores (442/443/436) were on the wrong puzzle. The relative ordering of profiles still held, but absolute numbers were ~3 points high.

True baseline post-fix: **~440** (not 443). The vol-14 BP-seed lift was real but smaller than reported.

## Fix

Commit `afb3dc9`: filter canonical hint cells out of destroy selection in every operator. Add debug-assertion that hint cells stay pinned across all destroy/repair cycles.

## Why it slipped

- ALNS destroy operators were written without an explicit hint-aware contract.
- No invariant check on hint pinning at iteration boundary.
- Score-only metric: the bug never reported a hint mismatch as an error because the hint pieces were valid 480-pieces.

## How to prevent recurrence

- `AlnsState` now carries `Pinned<Cell>` set; destroy operators take `&Pinned` and skip those cells.
- `debug_assert_eq!(state.canonical_hints(), CANONICAL_HINTS)` at each iter (release: zero cost).

## Linked concepts

- [[alns]] — the algorithm where this lived
- [[basin-457-pt]] — current cold-start record (post-fix)

## Linked memory

- `project_e2_vol14_alns_hint_bug`
