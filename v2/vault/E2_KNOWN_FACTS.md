# Eternity II (canonical 5-clue) — Known Facts (as of vol-213, 2026-06-10)

## Records

- **480/480**: theoretical perfect. None achieved on canonical 5-clue
  by anyone in any public source.
- **469/480**: community ceiling, Peter McGavin 2020-09-09 via
  Joshua Blackwood's solver. Verified canonical. Stored at
  `output/vol-65/mcgavin_469.json`.
- **460/480 [strict-canonical 5/5 hints], COMMUNITY**: groups.io thread
  "Highest points (of 480) with using all 5 (!) hints?" (2023-03) —
  McGavin 460 + "P=NP" 460, both verified LEGAL_COMPLETE 5/5
  (vol-211 decode: `output/vol-211/corpus_decoded_*/groups_2193*_460.json`,
  II=350 + IB=50 + BB=60). **Strict-track record target: 461.**
- **463/480**: **our matched-edges record** (vol-129 PALIMPSEST,
  cp=(2,3,0,1), 15-basin attack on (2,3,0,1)@462 base).
- **458/480** [strict-canonical 5/5 hints]: our strict-canonical
  record for ORIGINAL boards (vol-122; vol-199 second basin; vol-213
  witness-derived third basin). [The old "459 strict" was INVALIDATED
  by the V199 dup-piece audit.] **Vol-213: both community strict-460s
  are now exactly RE-CONSTRUCTIBLE by our engine** (REPLAY + double-
  break + et-cap, [[replay-prior-over-cost]]) — 460 reproduced ≠ 460
  original; the original-board strict target stays 461.
- ★★ **Community strict-460s contain 4-5 DOUBLE-BREAK cells** (one
  cell paying 2 mismatches at placement, row-major attribution) —
  violate-≤1 break-DFS provably cannot reach them (vol-213).
- **Standalone 14×14 interior (II/364)**: best in any known board:
  **358** (Blackwood+Bucas 469_c, 2020-11). Hinted-5/5 boards: 350.
  Our CLOISTER vol-211: 356 unhinted / 350 hinted (see
  [[cloister-standalone-interior]]).

**Unique 469 boards on canonical E2 in our corpus**: 2.
1. McGavin's original.
2. NEW (vol-68): pieces 234↔235 swap at positions 73↔75 of McGavin.

## Three-basin iso-plateau (vol-185–188)

All three of these basins are structurally locked at their score level
under every local operator we have:

| Basin | Score | Corner perm | Discovery |
|---|---:|---|---|
| local-459 (a.k.a. vol-60 p06) | 459 | (1,0,2,3) | vol-60 |
| V175 458-new | 458 | (3,0,1,2) | vol-175 |
| V181 460-new | 460 | (0,3,1,2) | vol-181 |
| V125 461 | 461 | (1,2,0,3) | vol-125 |
| V129 463 | 463 | (2,3,0,1) | vol-129 |
| McGavin 469 | 469 | (3,2,0,1) | community 2020 |

V181 460 specifically has been **MIP-proven rigid** across 4 distinct
32-cell regions (vol-187 INTAGLIO-MIP) plus 1/2/3-row joint swap rigid
(vol-186), plus 1h-ALNS no-lift, plus σ-transport to McGavin
INDECOMPOSABLE (vol-188).

## Structural properties of canonical E2

### Piece set

- 256 pieces, all distinct.
- 4 corner pieces (2 border sides each).
- 56 edge pieces (1 border side each).
- 196 interior pieces.
- 22 non-border colors.

### Symmetries

- **0 rotation-symmetric pieces** (all orbits size 4).
- **5 multiset-twin pairs** (10 pieces): (2,3), (5,14), (7,51),
  (109,110), (171,181). Share edge-color multiset but distinct
  cyclic order.
- **114 near-twin piece-pairs** (3 of 4 canonical edges shared).
- **NO board-level symmetries** on canonical 5-clue E2 — hints
  break all reflections/rotations. Symmetry-breaking is NOT
  a valid search-space-reduction angle (binding feedback).

### Bounds

- **Canonical-orientation max-matching**: 307 (vol-65 PSM polytope,
  closed-form min(E_c, W_c) + min(N_c, S_c)).
