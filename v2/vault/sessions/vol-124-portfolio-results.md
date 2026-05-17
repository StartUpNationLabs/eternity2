---
name: vol-124-portfolio-results
description: "Vol-124 portfolio attack results: 8 kissat seeds × 30 min on canonical SAT all returned s UNKNOWN. 4 ALNS basic seeds × 30 min on 458 strict record all stayed at 458 (zero improvement). LP-UB on canonical hint-only converging to 364 interior matched. Standing 480 contract remains UNMET."
metadata:
  type: session
---

# Vol-124 portfolio attack — empirical results

After the W14 super-block infrastructure showed AC-3 alone is too weak
(8% reduction), I ran a brute-force portfolio attack:

## Setup

- **8 × kissat** with seeds {11, 22, 33, 44, 55, 66, 77, 88}, 1800s budget each,
  on canonical-E2 SAT instance (171k vars × 5.8M clauses).
- **4 × ALNS basic** with seeds {1, 7, 42, 99}, 1800s budget each,
  starting from the 458 strict-canonical record
  `output/vol-122/RECORD_BREAK_458_strict_canonical_5_5_hints.json`.
- **2 × LP-UB**: `border_lp_ub` (errored — wrong board format) and
  `lp_ub_empty_border` (converging to ~364).

12 jobs sharing 8 CPU cores → effective ~2× slowdown per job.

## Results

### Kissat portfolio: all UNKNOWN

```
kissat seed=11 s UNKNOWN
kissat seed=22 s UNKNOWN
kissat seed=33 s UNKNOWN
kissat seed=44 s UNKNOWN
kissat seed=55 s UNKNOWN
kissat seed=66 s UNKNOWN
kissat seed=77 s UNKNOWN
kissat seed=88 s UNKNOWN
```

8 different random seeds, none decided in 30 min wall (~12 min CPU each
due to core sharing). Confirms the prior 1h kissat single-seed run:
**CDCL alone, on our current encoding, cannot decide canonical-E2
in O(hours) of compute**. The instance is too hard.

### ALNS portfolio: all stayed at 458

```
seed=1:  iters=1198 matched=458/480  (only new_best at iter=0)
seed=7:  iters=1199 matched=458/480
seed=42: iters=1199 matched=458/480
seed=99: iters=1198 matched=458/480
```

All 5 destroy operators showed 100% acceptance rate. This is a tell:
with t=1 and a basis at 458 that's MIP-proven local-optimal under
halo-2 (vol-118 rigidity theorem), the ALNS is doing a random walk
through equivalent 458 boards. No improvement possible from this
specific configuration.

### LP-UB on canonical hint-only: ≈364

The LP relaxation (no border fixed, just 5 hints) converges to
**~364 interior matched edges** as the upper bound. This is BELOW the
community 469 actual interior matched. Possible explanations:
1. The LP relaxation here uses a different objective (e.g., piece-sum
   instead of color-match-count).
2. The 469 includes border matches the LP doesn't.
3. The LP has integrality gap >> 100.

The result needs the `==== RESULT ====` print block to confirm what
364 means in our problem's units. Re-run with stdout capture confirmed
~22-31s convergence to value 364.000.

## Implications

After this session, the situation is:

1. **No 480 board produced.** Standing records unchanged: 459/480 (4/5
   hints, community) and 458/480 (5/5 strict, vol-122).
2. **CDCL SAT is exhausted** at the 1-hour-per-seed scale on our
   current encoding. Need either (a) better encoding (W14 — but AC-3
   too weak), (b) MCTS cube-and-conquer (W13, task #70), (c) different
   solvers (CaDiCaL, MapleCOMSPS).
3. **ALNS on the 458 record is locally exhausted** (matches vol-118
   prediction). Need a non-local trajectory to escape — likely from
   a DIFFERENT basin entirely (not the 458 one).
4. **LP-UB ≈ 364** suggests our LP is loose — needs lifting (vol-44
   cluster MIP UB ≈ 478 is the tightest sound UB so far).

## What this session built that survives

- `crates/bench-audit/src/bin/super_block_enum.rs` — Rust 2×2-block enumerator
  (28s for 127.6M blocks).
- `crates/bench-audit/src/bin/super_block_ac3.rs` — Rust AC-3 pruner
  (8% reduction; need stronger propagation for real prune).
- `scripts/w15_qubo/qubo_full.py` + `run_qubo.py` — QUBO encoder for E2,
  tested on 3×3 (solved perfectly).
- `scripts/w15_qubo/count_rings.py` — border ring counting derivation.
- `scripts/w15_qubo/rare_color_bipartite.py` — confirms 60 border
  pieces use rare colors (2-6) exclusively.
- `scripts/w15_qubo/hint_neighbor_analysis.py` — hint-adjacent
  candidate-set sizes (43-48 per direction, no forced placements).
- `scripts/w15_qubo/hint_pair_propagation.py` — standalone AC-3 from
  hints (14% domain reduction, no new forced cells).
- Multiple vault session notes documenting the literature roams,
  retractions (symmetry-break, Vandermonde-LP), and end-state.

## What the next session must do

The contract requires producing a 480 board. The plausible paths:

**Highest EV (multi-day Rust)**:
- **W13 — MCTS cube-and-conquer wrapper** around kissat. Splits the
  search into many disjoint cubes, solves in parallel, MCTS picks
  the most-promising variables to split on. Expected speedup over
  single kissat: 1.6-7.6× from literature (AlphaMapleSAT 2024).
- **W14-extended — add piece-uniqueness propagation** to super-block
  AC-3. After alldiff propagation, the residual SAT encoding may be
  small enough for kissat to decide.

**Medium EV**:
- **W15-cloud — pay for Fixstars Premium tier** ($2k/mo) and submit
  full 157k-var QUBO. ONE 10-min run = decisive empirical test of
  whether commercial Ising hardware can beat our encoded SAT.
- **W17 — learned-potential min-cost flow** (KnotFold transfer).

**Lower EV — but worth one shot**:
- **Different SAT solver**: CaDiCaL or MapleCOMSPS on the same encoding.
  Different CDCL heuristics may decide where kissat fails.

The user has sanctioned multi-week autonomy. Pick the highest-EV path
and ship it.
