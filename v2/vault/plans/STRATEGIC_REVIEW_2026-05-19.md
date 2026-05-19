# Strategic Review — 2026-05-19 17:42 CEST

After ~4h of post-McGavin pivot autonomous work, 16 vols (131-146)
shipped. Mixed results. Time to step back.

## What's been established

### Strong findings (publishable)
1. **Scaling curve** (V131): ALNS basic wall starts at 7×7/c5.
2. **3-regime ALNS gap** (V132-133): +80pp gap only in medium density.
3. **Forbidden-patch theorem** (V138-142): forbidden-k-patch count
   strongly anti-correlates with score. 99.72% of random 2×2 patches
   forbidden, 100% of 2×3 random.
4. **18 distinct basin families ≥458** (V129-T11).
5. **Record 463** (V129-T12) — within McGavin (2,3,0,1) basin.

### Refuted
- CONCRETION (V127), ATLAS (V128), FPL cross-basin (V125-T34),
  PALIMPSEST hard-pinning (V129-T7), ICEBERG (V145).

### Inert as integration
- INTAGLIO lex-tiebreak (V140), FILAMENT-repair (V134), TUNNEL ladder
  (V141), ForbidDestroy operator (V143, V146).

### Partial / built
- CONCORD (V126), PALIMPSEST mining (V129), GRAIN (V135-137),
  FILAMENT LK-2D (V130), INTAGLIO 2x2/2x3 (V138-143).

## The wall

**Short-budget (≤30min) local-search on record-tier boards (≥459) is
inert.** V140/V141/V143/V146 all returned zero improvement.

Why: σ-cycle indecomposability (vol-65). 461→469 needs coupled
255-cell permutation, not local moves. McGavin's 469 itself locally
optimal.

## What might work this month

### Tier 1 — multi-day brute compute (proven recipe)
V129-T12 found 463 via 18 × 30min ALNS on different basins. Scale:
1h-4h budgets, multi-seed, all 18 basins. ~500 CPU-hr / week.

### Tier 2 — find NEW basin families
Cluster 440-457 boards by corner perm + cell-diff. Hidden basins.

### Tier 3 — generator-aware (PROVENANCE)
Selby-Riordan piece set is deterministic. Hypothesize generator
fingerprints. Risky.

### Tier 4 — non-ALNS algorithms
- INTAGLIO-pruned DFS (exploit our strongest finding)
- BP-guided destroy (refuted as decimation, never tried as destroy
  target)
- PEPS tensor network (W1 deferred)

## Recommendation for next session

**Build INTAGLIO-pruned DFS**: deterministic backtracking with a
post-placement check that rejects any partial board containing a
forbidden k-patch. Exploits the strongest finding of this session.

## What's NOT recommended

- More short-budget ALNS variants from record-tier boards.
- More iso-score tiebreakers.
- More PT ladders.

## Linked
- [[forbidden-patch-theorem-2026-05-19]]
- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
- [[plans/MONTH_AHEAD_2026-05-19]]