- **Rotation-aware LP**: 480 (rotation absorbs canonical 307 gap).
- **Per-color budget** Σ ⌊N_c/2⌋ = 480 (no slack — Selby-Riordan tight).
- **NS-1 Δ-invariant** (Hopfer 2022): 469 → Δ=1; 459 → Δ=2; 458 → Δ=3-4.
  Δ=0 needed for 480. Correlates with score.
- **Top-4 rows on local-459**: ≤ 123 (vol-86 sound subset-UB).
- **3-row band LP-UB on V181 460** (rows 13-15, vol-187): UB ≈ 95.4,
  MIP-optimal ≤ 83 — LP slack, but no integer lift.

### Basin structure

- **MIP-locally-optimal at halo-2**: all tested 458/459/460/461 records.
- **47 distinct basin-components** in 135 unique 455+ records
  (Hamming<100 connectivity). McGavin = size 1.
- **McGavin isolated**: min Hamming from any non-McGavin record to
  McGavin = 247.
- **σ-cycle indecomposability**: now confirmed across **3 basin pairs**
  (vol-65 local-459↔McGavin, vol-99 sister-458↔sister-458, vol-188
  V181-460↔McGavin). Every proper subset of cycles reduces score.
- **K11 signatures** (vol-122): λ_2 + mz separate basins; HINT-RIGIDITY
  trade-off discovered.
- **INTAGLIO 2x2 finding** (vol-180): 99.72% random 2x2 patches are
  FORBIDDEN; HIGH boards have ~29 forbidden patches; 480 candidates have 0.
- **Corner-perm taxonomy** (vol-129): 18 corner-perm families carry ≥458
  boards in our 1278-board DB. 3 cps have ≥460 (McGavin (3,2,0,1),
  V125 (1,2,0,3), V181 (0,3,1,2)). vol-129 adds V129 (2,3,0,1) → 463.
  15 cps are still unexplored at ≥460 level.

### Row/column rigidity (vol-186)

V181 460 (and McGavin 469) row-locally-rigid: NO valid 16-piece chain
alternative for any row gives ≥ same score. Confirmed 1-row, 2-row,
and 3-row joint swaps all bounded.

### Spectral structure

- **Piece-compatibility graph**: spectral gap λ_1/λ_2 = 2.95.
- Fiedler vector near-perfectly separates frame from interior
  (10 "frame-leaning" interior pieces with color-15 affinity).
- **No multi-scale structure** beyond the frame/interior split.

### Topological structure

- **Vacuous**: 16×16 grid is contractible; H¹ = 0; no obstruction
  cocycle. Hardness is purely combinatorial.

## Algorithm landscape

### Refuted / bounded approaches (selected; see [[concepts/dead-ends]] for full)

- **Homotopy-ALNS** (β₁-cycle destroy): β₁ = 0 on all records ≥ 458.
- **Component-Quotient-Destroy** at halo ≤ 1: joint-MIP bound.
- **σ-cycle subset import** from oracle: every subset reduces score.
- **Bottom-N pinning of McGavin**: 443-462 only (top-N=14 is the line).
- **CAS** (Concentric Annular Solving): 433/480 greedy ceiling.
- **CAS-hybrid + ALNS**: 418/480 (worse).
- **Blackwood-then-CSP**: 304/480 (RAW infeasible for joe_csp).
- **Spectral clustering**: bi-clustered only (frame vs interior).
- **basin-mix MIP at 4 basins** (vol-112): MIP-PROVED optimum = 459.
- **σ-cycle predicts ALNS-lift** (vol-107): partial, weakens at N=6.
- **SigmaCycleDestroy ALNS op**: refuted at vol-108.
- **Beam search** analytically refuted (vol-109).
- **Oracle-aware repair**: graft loses 170 pts.
- **RL via ES**: degrades below imitation baseline (vol-48-49).
- **CHIASMUS basin crossover** (vol-172): refuted as record-mover.
- **SEMAPHORE row-Hungarian** (vol-183): row-10 piece-starvation wall.
- **LIGHTHOUSE bidirectional MERGE** (vol-184): 0 valid pairs.
- **V182 ENGRAVE K∈{2,4} band-fill**: refutes local 460 lift.
- **Naive CDCL at canonical 16×16** (vol-58-59): clause size 96.
- **Kissat on full puzzle SAT** (vol-124): 8×30min ALL UNKNOWN.
- **Single & double near-twin swaps on McGavin** (vol-68): max 469.
- **FPL probe** (V125-T34): basin transport via per-piece pinning INFEASIBLE.
- **FILAMENT result** (vol-130): SA-repair beats FILAMENT-repair.

