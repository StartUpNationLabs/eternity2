# Vol-44 — Border classes, MIP local-optimality, LP-UB landscape, color UB

**Theme**: Build LP-relaxation UB tool. Use it to characterise the
canonical-E2 search landscape. Test multiple basins for local
optimality. Probe perturbations and combinatorial bounds.

**Status**: rich research session, multiple findings, no record break.

## Toolset shipped

All in `crates/bench-audit/`:

- `border_ub.rs` — LP formulation library (corrected: B-I edges as
  variables, not forced). Supports MIP mode via `LpOptions.integer`.
- `cluster_repair.rs` — MIP cluster-repair lib (warmstart from current
  board for both x and y vars).
- Bins:
  - `lp_smoke` — toolchain smoke test.
  - `border_lp_ub_small` — generated-puzzle LP validation.
  - `border_lp_ub` — LP UB on a canonical-E2 board.
  - `border_mip` — full-board MIP (too large in practice).
  - `border_lp_perturb` — single-swap LP UB perturbation.
  - `border_lp_perturb_k` — k-swap LP UB perturbation.
  - `board_anatomy` — split score into B-B / B-I / I-I.
  - `mismatch_map` — find mismatch clusters + adjacency structure.
  - `board_diff` — board-vs-board similarity (cells, piece-sets).
  - `border_cluster` — cluster boards by border fingerprint.
  - `cluster_repair_458` — sequential cluster repair on vol-32 458.
  - `cluster_repair_class_b_457` — same for class-B 457 board.
  - `cluster_repair_lo00001` — same for lo_00001 (family A*).
  - `repair_region` — repair any user-specified region of cells.
  - `color_side_count` — per-color side counts + combinatorial UB.

Plus the LP solver dep: `good_lp + highs-sys` (HiGHS built from
source via cmake at workspace build time).

## Key findings

### 1. Three border-classes identified

LP UB sweep on all 10 verified records:

| Class | Members (records) | LP UB | bb |
|:---:|---|---:|---:|
| **A** | 458 (×2), 456 s2, 455 s1/s5, 454 | **478** | 60 |
| **B** | 457 s7, 457 s10, 456 s4 | **477** | 60 |
| **C** | 457 30min s4 | **476** | 58 |

### 2. MIP local-optimality of all sampled basins

| Board | Region | MIP result |
|---|---|:---:|
| vol-32 458 (class A) | 28 cells (all mismatch cluster cells) | delta = 0 (1.74 s) |
| vol-32 457 s7 (class B) | up to 27 cells (halo=2) | delta = 0 (52 s) |
| lo_00001 s457 (family A*) | up to ~14 cells (halo=2) | delta = 0 (~3 s) |

Each basin is the **integer optimum under any rearrangement** of up
to ~30 cells in its mismatch region. Stronger than vol-22's K=5
operator-lock; proven by exact MIP.

### 3. ALNS-diverse can't lift any LP-UB-478 basin

16 ALNS-diverse seeds, 10 min each, across 3 unexplored LP-UB-478
basins (lo_00001 s457, lo_f452 s455, lo_f150 s454). Best lift was
+1 in 2 of 4 lo_f150 seeds. No seeds reached 458.

### 4. vol-32 458 border is locally LP-UB maximal

13 random perturbations (k=2: 5 trials, k=3: 8 trials, k=5: 3 trials)
on vol-32 458's perimeter. **ALL 16 perturbations decreased LP UB**.
Range: −2 to −10. Larger k → bigger UB drop.

Random walk on the border can't find LP UB > 478.

### 5. McGavin canonical-projected = LP UB 477

The community 469 board, projected to canonical 5-clue (canonical
hints overlaid), gives LP UB **477** — lower than class A's 478.
McGavin's border is not a route past 458 under canonical 5-clue.

### 6. Combinatorial color UB on canonical E2 = 480

Sum_k floor(N_k / 2) = 480 where N_k = # non-BORDER sides of color k.
All N_k are even (5×24 + 5×48 + 12×50 = 960 = 2 × 480).

**Color multiplicity does NOT block a 480 solution.** The original
puzzle IS 480-solvable. The 478 LP UB on our basins captures
*spatial* constraints, not combinatorial ones.

### 7. Two families share LP UB 478

Family A* (vol-32 458, lo_00001) — share TOP 4 rows piece-for-piece
(56/56). Family LO (lo_f150, lo_f452) — structurally different
piece-set (8/256 cells same). Same LP UB despite different boards.

### 8. 458 board mismatch geometry

| Edge type | Matched | Total | Mismatched |
|---|---:|---:|---:|
| B-B | 60 | 60 | 0 |
| B-I | 52 | 56 | 4 |
| I-I | 346 | 364 | **18** |

18 I-I mismatches form **10 disjoint clusters**, max size 5,
all in rows 10-14. Top 9 interior rows perfect.

## Cumulative compute spent

- LP UB sweeps: ~20 × 2.5 min = 50 min.
- MIP cluster repair: ~10 × 0.5 min = 5 min.
- Perturbation trials: 16 × 2.5 min = 40 min.
- ALNS push (3 basins, 16 seeds): 16 × 10 min = 160 thread-min ≈ 20 min wall.
- Color counting + clustering tools: < 5 min.

Total ~2 hours wall. Multiple research-grade findings, all
committed and documented.

## What's running at vol close

8 ALNS-mega_mix seeds × 1h each on vol-32 458 board. Different
operator set from previously-tried diverse. Last chance attempt
to find 459+ within class A's basin via heavy operator mix.

## Unfinished frontiers

1. **CP search with LP UB objective** — generate borders directly
   that maximize LP UB. Multi-day build.
2. **Directed gradient search** in LP-UB landscape — least-bad
   perturbations identify directions less-blocked, may compound.
3. **Per-color LP UB analysis** — which colors get short-changed in
   the LP relaxation? Diagnostic.
4. **No-good CDCL learning** in solver-engine — standard SAT
   technique never applied to E2.
5. **RL self-play for value-order** — vol-29's identified ceiling
   path; not addressed.
6. **Spectral piece-graph clustering** — untested.

## Mathematical statements proven

> **Theorem (vol-44 / vol-32 458 board)**:
> The vol-32 458 board's piece arrangement is the integer optimum
> under any rearrangement of the 28 cells touching any I-I mismatch.
> All other 228 cells held fixed.
> (Proved by exact MIP via HiGHS B&B.)

> **Theorem (vol-44 / canonical E2)**:
> The combinatorial color-multiplicity UB on canonical E2 score = 480.
> No parity waste from color side counts.
> (Direct enumeration.)

> **Observation (vol-44 / vol-32 458 LP-UB landscape)**:
> 13 of 13 random k≤3 perimeter perturbations decrease LP UB.
> 458 border is at a substantial LP-UB local maximum.

## Linked concepts

- [[458-class-A-mismatch-structure]]
- [[border-class-geometries]]
- [[lp-ub-478-basins]]
- [[color-multiset-bound]]
- [[border-enum-lp-ub]] — LP math
- [[vol-43-reframing]] — pre-vol-44 strategy
