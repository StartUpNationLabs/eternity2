# Vol-122 — Basin Diversity & Rigidity in Canonical Eternity II

**Date:** 2026-05-17  
**Status:** Working paper. **No record discovered** (best 452 < 459 standing). Documents the structural findings of the autonomous session.

## Abstract

Canonical Eternity II (16×16, 23 colors, 5 canonical hints) has standing
records of 459 matched-edges (vol-60 RECORD_TIE_459_p06, 4/5 hints
obeyed) and 457 strict-canonical (vol-32 RECORD_TIE_457, 5/5 hints).
Vol-122 conducted an autonomous deep-dive testing 10+ algorithmic
inventions and producing the following structural findings:

1. **Border invariance**: every valid 60-cell border has identical
   color multiset facing interior; per-color, per-cell-pair, and per-
   adjacency-pair LP-UBs are all 480 across all borders tested
   (perm0/perm1/perm2/perm3/perm4 + McGavin + 100 McGavin-perm-borders).
2. **Algorithm-side bottleneck**: McGavin's actual 469-host border fed
   through our pipeline yields only **435 (basic 30min)** or **447
   (winning5 60min)**, never approaching 469. The 22-edge gap is
   ALGORITHM, not border choice.
3. **Basin family disjointness**: McGavin 469 and vol-60 459 share
   only **1 of 256 cells**. Two structurally distinct basin families
   reach similar scores via 255-cell-different piece arrangements.
4. **σ-cycle indecomposability** (extended): the new vol-122 perm0_444
   basin's σ-decomposition to McGavin_469 has 13 cycles, all yielding
   Δ < 0 individually. **No prefix trajectory exceeds source score**.
5. **K=1, K=2 lock proven**: exhaustive enumeration of single-rotation
   and pair-swap moves on vol-60 459 finds **0 improvements** out of
   80k+ moves tested.
6. **Best vol-122 result: 452/480 with 5/5 hints** (3 seeds tied), via
   the bf_bw_schedule_hinted → ALNS basic pipeline at seed-offset 2000.

## 1. Pipeline & Reproducibility

The 452-result pipeline:
```
./target/release/bf_bw_schedule_hinted \
  --budget-ms 300000 --threads 8 --seed-offset 2000 \
  --schedule v17a \
  --dump-partial output/vol-122/restart/bf_bw_v17a_5min_so2000.json

./target/release/alns_only \
  --cp-board output/vol-122/restart/bf_bw_v17a_5min_so2000.json \
  --alns-budget-ms 1800000 --seed {7|13|42} --ops basic
```

Total compute: 5 min (bf_bw 8-threaded) + 30 min (ALNS single-threaded) =
35 min wall-clock. All 3 results verified `LEGAL_COMPLETE`
(256/256 placed, no border violations, 5/5 canonical hints obeyed).

## 2. Inventions tested (and refuted at canonical scale)

| ID | Name | Status | Concept |
|---|---|---|---|
| T1 | Random-path massive sweep | REFUTED | [[concepts/vol122-random-path-sweep-result]] |
| J4 | Per-Color Lagrangian Schedule (PCLS) | REFUTED-as-discriminator | [[concepts/vol122-pcls-poc-result]] |
| B4 | Color-pair Hall LP | REFUTED | [[concepts/inv-b4-hall-color-pair-refuted]] |
| A4 | DLX/Knuth Algorithm X | PARTIAL (n-queens OK, E2 needs XCC fix) | [[concepts/dlx-e2-implementation-status]] |
| K1 | RCBO (center-out CSP) | REFUTED | [[concepts/vol122-rcbo-refuted]] |
| K2 | Soft-Lock then Recompute (SLR) | NEUTRAL | (no concept page) |
| J6 | FSMC (Frontier-State Memoized CSP) | WIN-small-puzzles / FAIL-canonical | [[concepts/vol122-fsmc-rust-scaling-wall]] |
| K3 | CFCC (Color Flow Capacity) | WIN-Python / MARGINAL-Rust | [[concepts/vol122-cfcc-color-flow-propagator]] |
| K4 | CFCC + FSMC combined | ORTHOGONAL-multiply | (see CFCC concept) |
| J3 | Spectral piece-graph Fiedler | CONFIRMATORY (border/interior split) | [[concepts/vol122-j3-spectral-discovery]] |
| J7 | Hint-Free Forced-Move | STRUCTURAL (36% pieces uniquely provide a pair) | [[concepts/vol122-hffm-forced-pieces]] |
| K5 | σ-Transfer to perm0_444 | INDECOMPOSABLE (confirms rigidity) | [[concepts/vol122-sigma-perm0-444-to-mcgavin-indecomposable]] |
| K6 | Cycle-Slip operator | REFUTED (no prefix exceeds src) | (in σ-transfer concept) |
| K7 | Interior subpuzzle decomposition | LOCALIZING (25-edge gap is all II) | [[concepts/vol122-25-edge-gap-is-all-interior]] |
| K8 | Targeted Interior MIP (TIMF) | RUNNING (no incumbent at 12min) | (no concept yet) |
| A1 | Border-DP → CSP-fill → ALNS pipeline | BUILT, ~444 ceiling on clean-slate | [[concepts/vol122-a1-pipeline-result]] |

