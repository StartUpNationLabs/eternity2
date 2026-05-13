# RESEARCH_NOTES_22_PLAN.md — vol-22 entry plan

**Date:** 2026-05-13 (drafted at vol-21 close).
**Predecessor:** read [[RESEARCH_NOTES_21.md]] first.

## State at vol-21 close

- **Cold-start ceiling**: still 457/480 (unchanged from vol-17/vol-18).
- **NEW METRIC**: relaxed-edge bound (per-board) — quantifies basin
  ceiling under cell-by-cell perturbation with relaxed piece-uniqueness.
- **Our 457 basin's ceiling**: **461** (gap = +4).
- **Different basins have different ceilings**: 456 boards span
  457-464, so basin ceilings are NOT score-determined.
- **Bound-ascent**: a NEW algorithm class. From any board, single-swap
  mutations can raise the relaxed bound by +6 to +12. We've reached
  bound=473 starting from a 450-score board.

## Empirical no-go (vol-21 ruled out)

1. ALNS at 30-60s budget recovers from any K≤47-cell destroy to the
   *same byte-identical* 457 board.
2. Hot-PT t-max 30 on a 456/464 basin (5min) made no progress.
3. Alternating bound-ascent + ALNS doesn't work: ALNS falls back
   to the original 457 within 1-2 iterations.

## Vol-22 priorities (ranked by potential impact × build cost)

### T1 — Bound-PRESERVING score recovery (1-2 days)

The composition `bound-ascent → ALNS` fails because ALNS doesn't
see bound. Modify ALNS:
- Acceptance: require `bound(new) ≥ bound(current)` AT EACH ACCEPT.
- Or: include bound in the objective: `score + λ × bound` with
  λ chosen to favor bound preservation.
- Or: at each repair-step, prefer moves whose relaxed-bound-impact
  is ≥0.

Implementation: modify `crates/localsearch/src/alns.rs` to accept
a `bound_floor: u32` parameter. Reject any candidate whose bound
falls below floor.

### T2 — Bound-ascent + CP recovery (high novelty)

After bound-ascent reaches bound=470, the edge structure has 470
locally-satisfiable adjacencies. Use this as a value-order guide
for Blackwood CP starting from canonical hints:
- For each cell, prefer pieces whose rotation matches the bound-470
  edge structure.
- Run CP under this guidance; the partial solution should naturally
  realize the high-bound edge structure.

If successful → 470-score directly. Build cost: 1 day to integrate
with existing solver-engine.

### T3 — Multi-cell bound-ascent moves (1 day)

Single-swap bound-ascent plateaus at 470-473. Maybe 3-cell or
4-cell cyclic moves can break through. Extend bound-ascent operator
to try K-cycles instead of just transpositions.

### T4 — Gap-guided basin triage (cheap)

For every board we save, compute and store the relaxed-bound and
gap. Boards with gap=0 are provable dead-ends; drop them from
the pool. Boards with high gap are worth more search.

Add gap-recording to `alns_e2`, `pt_e2`, and `cold_portfolio` save
paths. Build a "basin atlas" indexed by (score, bound) for visual
overview of the basin landscape.

### T5 — Survey: what's the maximum reachable bound?

Spend overnight compute on bound-ascent from many random starts and
many existing boards. Track the global max bound found. If it
approaches 480, we know an information-theoretic 480-bound exists.
If it caps at e.g. 475, the puzzle has a structural ceiling
below 480 (proof?).

### T6 — Implement the McGavin prune-restart (still on the books)

The original vol-21 plan still applies; bound-ascent is a sidetrack
that didn't produce a score win.

## Out-of-stack ideas

- Bound-ascent with random restarts (escape local-max-of-bound).
- Bound-ascent in dual space: edges as variables.
- Persistent homology of the (bound, score) phase diagram.

## Vol-22 entry tasks

1. Read this plan + RESEARCH_NOTES_21.md.
2. Pick T1 (bound-preserving ALNS) — highest EV at moderate cost.
3. Maybe T4 in parallel (cheap, gives long-term diagnostic).
