# Current vol — vol-108 CLOSED 2026-05-16 ~12:15 CEST

## Vol-108 close summary

**0 positive shipments, 2 honest refutations, 1 "not applicable":**

- T1 ✗ SigmaCycleDestroy ALNS op REFUTED. Built + tested on
  offset=100 partial. The σ-cycle's structural lock comes from
  halo edge-colour constraints, not cycle cells.
- T2 ✗ Fanout-sort value ordering REFUTED. Same trajectory at
  v17a strict, 5% nps regression from cache perturbation.
- T3 ✗ BOLT post-link reordering NOT APPLICABLE on apple-m1
  (Mach-O unsupported; ELF-only).

Collateral fix: vol-18 `compute_sigma_cycles` was crashing on
partial boards; fixed (`sigma.contains_key` check before push).

See [[../sessions/vol-108]] for the consolidated table.

## Engine state (unchanged)

- bf_bw: 84-85 M nps single-thread (PGO+T12+T1).
- vanilla_v2: 97 M pp/s.
- Pipeline reaches 450-451 stably in 7 min.
- Standing record: 459/480 unchanged.

## Vol-109 binding items (≤ 3)

### T1 — Oracle-aware ALNS repair (continuation of vol-108 T1)

Vol-108 T1 found that destroying σ-cycle cells alone doesn't unlock
the basin because the halo's edge colours pin the repair. The fix:
extend `repair_cells` to accept ORACLE PIECE pins for halo positions.
This forces the halo to take the oracle's piece assignment, removing
the structural lock, while the σ-cycle interior is freely repaired
by SA / CP.

Effort: multi-day (modify repair API, plumb through ALNS framework,
test variance). Could unlock the offset=100-style basins.

### T2 — Beam-search engine variant

A NEW search algorithm: maintain top-K partial boards at each depth,
expand each in parallel. Different from DFS — more breadth at low
depths, less depth at high depths. K=8 matches our thread count.
Test on canonical Selby-Riordan: does beam reach a depth/score
inaccessible to 8-thread DFS?

Vol-106 T10 measured 0.8% pairwise agreement across 8 DFS threads.
Beam search SHOULD produce more diverse trajectories at low depths
(since the beam explores ALL top-K from each depth, not just one).

Effort: 1-2 days. Build alongside, don't replace, bf_bw.

### T3 — Cross-machine throughput benchmark

Port bf_bw to a portable build target (cross-compile to
x86_64-unknown-linux-gnu / aarch64-unknown-linux-gnu) and measure
on different hardware. Compare apple-m1 84-85M to intel x86-64 and
M2/M3. Useful both for verifying our optimizations don't apple-m1-
overfit AND for unlocking BOLT (which works on Linux ELF).

Effort: 2-4 hours assuming no cross-compile surprises.

## Audit-at-open compliance

All vol-106-115 directive items still apply: blank-puzzle speedup
+ invention. Score-axis is OUT OF SCOPE.

## Linked

- [[../INDEX]]
- [[../DIRECTIVE_VOLS_106-115_BLANK_PUZZLE_SPEEDUP]]
- [[../sessions/vol-108|vol-108 close]]
- [[../concepts/sigma-cycle-destroy]]
- [[../concepts/fanout-sort-value-order]]
- [[../concepts/blackwood-fast]]
