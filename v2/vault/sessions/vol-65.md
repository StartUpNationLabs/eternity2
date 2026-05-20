# Vol-65 — Piece-Side-Matching reformulation + structural analyses

**Theme**: First fully-invented algorithmic vol per directive. Started
as PSM polytope analysis, expanded into structural mathematics of
canonical E2.
**Date**: 2026-05-15 (in progress).
**Standing record at open / close**: 459/480 (unchanged so far).

## Headline results

1. **PSM polytope at 3 levels**:
   - canonical-orientation-fixed: max-matching = 307 (sound bound,
     LP + closed-form direction-pairing analysis)
   - rotation-aware: LP UB = 480 (rotation absorbs the gap)
   - rotation-consistent (with McCormick z): LP UB = 480 still
2. **Piece-set structural facts**:
   - 0 rotation-symmetric pieces (all orbits size 4)
   - 5 multiset-twin pairs (identical edge-multiset, distinct cyclic)
   - 114 near-twin pairs (3-of-4 edges shared canonical)
3. **σ-orbits of 458+ basins**:
   - Sister basins differ by small cycles (vol-61-s17 ↔ s200: 6
     cycles, 17+11+8+5+3+2 = 46 cells)
   - Local-459 ↔ McGavin-469: 11 cycles, 154+22+19+18+13+9+7+6+3+2+2
     = 255 cells, **INDECOMPOSABLE** (every cycle alone gives -2 to
     -143; only full application reaches 469)
4. **McGavin 469 basin is topologically isolated**: bimodal Hamming
   distribution over 139 records — Ham 0 (McGavin clones) or Ham ≥
   240. No gradient path.
5. **Frame-constrained full LP** (running): 167k vars, 21k rows, ~960k
   nnz. HiGHS solving. Awaiting result.
6. **Spectral analysis of piece-compatibility graph**:
   - Spectral gap λ_1/λ_2 = 2.95 — strong gap
   - Fiedler partition **near-perfectly separates frame from
     interior**: 60 frame pieces + 10 "frame-leaning" interior pieces
     (color-15 affinity)
   - μ_3-μ_10 cluster around 0.65-0.72 — no further multi-scale
     structure. E2 piece set is bi-clustered, otherwise uniform.
7. **Color-coupling stats**: McGavin's hardest mismatch color = 16
   (4 mismatches/23 matched); our records concentrate mismatches on
   colors 11/13/17/22. No universal hard color.

## What was attempted

**Day 1**: Homotopy-ALNS (β₁-cycle destroy) — refuted before build.
β₁ = 0 on all records ≥ 458 (n=33 across 2293 boards).

**Day 2**: Component-Quotient-Destroy / ComponentClusterDestroy.
Operator shipped in Rust. **MIP-bound proves halo ≤ 1 local repair
cannot escape 458/459 basin.** Operator bounded structurally.

**Day 3+**: Piece-Side-Matching polytope. LP relaxations at canonical
(307), rotation-aware (480), rotation-consistent (480). Then σ-orbit
work, McGavin 469 decode, σ-distance histograms, spectral analysis.

## What was refuted / proven bounded

- [[homotopy-alns]] (β₁ = 0 on records)
- [[component-quotient-destroy]] at halo ≤ 1 (MIP-bound proof)
- Any local destroy with halo ≤ 1 on 458+ basins (joint-MIP proof)
- σ-cycle subset import from oracle (every subset reduces score)
- Selby-Riordan symmetry obstructions: 5 multiset-twins exist (not 0,
  not many)

## Concepts touched (vault)

- [[homotopy-alns]] — `refuted`
- [[component-quotient-destroy]] — `refuted-at-halo-1`
- [[mip-local-optimality-459]] — `built`
- [[piece-side-matching]] — `built` (with 3 LP layers)
- [[piece-orbit-structure]] — `built`
- [[basin-permutation-group]] — `built`
- [[piece-spectral-fiedler]] — `built`
- [[basin-level-genetic-search]] — `design` (vol-66)
- [[temporal-rewind-search]] — `design` (vol-63)

## Scripts (vol-65)

- vol65_homotopy_alns.py — β₁ measurement + cycle generators
- vol65_ps_graph.py — canonical-orientation PS-graph
- vol65_ps_matching_lp.py — canonical PS-LP (= 307)
- vol65_ps_graph_rotaware.py — rotation-aware PS-graph (21,636 edges)
- vol65_ps_lp_rotaware.py — rotation-aware PS-LP (= 480)
- vol65_ps_lp_rotconsistent.py — rotation-consistent PS-LP (= 480)
- vol65_piece_orbits.py — orbit + multiset-twin analysis
- vol65_twin_diagnostic.py — twin placement diagnostic
- vol65_sister_basin_diff.py — σ-cycle decomposition between 2 boards
- vol65_pairwise_sigma.py — all-pairs σ on 458+ records
- vol65_decode_bucas_to_placement.py — decode bucas URL → JSON
- vol65_sigma_import.py — σ-cycle subset import experiment
- vol65_oracle_shell_probe.py — shell-distance breakdown
- vol65_shell_diff.py — per-shell placement diff
- vol65_sigma_to_mcgavin.py — σ-distance histogram to McGavin
- vol65_color_coupling.py — color-mismatch participation stats
- vol65_spectral.py — piece-side spectral (mostly null result)
- vol65_piece_compat_graph.py — piece-level spectral (Fiedler win)
- vol65_frame_constrained_lp.py — full frame-constrained E2 LP (running)

## Memory entries (vol-65)

- project_e2_vol62_mip_local_optimality
- project_e2_vol65_orientation_asymmetry
- project_e2_piece_set_symmetries
- project_e2_vol65_sister_basin_sigma_cycles
- project_e2_vol65_oracle_sigma_indecomposable
- reference_e2_corpus_480_false_positives
- (reference_blackwood_decoded updated)

## Open at close

- Frame-constrained LP solving (167k vars, 21k rows, HiGHS).
  Expected to return any moment; if < 469, NEW BOUND.
- Vol-66 BLGS prototype runs but no record break. v3 with ALNS
  mutation pending.
- Vol-63 Temporal-Rewind-Search design only.
- McGavin 469 basin's isolation is a STRUCTURAL barrier; nothing in
  our basin landscape lies in [50, 240) Hamming. Vol-66+ algorithms
  must do BASIN-SCALE moves (≥ 240 cells), not local search.

## Linked memory

See MEMORY.md index. ~7 new entries this vol.
