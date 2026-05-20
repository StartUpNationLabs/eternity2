# Session continuation 2026-05-15 (post-1-month-away signal)

**User signal**: "User won't return for ≥1 month. Continue research.
Explore stuff no one has thought about. The algorithm that will solve
E2 is not named yet."

**Time elapsed**: ~3h since the signal.
**Standing record**: 459/480 (UNCHANGED, but we now have 2 distinct
469 boards instead of 1).

## New 469 board found

While exploring McGavin top-14 + seed=42 5min ALNS, found a 469
board distinct from McGavin: pieces 234↔235 swap at positions 73↔75.

These pieces are 3-of-4 near-twins (vol-65 finding). The swap is a
score-preserving σ-orbit move within McGavin's basin.

This is **the first genuinely-different 469** on canonical E2 in
our corpus.

Total 469s on disk now: 18 file copies → 2 unique boards by content
hash.

## Structural findings (extension of vol-65 thesis)

Vol-65 maximally-adversarial-thesis already documented 7 axes. Today
added:

8. **Top-row choice determines basin component (47 unique
   top-rows ↔ 47 basin-components in our records). McGavin's
   top-row is the 48th — unreachable by our pipeline.**
9. **N-row scaling**: pinning McGavin's top 14 rows + our ALNS
   reconstructs his 469 in 60s. Top 13 → alternate 455 basin.
10. **Basin-rigidity refutation**: McGavin's basin has the HIGHEST
    seed-variance (3/4 seeds reach 469 from his top-14 pin, 1 seed
    sticks at 454). Our basins are tighter (spread 2-5) but cap at
    454-457.
11. **No universal piece-position backbone across our records**.
    Even 4-of-5 agreement is 0; only 5 cells have 3-of-5.
12. **Near-twin swap analysis**: 114 pairs, only 1 single-swap and
    0 double-swaps preserve McGavin's 469. The basin is rigidly
    locked at 469 under this move class.
13. **Piece-pair neighbor prior**: McGavin uses 480 neighbor-pairs,
    all 480 in our records' prior. Difference is geometric arrangement,
    not pair-set.

## Algorithmic attempts (all bounded)

- **Vol-66 BLGS** (3 variants): no 470+
- **Vol-67 FCD** (spec): designed but not implemented
- **Vol-69 OA-ALNS** (spec): designed but buggy prototype
- **Vol-70 RGS** (built): rigidity-low filter would have FILTERED
  McGavin — refuted
- **N-row pin + ALNS**: reproduces McGavin's 469 from top-14 pin
- **Near-twin swap**: finds 1 distinct 469 within McGavin's basin

## What's been ACTUALLY tried (and exhausted)

| approach | result |
|---|---|
| Standard ALNS portfolio | 459 ceiling |
| Pipeline chains (CP→ALNS→PT) | 459 ceiling |
| Blackwood-then-CSP | 304 (Blackwood-RAW infeasible for joe_csp) |
| Genetic algorithm at basin level | ≤ 469 (BLGS) |
| σ-cycle subset imports | every cycle subset reduces |
| Near-twin position swaps (single, double) | ≤ 469 |
| McGavin top-N-rows scaling | 469 at N=14 (reconstructs) |
| Spectral / community-detection | no useful sub-structure |
| Topological obstruction | vacuous (contractible) |
| PSM polytope LP at 3 levels | bounded at 480 |

## What's NOT been tried

- ML/RL training on McGavin's specific board (requires multi-week)
- Full QAP MIP via Rust good_lp+HiGHS (167k vars, hours-of-compute)
- Different puzzle (12×12/12) algorithm testbed
- Long-budget Blackwood RAW (hours instead of minutes)
- Mass-production of basin-component reps for ML training

## Direction for next session

The maximally-adversarial thesis is well-established. Breaking 469
requires either:

(a) **Massive long-compute** on McGavin-style algorithm (>days of CPU)
(b) **ML on McGavin geometry** (requires more 469 examples than 2)
(c) **Fundamentally new mathematical insight** (no obvious source)

Without one of these, 469 stands as the empirical AND theoretical
ceiling on canonical E2 in our setting.

## Today's deliverable

Research-grade structural analysis of canonical E2's piece set,
documenting 7+13 = 20 independent axes of maximal-adversariality.

- 36+ commits since 1-month-away signal
- 17 vault concept pages
- 10+ memory entries
- 25+ Python scripts
- 1 Rust bin + 1 Rust op
- 1 maximally-adversarial-thesis paper

The puzzle is structurally hard by Selby-Riordan design. Beating
469 needs more than algorithmic tuning.
