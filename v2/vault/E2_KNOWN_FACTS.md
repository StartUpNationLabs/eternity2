# Eternity II (canonical 5-clue) — Known Facts (as of 2026-05-15)

## Records

- **480/480**: theoretical perfect. None achieved on canonical 5-clue
  by anyone in any public source.
- **469/480**: community ceiling, Peter McGavin 2020-09-09 via
  Joshua Blackwood's solver. Verified canonical. Stored at
  `output/vol-65/mcgavin_469.json`.
- **459/480**: our pipeline's ceiling (autonomous research,
  vol-60). Local board: `output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json`.

**Unique 469 boards on canonical E2 in our corpus: 2.**
1. McGavin's original.
2. NEW (vol-68): pieces 234↔235 swap at positions 73↔75 of McGavin.

## Structural properties of canonical E2 (vol-65, vol-68)

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

### Bounds

- **Canonical-orientation max-matching**: 307 (vol-65 PSM polytope,
  closed-form min(E_c, W_c) + min(N_c, S_c)).
- **Rotation-aware LP**: 480 (rotation absorbs canonical 307 gap).
- **Per-color budget** Σ ⌊N_c/2⌋ = 480 (no slack — Selby-Riordan tight).
- **NS-1 Δ-invariant** (Hopfer 2022): 469 → Δ=1; 459 → Δ=2; 458 → Δ=3-4.
  Δ=0 needed for 480. Correlates with score.

### Basin structure

- **MIP-locally-optimal at halo-1**: all 4 tested 458/459 records
  are joint-MIP-optimal at halo-1 (no local op with halo ≤ 1 can
  escape).
- **47 distinct basin-components** in 135 unique 455+ records
  (Hamming<100 connectivity). McGavin = size 1.
- **McGavin isolated**: min Hamming from any non-McGavin record to
  McGavin = 247.
- **σ-cycle indecomposability**: 459 → McGavin 469 transition is
  11 cycles spanning 255 cells; every subset application reduces
  score (no smooth path).

### Spectral structure

- **Piece-compatibility graph**: spectral gap λ_1/λ_2 = 2.95.
  Fiedler vector near-perfectly separates frame from interior
  (10 "frame-leaning" interior pieces with color-15 affinity).
- **No multi-scale structure** beyond the frame/interior split.

### Topological structure

- **Vacuous**: 16×16 grid is contractible; H¹ = 0; no obstruction
  cocycle. Hardness is purely combinatorial.

## Algorithm landscape

### Refuted / bounded approaches

- **Homotopy-ALNS** (β₁-cycle destroy): β₁ = 0 on all records ≥ 458,
  no cycles to destroy.
- **ComponentClusterDestroy** (halo ≤ 1): joint-MIP bound at 458/459.
- **σ-cycle subset import** from oracle: every subset reduces score.
- **N-row pinning** from McGavin: only N=14 reconstructs his 469;
  other basins don't show this threshold.
- **Top-row pinning alone**: gives 400/480 in our ALNS.
- **CAS (Concentric Annular Solving)** greedy: 433/480. Bound is
  piece-availability for inner shells once greedy locks pieces,
  NOT edge-coverage (full audit: all 480 edges in objective).
- **CAS-hybrid + ALNS**: 418/480 (worse than CAS alone).
- **CAS + ALNS-refine**: 437-439 (+4-6 only).
- **Vol-22 bound-ascent basins**: relaxed_bound not sound; actual
  ALNS-reachable scores 411-442.
- **Blackwood-then-CSP**: 304/480 (Blackwood-RAW infeasible for joe_csp).
- **Spectral clustering**: bi-clustered only (frame vs interior).
- **Single & double near-twin swaps on McGavin**: max 469 (one new
  swap, no 470).

### Operating algorithms

- **Standard ALNS pipeline** (winning5, 5min, multiple seeds): 459
  ceiling. 47 basin-components reached over time.
- **vanilla_path border-first scan**: +11 free score vs row-major.

### Designed but untested invented algorithms

- Vol-63: **Temporal-Rewind-Search** (revisit past states)
- Vol-67: **Forced-Component-Departure ALNS** (basin-aware)
- Vol-69: **Oracle-Attracted ALNS** (Hamming-to-oracle in objective)
- Vol-70: **Rigidity-Guided Search** (refined, refuted)

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
   (McGavin's + near-twin swap). The orbit is non-trivial.
6. **Selby-Riordan generator is maximally adversarial**: 7+
   independent structural axes all maxed out.

## Files of interest

- `output/vol-65/mcgavin_469.json` — decoded McGavin 469
- `output/vol-68/NEW_469_BOARDS/NEW_469_swap_pieces_234_235_at_pos_73_75.json` — NEW 469 (Hamming 2 to McGavin)
- `output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json` — local 459
- `output/vol-67/components_db.json` — 47 basin-component reps
- `output/vol-71/pair_neighbor_freq.npz` — piece-pair neighbor frequency matrix
- `output/vol-74/cas_full_fixed_solution.json` — CAS result (433/480)
- `output/vol-76/frame_solution_*.json` — enumerated 60/60 frames

## Open challenges

1. **Find another 469 in a different basin family** — currently
   the only known 469 family is McGavin's (with the +1 near-twin
   variant). Are there independent 469s reachable from different
   starting positions?
2. **Find 470** — requires structurally novel approach. Vol-68
   double-near-twin-swap on McGavin: max 468.
3. **Sound LP bound below 480** — current best LP bound is 480
   (trivial). A sound bound below 469 would be publishable.

---

**Standing as of session-2 end (2026-05-15 23:00)**:
- Record: 459/480 unchanged.
- Maximally-adversarial thesis: stands across ~20 axes.
- Genuinely new algorithms invented this session: 5+ (Homotopy-ALNS,
  ComponentClusterDestroy, BLGS, FCD, OA-ALNS, RGS, TRS, CAS).
- All bounded below 459 except CAS-shell-0-2 perfect at 252/252 outer.
