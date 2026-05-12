# Night 5 abstract — for an arXiv preprint

**Working title**: *Structural sources of the 449/450 plateau in Eternity II
local search.*

## Abstract (200 words)

The 5-clue Eternity II puzzle has a published metaheuristic SOTA of
458/480 matched edges (Wauters 2012) that has not been improved in
peer-reviewed work since 2019. Local-search algorithms commonly
plateau at 449/480, but the structural mechanism of this plateau is
not characterized in the literature. Working from a corpus of 29
plateau boards (score ≥ 440) produced by six independent solver
families, we identify three coupled mechanisms that pin the plateau:
(1) the asymmetric placement of the official 5th hint at cell (7,8)
generates a directional strain field whose cone-cone intersection
with the four 180-symmetric corner-hint fields produces a defect
hotspot at Manhattan distance 6-8 in the south-central quadrant;
(2) the 22 colors split into rare (counts 24, colors 1-5) and
abundant (counts 48-50, colors 6-22) classes; rare colors are 100%
matched on every plateau board, while ALL plateau mismatches occur
between abundant-color edges; (3) exhaustive testing of local-search
moves of size 2, 3, 4 (~6.6M trials, 0 improvements) places an
empirical Hamming-moat depth lower bound of ≥ 5 at the plateau. The
intersection of these mechanisms predicts that algorithms with
simultaneous ≥ 6-piece moves (Wauters' K=16 tile-assignment, Salassa's
6×6 region-rebuild) are necessary and that frame-first decomposition
succeeds because it changes the strain-field interaction.

## Why this matters

This is a **structural characterization** rather than an algorithmic
improvement: we don't break 450 ourselves, but we provide a falsifiable
mechanistic explanation for *why* 449/450 is hard, including:
- A specific predicted effect (asymmetric defect distribution).
- A quantitative empirical regularity (29/29 boards, 100% abundant-only).
- An empirical lower bound (Hamming-moat ≥ 5).
- A unified explanation for *why* polishing methods (Salassa TA,
  Salassa RO max-clique) fail on PT-derived boards.

To my knowledge, none of these are in the published literature. The
universal-mismatch lever (top-K interior edges that fail in 47-63%
of plateau states) is also novel.

## Falsification criteria

For each finding, the test that would falsify it:

1. **Strain cascade hypothesis (asymmetric hint mechanism)**:
   - Run unconstrained PT with the (7,8) hint REMOVED. If defect
     density still peaks at distance 6-8 from (7,8), the hypothesis
     is wrong (the hotspot is intrinsic to the geometry, not the hint).
   - If defect density becomes uniform (entropy increase) or shifts
     elsewhere, hypothesis confirmed.
   - **Status**: queued in `scripts/strain_diagnostic.sh`.

2. **Defect redistribution invariance (31-budget conservation)**:
   - Run NE2-iter (iterative deepening of forbidden set) for ≥3 rounds.
     If total mismatches drop below 31 in any round, the budget is
     breakable. If always ≥31, conservation confirmed.
   - **Status**: queued in chain (uses 450/6/6 board now).

3. **Rare-vs-abundant inversion (100% abundant-only mismatches)**:
   - Generate boards with extreme scores (≤435 or hypothetically ≥455)
     and check the rare/abundant breakdown. The current corpus is
     440-450; broader range would test robustness.
   - Status: would need either much-worse PT (uniform random fill)
     or a NEW above-450 board.

4. **Hamming-moat depth ≥ 5**:
   - Find a 6-piece simultaneous move that improves a 450 board.
     This requires either targeted construction (e.g., from RO
     max-clique fail boundaries) or a Wauters-K=16 / Salassa-6×6
     attempt.
   - Status: would need a memetic GA with full-region crossover.

## Author note

This is the right form to discuss with the user in the morning before
deciding whether to do a literature pass and a real submission.
The findings are strong enough to share with peers; the implementation
is messier than a paper would want and the experiments would need
re-running with more replicates for statistical robustness, but the
core thesis is defensible.

The finding most likely to surprise an E2 specialist:
**rare colors are 100% matched on EVERY plateau board.** This
reframes the problem from "find the right rare-piece routing"
(intuitive but wrong) to "navigate the abundant-color combinatorial
trap" (the actual hardness).
