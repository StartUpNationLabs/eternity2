# V15_FRAME_ENUMERATOR_SPEC.md

**Author**: vol-14 (2026-05-12), writing for vol-15 implementer.
**Purpose**: replace vol-12's pairwise-Hamilton frame enumerator
(`scripts/v12_hamilton_frame.py`) with a CSP-aware variant that
filters out frames inconsistent with the 4 interior canonical hints
under propagation. Vol-14 measured that ≥47% (baseline propagation)
or ~100% (gacolor+AC3) of vol-12's 75 173 frames (a LOWER BOUND
from a 120s time-budgeted DFS — NOT exhaustive) fail at hint-apply
time. **The vol-12 catalog is necessary-but-not-sufficient.** The
spec below describes a new enumerator that returns frames already
proven CSP-consistent end-to-end.

## Background

- **Vol-12 enumerator** (`v12_hamilton_frame.py`): DFS over 60 ring
  positions (4 corners + 56 edges), pinning TL corner for symmetry,
  enforcing pairwise edge-color matching `ring[i].out_side ==
  ring[i+1].in_side`. Result: 75 173 frames in 120 s — the DFS
  hit its time budget and did NOT complete. **The vol-12 catalog
  is a lower bound; the true Hamilton-valid count is unknown
  (likely much higher).**
- **Hint positions on canonical E2** (all 5 are interior, NONE on
  the ring): pos 34 (2,2), pos 45 (13,2), pos 135 (7,8), pos 210
  (2,13), pos 221 (13,13). The vol-12 enumerator never propagated
  any hint constraint into the ring DFS — the hints' edge colors
  can be entirely inconsistent with what the ring placed nearby.
- **What it misses**: 4 of the 5 canonical hints are *interior*
  (positions 135, 210, 34, 221). These hints' edge colors must
  match their neighbours' edges. Some of those neighbours are on
  the ring; some are deeper interior. Vol-12 never propagated the
  interior-hint constraints back to the ring.
- **Vol-14's measurement**: applying a frame + 5 canonical hints to
  the Rust engine (`crates/bench-audit/src/bin/run_e2_framefirst.rs`)
  rejects 47-100% of vol-12 frames depending on propagation strength.
  See [[project-e2-vol14-framefirst-null]] memory.

## Goal

A vol-15 enumerator that:
1. Visits the same 60-cell ring placement space as vol-12.
2. Maintains an incremental **per-cell domain bitset** for ALL 256
   cells (not just the ring) using the same data structure as
   `solver-engine::SearchState::domain_bits`.
3. At each ring step, calls **gacolor + AC-3 propagation** on the
   placed prefix.
4. Also pins the 4 interior canonical hints AT THE START (before
   any ring DFS) and runs propagation, so the ring DFS starts from
   a domain state where the interior hints are already constrained.
5. Returns only frames where, **after applying all 60 ring hints**,
   the engine state is still consistent (no empty domain at any
   unplaced position).

## Estimated surviving count

