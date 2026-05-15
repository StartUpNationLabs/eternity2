# Current vol — vol-52 (opening) — 2026-05-15

**Predecessor**: vol-51 closed with B1 bound-trigger infrastructure
shipped but the recovery path identified as the bottleneck. Standing
458 record unchanged. See [[../sessions/vol-51]].

## Vol-52 binding item — design document for lifted-LP via per-piece column-generation

**Mode**: research-grade design document, NO new code shipping this vol.

### Why this, why now

After 6 negative-result volumes on record-breaking tracks (vols 46-51),
the empirical evidence is overwhelming: **local search cannot close
the ~20-point LP-integer gap that exists in every basin**. Multi-week
algorithm change is what's actually needed.

The vol-50 [[../concepts/lp-integer-gap-anatomy|LP-integer gap anatomy]]
identified the binding constraint precisely:
- 33% of the gap is in fractional LP values (closeable by classical cuts).
- 67% is in integer-valued per-color LP UBs that cannot be jointly
  achieved due to piece-uniqueness.

Vol-47 already ruled out naive McCormick lifting on x-products (intractable
at canonical scale). But **per-piece decomposition** has not been
seriously analysed. The math is non-trivial; the design deserves a
careful write-up before any code investment.

### Scope for vol-52

1. **Write `vault/concepts/lifted-lp-column-gen-per-piece.md`** —
   a careful design document covering:
   - Lagrangian decomposition of the master problem by piece.
   - Per-piece subproblem structure (a piece is assigned to one cell
     with one rotation; LP gives fractional placement; we want to
     resolve piece-uniqueness exactly while relaxing it within
     subproblems).
   - Column-generation pricing: which placements to add to the master.
   - Stability conditions / convergence proof sketch.
   - Comparison to vol-47's failed lifting.

2. **Worked example at small scale**: 6×6/5c canonical-shaped puzzle.
   Hand-derive the per-piece columns for the first 2-3 generation
   rounds. Demonstrate the math actually closes a portion of the gap
   that vol-47's lifting did not.

3. **Build cost estimate**: how many weeks of engineering work would
   the full per-piece column-gen LP solver be? Identify the biggest
   unknown.

### Out of scope (NOT this vol)

- Building the LP solver itself.
- Running it on canonical E2 (would require weeks of engineering).
- Comparing measured LP UB to current 478.

### Risk budget

- Tight: 2 days of careful math + write-up.
- Kill condition: if the math reveals per-piece decomposition has a
  fundamental obstruction (e.g., scales worse than McCormick), document
  the obstruction and stop.

### What this produces

A durable vault concept page that:
- Future agents/researchers can read to understand the LP path.
- Captures the decision trail (why per-piece, why not McCormick, why
  not subgradient).
- Estimates the engineering cost for any future build.

## Audit-at-open

Aged ≥ 3 vols (from BACKLOG, not picked vol-51):
- `mcgavin-prune-restart-bound-trigger` (since vol-36) — built vol-51, recovery path identified as bottleneck, DEFER (not picking again)
- `unsat-soft-value-order-vol37` (since vol-34) — defer to vol-53+
- `multi-cell-bound-ascent` (since vol-22) — `wont-do` (vol-21/22 collapse mode confirmed)
- `bound-floor-alns-with-per-step-check` (since vol-22) — defer; invasive ALNS internals work
- `restore-or-simd` (since vol-25 perf) — engineering not research; defer
- `precompute-cell-nb-info` (since vol-25 perf) — engineering not research; defer
- `vault-validation-of-perf-wins` (since vol-25) — engineering; defer
- `learned-on-ties-long-pt` — already marked wont-do vol-50

Most are engineering work or already wont-do. Vol-52 picks none of them;
the binding item is design, not picking from this list.

## Linked

- [[../sessions/vol-51]] — predecessor
- [[../concepts/lp-integer-gap-anatomy]] — vol-50 math motivation
- [[../concepts/lifted-lp-formulation]] — vol-47 design (McCormick)
- [[../concepts/lifted-lp-column-generation]] — vol-47 column-gen attempt
- [[../concepts/lp-ub-478-basins]] — vol-44 basin survey
- [[../concepts/lp-ub-479-basin-found]] — vol-46 class D
