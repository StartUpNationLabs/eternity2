# Vol-35 — fitness landscape mapping + 457-cluster structure

**Theme**: Mapped the local-optimum landscape (FDC, basin diversity,
bound-recoverability) using vanilla_fast as the fast probe. Tested
record-break via deep family-lottery on highest-bound family.

**Raw**: `archive/raw/RESEARCH_NOTES_35.md` (not present — vol used
multiple compact session notes instead: [[vol-35-color-ratio]],
[[vol-35-t1b-family-lottery]], [[vol-35-basin-family-count]],
[[vol-35-throughput-clarification]], [[vol-35-457-basin-geometry]],
[[vol-35-progress]]).

## What was attempted

- T1a: thread-id-offset sweep on vanilla_fast (offsets 0-450 × 8
  threads × 5min) to discover basin families.
- T1b: 1-seed × 60s ALNS lottery on each discovered family.
- T1c: deep ALNS lottery on highest-bound family (12 seeds × 4
  ops × 3min on family 255, bound=463).
- T2: color-ratio scaling experiment (4×4 to 16×16 at canonical
  pp/c ratio).
- T3: pairwise Hamming and consensus-core analysis on 5 distinct
  cold-start 457 cluster reps.
- T4: edge_relax bounds on the 5 cluster reps.
- T5: greedy bound-ascent on cluster B (bound=465).
- T6: vanilla_fast performance verification (confirmed 124.7M pp/s
  single-thread, no regression — earlier sub-30M reading was CPU
  contention from concurrent probes).

## What was measured / kept

- **46 productive thread_ids** discovered in vanilla_fast sweep
  {0..457} — vs 5 from default {0..7}. Basin diversity scales
  approximately linearly with sweep offset coverage.
- **5 distinct 457 cluster attractors** confirmed via pairwise
  Hamming. Mean H=224/256 between clusters; min H=53 (sister-pair
  blackwood s7/s10).
- **Cluster bounds** (edge_relax) ranging 462-465, with cluster B
  highest at 465 (+8 gap above 457).
- **Cross-cluster consensus** = exactly the 5 canonical hints.
  Confirms [[../../../../Users/raphaelanjou/.claude/projects/-Users-raphaelanjou-Documents-dev-projects-polytech-eternity2-v2/memory/project_e2_vol20_backbone_correction.md|vol-20]] on a fresh sample.
- **Deep family-255 lottery**: 3 seeds hit 457 across 2 ops
  presets out of 48 runs. Robust 457 attractor, no 458.
- **vanilla_fast throughput**: 124.7M pp/s single-thread, 122.5M
  pp/s for `vanilla_fastest` (unsafe variant — LLVM at ceiling).
- 7th distinct 457 board saved (vol-35 family-255 deep, byte-
  identical to vol-35 60s family-255).

## What was refuted

- **Color-ratio hypothesis** (user-proposed): FDC at canonical
  pp/c ratio (8×8/5c, 10×10/8c) does NOT improve over off-ratio.
  FDC=-0.086 at 10×10/8c vs ≈0 at 8×8/5c. Size, not ratio, drives
  landscape structure.
- **Cross-basin consensus structure beyond hints**: only the 5
  canonical hint cells agree across 5 distinct 457 cluster reps.
  No usable structural backbone for pre-commit.
- **Family-lottery saturation at 457**: deep lottery (48 runs ×
  3min × 4 ops presets) on family 255 (bound=463, +6 gap) caps
  at 457. ALNS recovery on this family cannot close the gap.
- **Greedy bound-ascent without recovery-tooling**: reproduces
  vol-22 — can reach bound=470 in 165s, but score collapses to
  78. No path from bound-470 to score-458 without a McGavin-style
  prune-restart that retains basin context.

## Concepts touched

- [[basins/basin-457-pt]] — refined to 5+ distinct cluster
  attractors (was 1 in vol-20 memory).
- [[bound-ascent]] — second reproduction of vol-22's
  "high-bound-then-recovery-collapse" pattern. Marks the
  open question as "build McGavin-style recovery, not more
  bound-walks".
- [[fitness-distance-correlation]] — measured at 5 sizes; weak
  signal at all scales (FDC ∈ [-0.105, +0.084]).
- [[basin-family]] — established that vanilla_fast thread-id-offset
  is a primitive for family discovery; 46 families found vs 5
  default.

## Open at close

1. **Cluster B (bound=465) deep lottery untested**. Family 255 was
   chosen for T1c by bound=463. Cluster B's 457 has bound=465 (+2)
   and is from vol-32 blackwood — different ALNS path entirely.
   Worth a deep lottery on the partial that produced B's 457.
2. **McGavin-style prune-restart** still unshipped. The
   bound-ascent finding (vol-22 + vol-35) keeps pointing at it.
3. **Higher-offset sweeps** {500..900}. 46 families found in
   {0..457} suggests another 50+ in unexplored ranges.
4. **ML revisit with cluster-aware seeding**. Vol-29's imitation
   ceiling result used distribution-matched training from canonical
   trajectories. Train on cluster-A vs cluster-B traces separately
   to see if there's a per-cluster ML lift.

## Records ledger (verify_records.sh)

| score | source | verified |
|---:|---|---|
| 458 | vol-32 vanilla_fast → ALNS | ✓ |
| 457 | vol-32 blackwood_mrv seed 7 | ✓ |
| 457 | vol-32 blackwood_mrv seed 10 | ✓ |
| 457 | vol-32 blackwood_mrv seed 4 (30min) | ✓ |
| 457 | vol-34 t1signal seed 1 | ✓ |
| 457 | vol-34 t3 t01 seed 1 | ✓ |
| 457 | vol-35 family-255 seed 1 | ✓ |
| 457 | vol-35 family-255 deep seed 1 (byte-dup) | ✓ |

PASS=8/8.

## Linked memory

- `project_e2_vol20_operator_lock.md` — corrected: cold-start 457s
  are NOT all byte-identical; 5 distinct clusters at H≥246.
- `project_e2_vol22_basin_escape.md` — reproduced (greedy bound-ascent
  reaches 470, score collapses, ALNS recovery gap holds).
- `project_e2_vol32_blackwood_mrv_456.md` — vol-32 record still stands.