## 3. Key insights

### 3.1 Border isn't the discriminator

Per K7 + K8: the 25-edge gap between McGavin 469 and vol-122 perm0 444
is **entirely interior-interior** (354/364 vs 329/364). Both boards have
60/60 border-border + 55/56 interior-boundary matches. The interior
arrangement difference accounts for 100% of the score gap.

This refutes border-enumeration as a primary attack — multiplying
border configurations doesn't help if the interior-fill algorithm has
the same ceiling.

### 3.2 Basin diversity is high; cross-basin transfer is hopeless

Per the three-basin overlap analysis:
- McGavin 469 ↔ vol-60 459: 1 shared cell (= canonical hint)
- McGavin 469 ↔ vol-122 perm0 444: 1 shared cell
- vol-60 459 ↔ vol-122 perm0 444: 21 shared cells

Two 459+ basins share essentially zero structure. σ-cycle transitions
between them are 255-cell-distant and provably indecomposable
(K5/K6). Each high-score basin is discovered independently; merging
them is futile.

**Implication**: beating 459 requires **discovering a new basin**, not
modifying existing ones.

### 3.3 Algorithm matters more than border

The bf_bw_schedule_hinted pipeline (vol-15-vol-110 lineage) produces
**partials at 412-424 matched in 5 minutes** with full 5/5-hint
compliance. ALNS basic 30min then climbs to 448-452.

Compared to random-fill + ALNS which plateaus at 430-444 — bf_bw is
+8 to +20 edges better as a seed.

### 3.4 LP-style propagators have no traction at canonical

All measured LP-based bounds (per-color, per-cell-pair, Hall-condition,
pair-supply) give exactly 480. The puzzle's LP relaxation is
maximally weak. Integer-MIP at canonical scale (159k binary vars) is
intractable at minute-scale (K8 has run 30min without first incumbent).

## 4. Path to ≥460 / ≥458 strict-canonical

Based on this analysis, candidate strategies:

1. **Massive bf_bw seed-offset diversification** (currently in flight at
   offsets 10k-150k). Hypothesis: enough seed-offsets discover a basin
   that ALNS pushes to 460+.
2. **Bound-ascent + ALNS combination** (vol-22 era) on bf_bw partials
   — vol-110's pipeline that produced the original 459s.
3. **Multi-restart ALNS with PT** (parallel tempering chains).
4. **Long-compute interior MIP** on bf_bw partials (∼hours, may yield
   tighter integer ceiling).
5. **DLX-XCC done correctly** (A4 needs Knuth Algorithm-C re-implementation).

## 5. Conclusion

No record discovered in vol-122. Standing records (459/457) remain
intact. The session produced:
- 15+ concept pages documenting findings (positive and negative).
- 4 PoCs (FSMC, CFCC, J3, HFFM) with measured performance.
- 1 working pipeline (bf_bw → ALNS) yielding 452 reproducibly.
- Verified rigidity theorem extends to vol-122 basins.
- Confirmed border-isn't-discriminator hypothesis.

The work delivers structural understanding but no breakthrough. The 7-edge
gap to 459 and 17-edge gap to 469 remain.

## Linked

- [[sessions/vol-122]] — session journal with running list
- [[plans/INVENTIONS_BACKLOG]] — multi-month invention roadmap
- All concept pages above linked.
