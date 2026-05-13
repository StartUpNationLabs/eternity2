# VOL-33 — pivot to engine + community-knowledge tracks

**Opened**: 2026-05-14 (vol-32 close, post-ML-bug discovery).
**Status**: drafted overnight at vol-32 close.
**Theme**: vol-32 refuted vol-30/31's ML lift as a one-line bug.
Per user note "if ML is not that good, move on", vol-33 pivots from
ML to two BACKLOG items that have been queued since vol-32 open and
are now top priority: (a) unsat-clause-propagator (capiman/e2 database),
(b) joe-iteration-budgeted-prune. Also adds (c) InsertionOrder
investigation as the lightweight follow-up to vol-32's discovery.

## Why this volume exists

1. **ML closed for now**: the canonical 5-clue 16×16 ML lift is real
   but small (+3 matched edges from imitation, +0 score post-ALNS).
   The vol-30/31 headline numbers were a bug. RL self-play remains
   the only direction that could structurally beat the imitation
   ceiling, but it's a 1-2 week build that hasn't yet shown leverage.
2. **Community-knowledge propagators are unexplored**: capiman/e2's
   70M unsat 2-piece clauses are sitting in `output/capiman_e2/`.
   Vol-32's Python prototype confirms the data loads and parses
   cleanly (130k literals, 53M clauses in 56s). Rust integration is
   ~1 day, and this would be the **first time we use community-verified
   pruning** in the engine. Likely the largest pruning gain since
   gacolor + AC-3.
3. **Joe's iteration-budgeted prune is half a day**: reuses existing
   `mcgavin-prune-restart` plumbing (vol-23) with a different
   triggering policy (iteration-count rather than CP-depth). msg
   #11725 reports 30-49% search-space reduction.
4. **Vol-32 discovered InsertionOrder > EdgeBpMarginals by +9 under
   joe_depth150_bp**. Worth characterising across profiles before
   committing engine-level changes.

## Audit-at-open

Items aged ≥ 3 vols (vol-33 open, items ≤ vol-30 are old).

Vol-32 already promoted these to `refuted` or `wont-do`:
- `learned-on-ties-hybrid` (vol-30) → `refuted`
- `learned-on-ties-alns-postfill` (vol-31) → `refuted (re-attributed)`
- `learned-on-ties-basin-escape` → `wont-do (premise refuted)`
- `learned-on-ties-hyperparam-sweep` → `refuted (no-op)`

Remaining aged items:
- `multi-cell-bound-ascent` (12 vols): defer (ALNS-axis, orthogonal).
- `bound-floor-alns-with-per-step-check` (12 vols): defer.
- `diverse-457-search` (13 vols): defer.
- `learned-16x16-long-train` (RL self-play flavor): defer; ML closed.

NEW vol-32 items pickable for vol-33:
- `unsat-clause-propagator-prototype` (Python prototype shipped) — **PICKED, becomes T1**.
- `insertion-order-under-joe-depth150-bp` (partial) — **PICKED, becomes T3**.

## Binding items (3 max)

### T1 — Unsat-clause-propagator Rust integration

**Vol-32 bootstrap shipped** the loader + bench bins:
- `target/release/unsat-clauses-load --info ... --cnf ... --out forbidden.bin`
  parses 67.4M pairs from 68 files in <60s, writes 540 MB CSR binary.
- `target/release/unsat-clauses-bench forbidden_all.bin` measures
  lookup: **238 ns per placement** (4.2M placements/sec).
- `output/vol-33/forbidden_all.bin` (540 MB) and `forbidden_round1.bin`
  (425 MB) ready for vol-33 engine consumption.
- At ~500K nodes per canonical run, overhead ≈ 120 ms — negligible.

Vol-33 remaining work:
1. **Encoding reconciliation** (vol-32 discovered the mismatch — see
   `output/vol-32/unsat_validation_FINDING.md`): 74% of our placements
   aren't in capiman's encoder, and 21 conflict pairs flagged on
   placements that ARE encoded (= known-good moves marked forbidden).
   Need to:
   a) Parse capiman's piece edge tuples (PatternN/E/S/W columns in
      `e2_info.c`).
   b) Build piece-equivalence map: capiman_card_N → our_piece_id_M
      via edge-tuple match.
   c) Resolve rotation convention (capiman 1..4 → our 0..3 + offset).
   d) Re-validate against `edge_bp_165` until 0 conflicts.
   Half a day of careful Rust work — NOT optional.
2. **Engine integration**: in `place_and_propagate` (after gacolor +
   AC-3), compute the placed literal X via the encoder, iterate
   `forbidden_partners[X]`, decode each Y to `(piece, field, rot)`,
   and call `remove_from_domain` on that cell's row matching that
   piece+rotation.
3. **Lazy load**: OnceCell-protected; only load when a profile that
   uses it is instantiated.
4. **Profile registration**: new `joe_depth150_bp_unsat` profile in
   `EngineConfig`. Falls back to no-op if `forbidden.bin` missing.