Lower bound: the puzzle has exactly one solution (vol-10 probe #6),
so at least one frame is CSP-valid. **No usable upper bound** —
vol-12's 75 173 was a time-bounded sample, not exhaustive, so the
true total is unknown.
Order-of-magnitude estimate based on vol-14's data:
- Of 500 random frames, **~0** pass the full gacolor+AC3 hint-apply.
- Of 500 random frames, **267 (53%)** pass *baseline-prop* hint-apply
  but their interior is exhausted in <200 ms.
- Inferred: gacolor+AC3 is roughly 100× stricter than baseline.
- Extrapolating: **0-100** globally-CSP-valid frames out of the
  vol-12 sample of 75 173 (which itself was a 120s-bounded subset
  of an unknown larger Hamilton-valid total).
- **Most likely range**: 1-30 frames. If higher, vol-15 still wins
  (small enough sweep). If 0, the integration-CSP is actually
  proving the frame catalog itself is overconstrained (which would
  be a publishable null).

## Implementation plan

### Phase 1 — Rust port of the vol-12 DFS (~1 day)

New crate `crates/solver-frame-enum/`:
- `src/lib.rs`: `enumerate_frames(puzzle: &Puzzle, hints: &Hints,
  config: &FrameEnumConfig) -> Vec<Frame>`.
- `Frame { ring: [(PieceId, Rotation); 60], domain_snapshot:
  Vec<u64> }` — the second field is the `domain_bits` state of all
  256 cells after this frame is applied. Pre-computing this means
  vol-15 #5 (frame × interior sweep) can resume from the snapshot
  without re-doing propagation.
- DFS state mirrors `SearchState` but is specialised for ring
  enumeration: variable order is fixed (the 60 ring positions in
  order), value order can be `ring[i].piece_id` ascending or
  randomised by seed.

### Phase 2 — Integrate gacolor + AC-3 (~1 day)

The current `SearchState::place_and_propagate` already does what
we need. Reuse it. Two design options:

**Option A (preferred)**: import `SearchState` from
`crates/solver-engine` and drive it directly from the frame
enumerator. Add a public `pin_to(pos, row_id)` method to
`SearchState`. Frame enumerator becomes a thin wrapper that calls
`SearchState::new` once + 60 sequential `pin_to + place_and_propagate`
calls per candidate frame. If any returns `Wipeout`, prune; else
continue DFS.

**Option B**: re-implement gacolor + AC-3 in the frame-enum crate.
More code; faster (no per-call overhead from the full engine
state). Defer to vol-16 if Phase-1 Option-A is too slow.

### Phase 3 — Pre-pin all 5 canonical hints (~few hours)

Before ring DFS starts:
1. Call `SearchState::new` on the full puzzle.
2. Apply each of the 5 canonical interior hints (positions 34, 45,
   135, 210, 221) via `pin_to + place_and_propagate`.
3. Save this state as the "root" SearchState.
4. For each ring DFS branch, **clone the root state**, then apply
   ring placements on top.

Cloning a `SearchState` is `O(n_cells × words_per_pos)` =
`256 × 4 = 1024 u64` = ~8 KB per clone. Cheap enough to clone
per top-level DFS branch but probably want a copy-on-write or
undo-stack approach for deep branches.

### Phase 4 — Output schema (~hours)

```json
{
  "schema_version": 2,
  "info": {
    "puzzle": "size_16_official_eternity.csv",
    "elapsed_s": ...,
    "dfs_nodes": ...,
    "propagator_strength": "gacolor_ac3",
    "hint_pre_pin": [34, 135, 210, 221]
  },
  "frames": [
    {
      "ring": [[pid, rot], ...60 entries...],
      "A_multiset": {"1": 12, "2": 12, ...},
      "interior_domain_sum": <int>,
      "interior_smallest_domain": <int>,
      "interior_already_empty_count": <int>  // 0 = consistent
    },
    ...
  ]
}
```

Backwards-compatible with vol-12's schema where fields overlap.

## Risks

1. **Speed**: gacolor + AC-3 per DFS node is slow vs vol-12's
   pairwise check (~10 µs vs ~100 ns). 75k frames × 8M propagations
   = ~5 hours wall-clock single-thread. Mitigation: use the
   "domain bits delta from parent" undo log so we don't re-propagate
   from scratch at each DFS step. With incremental propagation we
   should land ~30-60 min total.
2. **Memory**: storing the full domain_bits snapshot per surviving
   frame is `~8 KB × N_surviving`. If N=100, that's 800 KB — fine.
   If N=10 000 (unlikely), 80 MB — also fine.
3. **Correctness**: the Rust engine's propagators are tested but
   the frame enumerator will call them in unusual patterns
   (pinning corners then progressing around the ring rather than
   the engine's MRV/border-first order). Need a smoke test:
   the enumerator must reproduce at least one known board (e.g.,
   the 443 BP-seeded board has a valid Hamilton frame → that frame
   should be in the output).

## Vol-15 task list (in order)

- [ ] **#13.1**: scaffold `crates/solver-frame-enum/` with empty
  `enumerate_frames` returning the vol-12 results.
- [ ] **#13.2**: add `SearchState::pin_to_public` + clone support.
- [ ] **#13.3**: implement Phase-3 (pre-pin interior hints).
- [ ] **#13.4**: implement Phase-1/2 ring DFS + incremental prop.
- [ ] **#13.5**: smoke test: enumerator must find ≥1 frame derivable
  from `output/HISTORIC_first_454_1778567792.json`.
- [ ] **#13.6**: full enumeration → write
  `output/v15_frames/csp_valid_frames.json`.
- [ ] **#13.7**: for each surviving frame, run
  `joe_depth150_par + EdgeBpMarginals` on the residual interior
  (Blackwood-policy-aware engine if vol-15 #1 lands first).

## What this unblocks

- **Frame × interior sweep** (vol-14 plan item #5): with ~100
  surviving frames × ~30 s each = ~1 hour to try every globally-CSP-
  valid frame. If the puzzle has exactly 1 solution, one of these
  frames is THE solution-frame; the question becomes whether the
  interior search can complete it.
- **Better CP heuristics**: the interior search starting from a
  globally-consistent frame has dramatically smaller domains, so
  the BP marginals + NS-1 propagator + AC-3 are all more effective.
- **Honest comparison with McGavin/Blackwood**: their algorithm
  uses break-indexes to *allow* mismatches and reach 469. With our
  CSP-valid frames + interior search aimed at the full puzzle (no
  breaks), we either find 480 or prove no completion exists for
  that frame.

## Related

- `scripts/v12_hamilton_frame.py` — the prior implementation.
- `crates/bench-audit/src/bin/run_e2_framefirst.rs` — vol-14 test
  harness that surfaced the null.
- `output/v12_hamilton/frames_full.json` — vol-12's 75 173 frames
  (misleadingly named — NOT a full enumeration; lower bound only).
- `output/v14_framefirst/latest/results.tsv` — 500-frame survey.
- Memory entries: `project_e2_vol14_framefirst_null.md`,
  `project_e2_hamilton_frame_count.md`,
  `project_e2_mcgavin_blackwood_gap_analysis.md`.
