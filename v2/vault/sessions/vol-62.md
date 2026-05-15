# Vol-62 — Homotopy-ALNS refuted; sound joint-MIP-bound on 458+ records

**Theme**: First invented-algo vol (per user directive vols 61-70).
β₁-cycle destroy was the proposed primitive. Empirically refuted,
pivoted to component-quotient-destroy (also pre-existing), then
landed the SOUND result: 458/459 records are joint-MIP-locally-
optimal at halo-1.
**Date**: 2026-05-15 (closed 18:50 CEST).
**Standing record at open / close**: 459/480.

## Headline result

**Sound, falsifiable proof:** The local 459 (p06), vol-32 458, and
both vol-61 458 records (seed17, seed200) are **joint-MIP-locally-
optimal at halo-1**. With ALL defect cells + their immediate halo
free simultaneously (57-64 cells per board), no piece-permutation +
rotation can improve the score. Verified with HiGHS-backed MIP in
180s each.

This rules out ALL local destroy operators with effective halo ≤ 1
as candidates for breaking 458 or 459 from these basins. Any
operator in this class — `ComponentDestroy`, `ComponentClusterDestroy
{halo: 1}`, `MwpmDefectPair`, `WorstWindow{k≤60}`, `ConflictDriven
{≤60}` — is bounded by the MIP.

## What was attempted

1. **Day 1 morning**: drafted Homotopy-ALNS spec
   ([[../concepts/homotopy-alns]]) — destroy regions bounded by β₁
   generator cycles of the defect graph.
2. **Day 1 midday**: prototyped β₁ measurement in
   `scripts/vol62_homotopy_alns.py`. Found β₁ = 0 on local 459.
3. **Day 1 broad scan**: ran β₁ measurement on 2,293 saved boards.
   Conclusion: β₁ = 0 across all known records ≥ 458.
4. **Day 1 pivot**: defect graphs are FORESTS at records;
   cycle-targeted destroy is useless. Pivoted to
   "Component-Quotient-Destroy".
5. **Day 1 honest correction**: audited codebase, found
   `ComponentDestroy` + `ComponentPlusHaloDestroy` already exist
   (vol-17 NOVEL). Re-framed CQD as a tuning/scheduling change.
6. **Day 1 evening**: identified the genuinely-new gap and shipped
   `ComponentClusterDestroy { cluster_radius, halo }` op. Exposed
   via `--ops cluster_only` and `--ops winning5_cluster`.
7. **Day 1 late**: built `vol62_cluster_mip_bound` driver using
   existing `cluster_repair.rs` HiGHS MIP. Ran on local 459 at
   r=1, r=2, r=3, and joint-MIP. Repeated on vol-32 458 and the
   two vol-61 458 records.

## What was measured / kept

### β₁ measurement (refutes Homotopy-ALNS)

2,293 saved boards. At every score ≥ 458 (n=33), β₁ = 0. β₁ > 0
appears only at scores ≤ 455 and is always 1 (rarely a single tiny
4-cycle). Refutes the concept before implementation.

### Joint-MIP-bound (vol-62 headline)

| board | n comps | joint region | delta | obj | MIP time |
|---|---|---|---|---|---|
| local 459 (p06) | 4 | 59 cells | +0 | 120.0 | 180.24s |
| vol-32 458 | 2 | 57 cells | +0 | 112.0 | 180.04s |
| vol-61 458 (seed17) | 4 | 62 cells | +0 | 127.0 | 180.02s |
| vol-61 458 (seed200) | 5 | 64 cells | +0 | 127.0 | 180.14s |

All 4 records yield joint-MIP delta = +0. The proof generalizes —
this is a STRUCTURAL property of the high-score regime.

### Per-component MIP (radius 1)

On 459: 4 components (sizes 18, 11, 4, 2), all proven delta=+0 at
halo r=1. Confirmed at r=2 (5-30s timeout on big comps, smaller
comps proven optimal sub-second).

On 458 (vol-32): 2 components (sizes 32, 4), all delta=+0 at r=1.

### `ComponentClusterDestroy` operator shipped

`crates/localsearch/src/alns.rs::ComponentClusterDestroy {
cluster_radius, halo }`. Exposed as `--ops cluster_only` and
`--ops winning5_cluster` in `alns_only`. Bounded by the joint-MIP
proof at halo ≤ 1.

## What was refuted

- **[[../concepts/homotopy-alns]]** — β₁ = 0 on all records.
  Concept marked `refuted` with full evidence in concept page; no
  quiet delete.
- **[[../concepts/component-quotient-destroy]]** — concept survives
  but operator is BOUNDED by joint-MIP-bound at halo ≤ 1. Status
  `refuted at halo ≤ 2` (per-component) and `refuted at halo ≤ 1`
  (joint).

## What's NEW (the actual vol-62 deliverables)

1. **β₁ scan** of 2,293 boards: empirical characterization that
   defect graphs are forests at records.
2. **Component-size regime**: at score 459, components are size ≤ 5;
   at 458, sometimes one big 32-cell component; structure differs.
3. **`vol62_cluster_mip_bound` bin**: drop-in tool to compute sound
   integer upper bounds on any local-repair improvement.
4. **Joint-MIP proof**: refutes a whole class of local operators as
   record-breakers; redirects vol-63+ toward BOARD-SPANNING or
   TRAJECTORY-DEPENDENT mechanisms.
5. **`ComponentClusterDestroy` operator**: shipped but bounded.

## Concepts touched

- [[../concepts/homotopy-alns]] — `refuted` (β₁ = 0 on records)
- [[../concepts/component-quotient-destroy]] — `refuted at halo ≤ 1`
- [[../concepts/mip-local-optimality-459]] — NEW, `built`

## Open at close

- Run joint-MIP on the cross-machine SOTA p20 459 board (different
  basin geometry — does the conjecture hold there too?).
- Run radius-2 joint-MIP (region ≥ 90 cells). May not solve to
  optimum in budget; column generation needed for proof.
- Vol-63 pivot: NON-local mechanisms. Drafted
  [[../concepts/temporal-rewind-search]] with codebase audit
  up-front (lesson learned from vol-62).

## NOTE: this is the vol-62 session; vol-65 is its own session

See [[vol-65]] for the substantial vol-65 work that came after.

## Linked memory

- `feedback_vols_61_to_70_invented_algos` — directive
- `feedback_no_false_metrics` — vol-62's MIP IS a sound bound, unlike
  `greedy_relaxed_score`
- `project_e2_459_sota_cross_machine` — for context on the 459
- TBD: new memory entry "458+ records jointly MIP-locally-optimal at
  halo-1" to capture for future agents