5. **Gate**: depth lift ≥ +5 on canonical 5-clue at 60s; clear
   measurement that adds to gacolor + AC-3 rather than subsumed by it.

Cost: **1.5-2 days** (loader + bench done; reconciliation is the
unblock). Estimate revised upward at vol-32 close after the
validation found the encoding mismatch. Without reconciliation, the
propagator would prune valid moves — silent correctness bug.

### T2 — Joe iteration-budgeted prune

Port msg #11725's policy on top of existing `mcgavin-prune-restart`
plumbing (vol-23 shipped):
- New `SolveOpts.prune_iter_budget: Option<usize>` field.
- New triggering policy: if `current_depth > 150 && iterations_since_progress > 2000`,
  trigger prune-to-depth-150 restart.
- Compare cold-start nodes/depth on canonical 5-clue at fixed budget.

Cost: half a day. The infrastructure exists; this is policy tuning.
Gate: 30%+ search-space reduction at iso-budget.

### T3 — InsertionOrder generality investigation

Characterise vol-32's surprise finding (InsertionOrder beats
EdgeBpMarginals by +9 depth under joe_depth150_bp) across the engine
profile registry:
- `joe_depth150_bp` (confirmed +9 depth on canonical)
- `border_first_lcv` (baseline)
- `blackwood_raw` (Blackwood)
- `gacolor_ac3_ns1` (NS-1 propagator)
- `joe_depth150_bp_par` (parallel variant)

For each profile, A/B with `--mode insertion` vs the profile's
default. Report depth, nodes, matched edges. If InsertionOrder wins
generally, consider making it the default value-order for
high-propagator profiles; if it wins only under joe_depth150_bp,
characterise why (likely propagator-induced ordering interacts with
BP sort).

Cost: ~half day. ~5 profiles × 60s budget × 2 modes = 10 min compute
+ analysis writeup.

Combined gate: at least one of T1/T2/T3 produces a measurable improvement
in depth, score, or characterisation. If all three null-out, vol-34
pivots to vanilla-fast-backtracker as the remaining BACKLOG item.

## What this vol explicitly does NOT do

- ❌ More ML training. Imitation ceiling reached; RL is a separate
  multi-week project; LOT post-fix is +0 score.
- ❌ Vanilla fast backtracker (BACKLOG vol-34+). Heavy build, lower-EV
  than unsat-propagator.
- ❌ Bound-ascent variants (BACKLOG, multi-vol deferral). Score-axis
  isn't the binding constraint; depth + pruning is.
- ❌ Re-running T3 PT lottery from `lot_fixed_v4` partial. Vol-32 T6
  already showed the post-fix LOT gives -2 ALNS — no PT lift
  expected.

## Honest cost estimate

- T1: 1-2 days build + half day measurement = 2 days.
- T2: half day build + half day measurement = 1 day.
- T3: half day total.
- Vault close: 30 min.

**Total**: 3.5 days. Comfortably fits a normal volume window (the
overnight rule applies; estimates 1.5-3× too long, actual likely 2-2.5 days).

## Files / drivers needed

```
crates/solver-engine/src/unsat_propagator.rs   NEW
crates/solver-engine/src/lib.rs                MOD (propagator hook, profile)
crates/ml-export/src/bin/canonical_eval.rs     MOD (--mode unsat or new profile arg)
ml/unsat_propagator_proto.py                   EXISTS (vol-32)
output/capiman_e2/                             EXISTS (Git LFS data, vol-32)
output/vol-32/unsat_propagator/literal_decoder.json   EXISTS (vol-32 Python output)
ml/measure_insertion_order.sh                  NEW (T3 driver)
```

## Linked concepts

- [[../concepts/unsat-clause-propagator]] — vol-32 prototype, vol-33 build target.
- [[../concepts/learned-value-order]] — closed for now post-vol-32 correction.
- [[../sessions/vol-32]] — direct predecessor with full context.

## Why this is the right shape

- **Highest-EV from BACKLOG**: unsat-propagator is the single largest
  pruning gain we haven't tried. Community-verified data sitting on disk.
- **InsertionOrder is the lightweight win**: vol-32 already discovered it;
  T3 just measures whether it generalises beyond joe_depth150_bp.
- **Joe's prune policy is half a day with existing infrastructure**.
- **All three tracks have clean numeric gates**: pass/fail on a single
  measurement.
- **Vol-33 negative result is informative**: if none of T1/T2/T3 moves,
  the remaining engine-axis options are vanilla-fast-backtracker (vol-34)
  and RL self-play (vol-35+). We'll know where the ceiling really is.

## Vol-32 closeout summary (for context)

Vol-32 was "overnight ML engineering" — discovered the ML lift was a
bug (lib.rs:2550 cell_side_edge missed LearnedOnTies arm), fixed in
commit `95978a5`. Real ML signal at canonical is +3 matched edges,
not the claimed +9 depth / +10 score. The +9 was actually
InsertionOrder beating EdgeBpMarginals under joe_depth150_bp.
Unsat-propagator Python prototype shipped as the vol-33 foundation.