### Operating algorithms (matched-edges, current pipeline)

- **V155 PRIOR** corpus-prior data-augmented beam — from-scratch 456.
- **V155 → ALNS basic_lkh** pipeline — from-scratch 460.
- **V181 KEYRING** (patch + pheromone + position prior) — 460 in new cp.
- **A1 border-DP + bf_bw + ALNS** — vol-125 461.
- **PALIMPSEST consensus-trap targeting** — vol-129 463.
- **vanilla_path border-first scan**: +11 free score vs row-major.

### Engine performance

- **blackwood-fast**: 85M nps single-thread (232× over solver-engine
  BLACKWOOD_RAW from vol-15). ~28% of Bucas's C single-thread.
- **vanilla-v2**: 97 M pp/s (+33% over vanilla_fastest).
- Engine baseline → vol-114: from 367k nps to 85M nps over the
  106-115 directive.

## Critical empirical facts

1. **McGavin's 469 basin is topologically isolated**. No
   pipeline-reachable basin has Hamming < 247 to him.
2. **Our pipeline can RECONSTRUCT McGavin's 469** given his
   top-14 rows pinned (224/256 pieces). Bottleneck is finding
   those 224 pieces without his algorithm.
3. **Δ-invariant correlates with score**. A search minimizing
   Δ may bias toward high-score basins.
4. **No universal piece-position backbone**. Across 5 high-score
   records (incl McGavin), 0 cells have all-5-agreement, 0 have
   4-of-5, only 5 have 3-of-5.
5. **The 469 score-level set has ≥ 2 distinct configurations**
   (McGavin + near-twin swap). The orbit is non-trivial.
6. **The 458-level set has ≥ 3 distinct basins** with corpus-distance
   ≥ 240 cells (sweep_p18 vs vol-32 vs V175). Vol-119 + vol-175 work.
7. **Selby-Riordan generator is maximally adversarial**: 7+
   independent structural axes all maxed out.
8. **Cross-basin σ-transport is universally indecomposable** at the
   cycle level (3 distinct basin pairs measured).
9. **Three iso-locked basins at 458-460 under all local ops**
   (V175 458, vol-60 459, V181 460). Path to 461+ requires
   non-local / cross-basin / fundamentally new operators.

## Files of interest

- `output/vol-65/mcgavin_469.json` — decoded McGavin 469
- `output/vol-68/NEW_469_BOARDS/NEW_469_swap_pieces_234_235_at_pos_73_75.json` — NEW 469 (Hamming 2 to McGavin)
- `output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json` — local 459
- `output/vol-125/.../RECORD_461_*.json` — V125 461 (cp=(1,2,0,3))
- `output/vol-129/.../RECORD_463_*.json` — V129 463 (cp=(2,3,0,1))
- `output/vol-175/long_lift_20260520T104000/RECORD_458_NEW_BASIN_zigzag_s99.json` — V175 458 (cp=(3,0,1,2))
- `output/vol-181/RECORD_460_NEW_BASIN_row_s42_cp0312.json` — V181 460 (cp=(0,3,1,2))
- `output/vol-67/components_db.json` — 47 basin-component reps
- `output/vol-76/frame_solution_*.json` — enumerated 60/60 frames
- 1278-board record DB: `database-400-480/`

## Open challenges (current as of vol-188)

1. **Find ≥460 in any of 15 unexplored corner-perms** (vol-189 CORTEZ
   binding).
2. **Cross-basin σ-transport between closer basins** — vol-188 measured
   V181 460 ↔ McGavin 469 (gap 9) → indecomposable. Open: V129 463 ↔
   McGavin 469 (gap 6), V125 461 ↔ V129 463 (gap 2).
3. **Non-rectangular MIP regions** on V181 460 (diagonal, L-shape).
4. **4-row MIP** with stronger LP cuts (vol-187 4-row inconclusive at
   30min).
5. **SDP relaxation** for tighter than-LP score bounds.
6. **Multi-week RL self-play** (deferred since vol-30+).
7. **Branch-and-Price-and-Cut** full implementation (vol-52 estimated
   3-4 weeks).

## See also

- [[sessions/TIMELINE]] — vol-1..188 timeline with eras.
- [[SYNTHESIS_VOL_188]] — master synthesis (vol-188 close).
- [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]] — the
  rigidity theorem paper.
- [[REMINDER_USER_DIRECTIVES]] — binding directives.
