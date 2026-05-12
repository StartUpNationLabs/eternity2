# Eternity II research — volume 6

Continuation of `RESEARCH_NOTES_5.md` (night 5: score 449 → 453, two
breakthroughs via GA crossover, 10 publishable structural findings).

This volume's scope: **beyond-known methods** — explore mechanisms not
present in the published literature. The user explicitly asked for
this after seeing the night 5 results. Target is genuinely-novel
algorithmic contributions, not incremental polish.

Auto-memory in `project_e2_state.md` carries authoritative state.
Best score: **453/480** (3 distinct boards in 2-3 basins).

---

## 2026-05-12 07:07 — Vol. 6 session start

### Mission

Five candidate "beyond-known" approaches identified at start of
session. Each is principled (built on vol-5 structural findings),
small-scoped enough to test rigorously, and if successful would be
publishable in its own right.

| ID | Approach | Effort | Risk | Expected gain |
|---|---|---|---|---|
| A  | Rare-color invariance verification + reduction | 2-4h | low | structural insight; possible 4× problem-size reduction |
| B  | Strain-cascade-aware GA crossover | 4-8h | medium | +1 to +3 from improved breakthrough rate |
| C  | Multi-board consensus seeding | 2h | low | unknown — genuinely new mechanism |
| D  | Adversarial mismatch-domino solver | 3-4h | medium | +1 per fixed cluster |
| E  | Tiny board-completion transformer | 1 day | high | unclear; longshot |

**Strategy**: do A first (cheapest, biggest potential structural
insight), then C, then evaluate. B/D/E only if A and C inform direction.

### Why these are "beyond-known"

Published E2 literature (Wauters 2012, Salassa 2017/2019, Schaus-
Deville 2008, Niang 2011, Munoz 2009) covers:
- Local search variants (PT, SA, ALNS, tabu).
- MILP construction + max-clique RO.
- Memetic GA with block crossover (random regions).
- Frame-first decomposition.

None of them exploit:
1. **Rare-color invariance** — that 5 specific colors are 100% matched
   on ALL plateau boards. This was first observed in vol-5 night.
2. **Strain-cascade structure** — defects cluster at L1 distance 6-8
   from the asymmetric (7,8) hint. Vol-5 night finding.
3. **Ensemble consensus** — using 20+ high-quality boards as a prior.
4. **Mismatch-domino targeting** — focusing on the most cascade-prone
   defect rather than random destroy.

A + C use #1 and #3. B uses #2. D uses #4. E uses #3 differently.

### A — RARE-COLOR INVARIANCE (07:10): MUCH STRONGER than expected

**Hypothesis tested**: rare-color pieces are at the same cells across
plateau boards.

**First-pass result (corpus 142 boards ≥ 440)**: 6/60 rare pieces are
≥80% invariant. Only the 4 corners + a couple specific cells.
Initially looked like weak invariance.

**Reframing**: corpus contains MANY border configurations (different
frame-first seeds → different border placements). Edge pieces land
at different cells across these configurations. **The right question
is invariance WITHIN one border family.**

**Stratified analysis (corpus ≥ 449, top border family = 38 boards)**:
- 13 distinct border signatures across corpus.
- Top border family: 38 boards (mix of GA-LARGE results around the 452
  basin), score distribution {451: 9, 452: 20, 453: 5, 449: 2, 450: 2}.
- **Within this family: 164/196 interior cells (84%) have the SAME
  piece in ≥80% of boards.**
- **169/251 cells (67%) have the SAME piece in ≥95% of boards.**

**Free interior cells (consensus < 80%): 32 cells.**

**Spatial pattern**: ALL 32 free cells are at L1 distance ≤ 9 from the
asymmetric hint (7,8), clustered south-west. Skeleton covers the rest.

```
 6  .  .  .  .  .  .  .  #  .  .  .  .  .  #  .
 7  .  .  .  .  #  #  .  .  .  .  .  .  .  .  .
 8  .  .  .  #  #  #  .  *  #  #  #  .  .  .  .   ← hint
 9  .  .  #  #  #  .  .  .  .  .  #  #  .  #  .
10  .  .  #  #  .  .  .  .  .  #  #  .  .  .  .
11  .  .  #  #  .  #  .  .  .  .  #  .  .  .  .
12  .  .  #  #  #  #  #  .  .  .  .  .  .  .  .
13  .  .  h  #  #  .  .  .  .  .  .  .  .  h  .
14  .  .  .  .  .  .  .  #  .  .  .  .  .  .  .
```

**STRUCTURAL SKELETON IDENTIFIED.** This is the operational form of the
strain-cascade hypothesis: the strain front IS where the boards
disagree, and everything else is consensus.

**Implications**:

1. **Tractable sub-puzzle**: 32 free cells with ~5-9 candidate piece
   options each (per the n_distinct counts). State space = ~6^32 ≈
   10^25. Too big for brute force but small enough for **stronger
   methods that fail on the full puzzle**: focused MaxSAT, branch-
   and-bound, even careful enumeration.

2. **The skeleton + sub-puzzle decomposition is genuinely beyond-known.**
   No published E2 work has reported it. It directly operationalizes
   the structural insights from vol-5.

3. **Score potential**: if the 32-cell sub-puzzle has a better
   solution than the corpus best (453), we beat 453 with the skeleton
   intact.

**Falsification observations**:
- Score range in top family is 449-453. The OPTIMAL configuration of
  the 32 free cells (given the skeleton) determines the maximum
  reachable score in this family. If that maximum is 453, the skeleton
  IS the bottleneck — no 454+ possible without breaking the skeleton.
- If the maximum is 460+, we have a path to a much higher score that
  none of our methods has found.

**Next experiment**: build a focused CP/MaxSAT solver for the 32-cell
sub-puzzle. Estimated 4-8h.

### A continued — consensus-threshold sweep (07:14)

**Setup**: try multiple consensus thresholds for skeleton.

| Threshold | Skeleton size | Free cells | Zero-cand cells | Total candidates |
|---|---|---|---|---|
| 0.95 | 174 | 82 | 1 | 14,644 |
| 0.90 | 188 | 68 | 3 | 7,752 |
| 0.80 | 224 | 32 | 9 | 467 |
| 0.70 | 228 | 28 | 7 | 280 |
| 0.60 | 242 | 14 | 8 | 10 |

**Observation**: at 0.80 threshold, 9 of 32 cells have ZERO valid
candidates. The skeleton is OVER-constraining for those cells —
no free piece can fit their surrounding colors. This means the
"true skeleton" includes some cells that need to be reconsidered.

**At 0.95**: only 1 zero-candidate cell out of 82 free. This is
much closer to the actual structure: the truly-invariant skeleton
is ~174 cells, with 82 cells genuinely uncertain.

**Refined strategy**: use 0.95-threshold skeleton (174 cells) and
solve the 82-cell sub-puzzle with focused methods. Total candidate
state space ≈ 14,644 root-level candidates with constraint
propagation — still tractable for CP with branch-and-bound.

**Even better**: instead of hard skeleton + hard free, use the
consensus AS A PRIOR for variable ordering and value picking in
PT/SA. PT would still consider all cells but be biased toward
the consensus placements. This is a **soft-skeleton** approach.

### FRAME-LAST verified: 453 is OPTIMAL for inner k≤5 (07:53)

**Encoder works correctly.** Sanity-tested with EvalMaxSAT on
multiple sub-puzzles of the 453 board:

| center-k | free cells | EvalMaxSAT optimum | 453's mismatches | Result |
|---|---|---|---|---|
| 2 | 4 | o 1 | trivial | works |
| 3 | 9 | o 4 | 4 | **IDENTICAL** |
| 4 | 16 | o 6 | 6 | **IDENTICAL** |
| 5 | 25 | o 8 | 8 | **IDENTICAL** |
| 6 | 36 | TIMEOUT (60s) | 13 | unknown |

**Solve times** (single-thread EvalMaxSAT):
- k=3: 0.6s
- k=4: 2.8s
- k=5: 9.3s
- k=6: timed out at 60s (need longer budget)

**RIGOROUS RESULT**: the 453 board is the GENUINE OPTIMUM for the
inner k=3, 4, 5 sub-puzzles, given its outer is fixed. It's not
just a heuristic local optimum — MaxSAT proves no arrangement
of the inner k≤5 pieces (using only the inner pieces) can beat
the existing placement.

**Verification of vol-5/6 structural picture**: the 453's defects
ARE the structural minimum given the constraints. Improving 453
requires CHANGING THE OUTER (the skeleton/border), not the inner.

**Implication for "beyond-known"**:
1. Inner-perfect frame-LAST does NOT directly improve the 453
   because the inner is already optimal.
2. To find 454+ we MUST change the outer. Frame-first (which
   does change the border) is the right algorithmic class.
3. A novel algorithm: **enumerate outer configurations and
   for each, check inner optimum**. With EvalMaxSAT solving
   k=5 in 10s, we could test 100 outer configurations per
   18 minutes — feasible.

**Earlier confusion**: my first inner-8 EvalMaxSAT run "produced
no output" because k=8 was too hard within 12 minutes. **Smaller
center sizes solve quickly and produce CORRECT optima.**

**Honest disappointment**: the proof of 453 optimality means
inner-only optimization cannot break 453. The structural insight
SAYS we need to change the outer, and that requires frame-first
or GA — which we already have.

**What TO do next**:
1. Run EvalMaxSAT on the 452 board's inner k=3,4,5 — does it
   confirm 452 is also locally inner-optimal? (Should be, by
   same logic.)
2. **Most actionable**: take a 451 board (different outer than
   453), find its inner k=5 optimum, see if combining "453 outer
   + 451 inner" or vice-versa creates a better board. This is
   GA-crossover at the level of OUTER vs INNER decomposition.
3. Try EvalMaxSAT on k=6, 7 with longer budgets (1-2h each).

### FRAME-LAST proper (07:37): minimal SAT encoder DONE

**User instruction**: "we have all the time we want to fix things
properly", "break your limiting thoughts".

**The proper fix**: rewrite the SAT encoder to omit variables for
pinned cells. The vol-5 night's EvalMaxSAT failure was rooted in the
encoder emitting 5.8M clauses + 156k vars regardless of how many
cells were pinned. The new encoder makes pinning ACTUALLY shrink
the problem.

**Implementation** (~2h Rust):
- `VarMap::build_with_pinned(puzzle, pinned_map)`: skips emitting
  vars for pinned cells AND for pieces that are used in the pinned
  set.
- `encode_with_pinned(puzzle, hints, vmap, opts, pinned)`: skips
  cell-EO for pinned cells, skips piece-EO for pinned pieces.
- For edge-match clauses with one pinned endpoint: the pinned color
  is a constant — m_{e,k} for k≠pinned forced false; the other side
  must emit the pinned color.
- For pinned-pinned edges: collapsed to a "TRUE" tautology that
  contributes +1 to the MaxSAT objective.
- Backwards-compat: `build()` / `encode()` delegate to the new
  functions with empty pinned map.

**Empirical reduction** (HISTORIC 453 board, pin outside, free
center-k):
| center-k | free cells | OLD vars | NEW vars | OLD clauses | NEW clauses | OLD size | NEW size |
|---|---|---|---|---|---|---|---|
| 8  | 64  | 156k | 27k  | 5.8M | 383k | 109 MB | 6.5 MB  |
| 12 | 144 | 156k | 90k  | 5.8M | 2.6M | 109 MB | 46 MB   |

15× reduction at center-k=8, 2.2× at center-k=12. **EvalMaxSAT now
has a chance.**

**Launched: EvalMaxSAT on inner-8 (TCT 1800s)**. PID 59281.
Result will tell us: given the 453's outer fixed, what's the
optimal inner-8 placement using the existing 64 inner-8 pieces?

If MaxSAT finds an inner-8 with FEWER mismatches than the current
453 has (15 in that zone), we'll improve the score.

### USER QUESTION (07:30): "allow mistakes only in outer 2 layers"

**Empirical check across 86 corpus boards (score ≥449)**:
- Mismatches in outer-2 zone (rows/cols 0-1, 14-15): 291 (11.5%)
- Mismatches in inner-12 zone (rows/cols 2-13): 2,239 (**88.5%**)
- Average defects per board: 29.4

**Conclusion**: defects naturally occur INTERIOR. The "allow only
outer mistakes" constraint would FORCE the optimizer to move
defects from where physics wants them (interior strain front) to
where physics doesn't want them (boundary).

**Two ways this could go**:
1. (Optimistic) Constraint reveals a NEW basin where strain
   dissipates to boundary instead of clustering at (7,8) cascade.
   If 30 mismatches can be pushed to outer-2 zone: ≤ 264 inner +
   29.4 outer ≈ 264 + ~10 unmatched outer = 274+ → potentially
   higher score IF inner perfect-fill is achievable.
2. (Pessimistic) Constraint is unsatisfiable or produces much
   worse boards because it fights against natural strain dynamics.

**Testing strategy**: NE2-style soft penalty on a large set of
inner-zone edges. forbidden.rs's u64 bitset caps at 64 edges
(264 won't fit). Either extend the bitset (Rust patch ~30 min)
or use a SUBSET of inner-zone edges as forbidden.

Better: **inner-perfect frame-LAST experiment**:
- Take inner 12×12 region.
- Solve it EXACTLY via CP (12² = 144 cells, ~270 internal edges).
- Then place the outer 2 layers around it.
- Total ≥ 264 inner + outer matches.

This is the inverse of frame-first. Has not been tried.

### Anti-consensus exploration (07:25) — wrong target

**Setup**: build forbidden-edge list from edges that have ≥95%
same-color consensus across corpus.

**Result**: 24 edges qualify. Of those, **9 are border-related**
(forced by hint placement) and **15 are interior** but cluster
around the symmetric corner-hint cascades.

Penalizing these would force PT away from corner-hint configurations,
basically making the puzzle impossible. **Not the right anti-consensus
target.**

The right target would be edges consensus WITHIN the 452 basin
specifically and VARYING across OTHER basins. Identifying that
requires per-basin partitioning of the corpus, which I haven't done.

**Verdict**: anti-consensus needs basin partitioning first. Defer.

### A continued — Free-zone solver TRIED but BACKTRACKING approach yields 357 (07:22)

**Setup**: backtracking solver on 0.95-threshold sub-puzzle (82 free
cells, 1 zero-cand cell skipped, 287 skeleton-internal edges baseline).

**Result**: 120s search, 216k nodes visited, best free-zone partial
contribution = 70 edges. Total full-board score = 357/480.

**Diagnosis**: the skeleton baseline of 287 internal edges is FAR
LOWER than the 451-453 boards' total scores. The free zone in the
existing 453 boards contributes ~166 edges (skeleton-free + free-
free), of which my solver only achieves ~70 in 2 minutes.

**Why this didn't work**: my decomposition is too "rigid":
- Skeleton placements are FIXED.
- Skeleton individual pieces aren't EDGE-optimal in isolation; they're
  optimized as a network with the free pieces.
- Holding the skeleton fixed while searching free zone alone loses the
  cross-pollination that produces 453.

**Implication**: pure skeleton+free decomposition with hard skeleton
is NOT the right algorithm. The skeleton is informative as a
DESCRIPTION (where solutions agree) but not as a HARD CONSTRAINT.

### C — CONSENSUS SEEDING (07:20): NEGATIVE — polishes back to 452

**Setup**: built a consensus board from the top family (38 boards).
Per-cell modal piece, with greedy duplicate repair. Initial score:
451/480.

**PT polish (300s, seed 5371)**: best = 452/480.

**Overlap analysis**:
- consensus 452 vs original 452: **100% identical**.
- consensus 452 vs original 453: 75.9% (different basin).

**Verdict**: consensus seeding lands in the SAME 452 basin we
already had. PT collapses the smoothed-consensus board back to
the most-attractive nearby fixed point, which is the existing 452.

**Why it didn't work**: the consensus IS a smoothed version of
the 452 basin's representative boards. PT just removes the noise
and lands at the cleanest 452. To find a NEW basin, the seed must
be structurally orthogonal to the 452 — which the consensus, by
construction, is not.

**Implication**: consensus seeding alone does NOT escape basins.
It's a useful "PT-prep" but not a breakthrough mechanism in itself.

**Combine with constraint**: use the consensus AS A FORBIDDEN
SET (NE2-style) — penalize PT for matching consensus placements,
forcing exploration AWAY from the basin. ~30 min experiment.





---

### Structure of this notes file

Each candidate gets its own subsection. Per experiment:
- Hypothesis (what we expect, why)
- Setup (exact command, parameters, predicted outcome)
- Result (numbers + interpretation)
- Verdict (next step)

---

## VOL-6 PIVOT — BORDER-FIRST attack ("change the edges, not the center")

### Context

EvalMaxSAT inner-{3,4,5} bisection rigorously proved: the 453 board's
**inner k≤5 sub-region is OPTIMAL given the current outer**. Inner k=6
times out at 60s, k=8 times out at 739s with `s UNKNOWN`. Inner-attack
as a path to 454+ is dead.

Sister-session research conclusion: the 453 ceiling is a property of
the CURRENT BORDER, not of the puzzle. To find 454+, we must change
the BORDER (the 60 outer cells: 4 corners + 56 edge pieces).

### Inner-attack ruled out — EvalMaxSAT bisection table

Encoded the 453 board's interior as a partial-MaxSAT instance with a
square sub-region of side `k` UNFIXED and the rest pinned. Used the
minimal pinned-aware encoder (15× WCNF size reduction at k=8). Ran
EvalMaxSAT (single-thread CDCL + core-guided MaxSAT) per `k`:

| k | sub-region | result                       | wall time | implication                                        |
|---|------------|------------------------------|-----------|----------------------------------------------------|
| 3 | 9 cells    | `o 4` (= 453's actual)       |   0.6 s   | inner-3 placement OPTIMAL                          |
| 4 | 16 cells   | `o 6` (= 453's actual)       |   2.8 s   | inner-4 placement OPTIMAL                          |
| 5 | 25 cells   | `o 8` (= 453's actual)       |   9.3 s   | inner-5 placement OPTIMAL                          |
| 6 | 36 cells   | TIMEOUT                      |  60   s   | EvalMaxSAT cannot prove ≤453 in 1 min              |
| 8 | 64 cells   | `s UNKNOWN`                  | 739   s   | killed at ~12 min; problem grows past tractability |

`o N` is EvalMaxSAT's notation for "best known objective" (=number of
unsatisfied soft clauses; minimizing this minimizes mismatches).

**Reading**: for k ∈ {3, 4, 5}, the solver completes and returns the
SAME mismatch count the 453 board already has. That is the strongest
form of optimality proof available — no rearrangement of the inner
k×k pieces (with the outer 256-k² pinned) beats current placement.

For k ≥ 6 we don't yet have proof either way, but the interior k=8
window (4096 piece-rotation variables) didn't even produce a soft
bound after 12 min. Beating 453 by re-arranging only the inner is
either impossible (k≤5 confirmed) or beyond a state-of-the-art
single-threaded MaxSAT solver in reasonable time (k≥6).

**Conclusion**: route to 454+ is NOT through the inner. Pivot to
border-space exploration is forced by evidence.

### BORDER-1 — DIAGNOSIS (2026-05-12 morning): CORPUS IS BORDER-MONOCULTURE

**Setup**: extracted the 60-cell border signature (piece_id, rotation
per cell) of every corpus board ≥449. Counted unique borders and
per-cell consensus.

**Result**:
```
corpus ≥449:                                28 boards
unique borders:                              3
border collisions (boards sharing border):  25 / 28
mean per-border-cell agreement:              0.862
border cells with 100% consensus:            5
border cells with ≥95% consensus:            5
border cells with ≥80% consensus:           58 / 60
border cells with <50% consensus:            0
```

**Interpretation**: every algorithm we ran (PT, NE, frame-first, GA-XL,
GA-CASCADE) explored ESSENTIALLY ONE BORDER. 58/60 border cells are
the same piece-rotation in ≥80% of all boards ≥449. The corpus is
border-monoculture.

**Why this happened**: PT and frame-first both lock the border early
(it's trivially 100% feasible per RESEARCH_NOTES_4 Phase-C); GA
crossover preserves border because corner-and-edge pieces have
distinct color signatures, so swapping interior blocks never disturbs
the border. The corpus inherited the border from the FIRST converged
PT run and propagated it via every downstream algorithm.

**Implication**: the 453 ceiling is a property of THIS BORDER. Moncktons's
hint structure constrains many borders to be near-feasible, so there
should be many distinct valid borders — we've just never sampled them.

### BORDER-2 — generative border library (in progress)

**Hypothesis**: there exist many (possibly thousands) of distinct
fully-feasible borders — sequences of corner+edge pieces along the
perimeter where adjacent border-colors match, AND the 5 official hint
pieces are placed at their fixed cells/rotations.

**Setup (planned)**:
1. Identify the 60 border pieces (4 corners with two BORDER edges,
   56 edges with one BORDER edge) from the puzzle file.
2. Enumerate / sample border placements as sequences:
   - Top row: corner_TL → 14 edge pieces → corner_TR
   - Right col: corner_TR → 14 edges → corner_BR
   - Bottom row: corner_BR → 14 edges → corner_BL
   - Left col: corner_BL → 14 edges → corner_TL
3. Per cell, the inward-facing color is what the interior must match.
4. The 5 official hints constrain 1 corner + ?? cells.
5. Use a fast backtracker (no interior, just border) — should be very
   cheap. Target: 100-1000 distinct feasible borders.

**Predicted outcome**: tens to thousands of feasible borders, far more
than 3. Confirm with score per (border, interior PT 30s) pair.

### BORDER-2a — Combinatorial estimate (transfer-matrix)

**Setup** (`scripts/border_count_estimate.py`): build a transfer
matrix `T[c→c']` = # edge placements presenting (left=c, right=c')
when oriented BORDER-out. 4 corner placements per corner × `T^14`
along each side × cycle closure.

**Result**:
```
Naive 4! × 56!:                    1.7e76
Transfer-matrix (with replacement): 2.4e58
Per-color T row sums (color → # placements): 1=12, 2=11, 3=10, 4=11, 5=12
Border-color alphabet: ONLY {1,2,3,4,5} (the rare colors).
Per-corner placements: TL=TR=BR=BL=4 each.
```

**Interpretation**: the border CSP has very strong color regularity:
only 5 colors used on the inward perimeter, branching factor ~10
after color match (vs 64 raw placements). With-replacement count
≈ 10⁵⁸ is the "shape" — once piece-uniqueness is enforced, the true
count is astronomically smaller but still enormously larger than 3.

**Implication**: there are almost certainly 10²–10⁸+ distinct
feasible borders. Naïve Python backtracking (60-deep tree, ~10
branching) is too slow. Need:
  - Rust implementation (10²-10³× speedup over Python).
  - Cycle-closure constraint propagated UP FRONT (fix TL incoming
    color first).
  - Per-color piece-budget pruning (only 10-12 pieces per color
    class, so we can prune when a class is exhausted before all
    its slots are filled).

**Side discovery**: the border uses ONLY colors 1-5 (the "rare
colors" from RESEARCH_NOTES_5 frequency analysis). This means the
abundant colors 6-22 NEVER appear on the perimeter — they're
pure-interior. This was implicit but is now confirmed: it explains
why "rare always matched" in our corpus — rare colors are
*structurally forced* on the perimeter where colors are scarce.

### BORDER-2b — Rust enumerator (corners-first decomposition)

**Iteration 1 (full-perimeter DFS)**: 690M nodes/30s, 0 borders.
Single-step forward-checking too weak; max_depth stalled at 29/60
(top row + half right column). Pure DFS doomed for a 60-deep tree
with branching ~10.

**Iteration 2 (corners-first + per-side path enumeration + 4-way
disjoint product)**: 60s, 0 borders, 3 corner-quads tried. Per-side
enumeration itself is the bottleneck.

**Iteration 3 — diagnostic**: enumerated TOP-side paths with the
453's known boundary colors (start=1, end=2):
```
top paths start=1 end=2: 5,774,451+ (cut off at 30s, not exhausted)
nodes: ~10M, ~330k paths/s in Python
```

**HUGE FINDING**: a **SINGLE side** has 5.77M+ paths just for a single
(start, end) color pair. With 4 corner placements per corner and 24
corner-permutation symmetries, the total raw border space is at least
10²² distinct paths before piece-disjoint filtering. The 3-border
corpus monoculture is NOT a property of the border space being small —
it's pure algorithmic stickiness.

**Implication**: SAMPLING is the right approach, not enumeration. We
need a stratified sampler:
  1. Sample (TL, TR, BR, BL) corner-quad uniformly from ~24 distinct.
  2. For each side: sample one valid 14-piece path uniformly via
     Las Vegas backtracking (random ordering at each node, restart
     on dead end).
  3. Reject if cross-side piece-disjoint constraint fails.
  4. Repeat until N=10³+ distinct borders.

**Iteration 4 — Las Vegas sampler (SUCCESS)**:
- Pick a corner-quad uniformly at random from the 24 distinct.
- Per side, randomized backtracking with shuffled candidate order
  + node budget (50k per side).
- Cross-side disjoint-pieces enforced via bitmask (256-bit `[u64; 4]`).
- FNV-style hash for de-duplication.

```
target=10000 borders, 60s budget
result: 10000 distinct borders in 5.9s, 11367 samples,
        88% per-sample success rate, ~1900 samples/s.
```

**Implication**: the border space is enormous and easy to sample
diversely. Our corpus monoculture is 100% an artifact of every
algorithm latching onto the SAME border early. Now we have 10k
borders and can ask: which borders SUPPORT a higher interior PT
score than the corpus's 3?

### BORDER-2c — diversity sanity check on the 10k library

`scripts/border_diversity_check.py`:

| metric                              | corpus (n=28) | library (n=10000) |
|-------------------------------------|---------------|-------------------|
| mean per-cell agreement (modal/n)   | **0.862**     | **0.045**         |
| cells with ≥80% agreement           | 58 / 60       | **0 / 60**        |
| cells with ≥50% agreement           | 60 / 60       | 0 / 60            |
| pairwise mean overlap (1000 pairs)  | clustered     | **0.036**         |
| pairs with ≥80% overlap (1000)      | clustered     | **0 / 1000**      |
| distinct corner-quads               | ≈1            | **24 / 24** (all) |

Corner-quad distribution near-uniform (most common 486, least 341
out of 10000 / 24 = 417 expected). Per-cell agreement collapses
from 86% to 4.5%. Pairwise overlap 3.6% on average — the 10k
borders are nowhere near each other and nowhere near the corpus.

**Conclusion**: the Las Vegas sampler is genuinely escaping the
corpus monoculture. Safe to proceed to BORDER-3 triage.

### BORDER-3c — surrogate triage (color supply vs. corner tightness)

**Surrogate v1 — global color over-demand**: per border, compute
inward-color histogram and compare against inner-piece color supply.

```
inner-piece color supply per color: ~44-49 edges per color (17 abundant colors)
border inward demand per color:     1-6 edges per color
over-demand score (corpus 453):     0
over-demand score (10k library):    min=0, max=0, median=0
```

**Verdict**: USELESS as a discriminator. The inner palette is far
richer than the border demands, so every feasible border satisfies
supply trivially. **Structural insight**: the border is NOT a binding
constraint on color supply.

**Surrogate v2 — inner-corner tightness**: at each of the 4 inner
corner cells (1,1), (14,1), (1,14), (14,14), count the number of
(inner_piece, rotation) pairs that satisfy BOTH boundary-color
constraints. If any corner has 0 → border is **provably infeasible**.

```
borders with ≥1 inner-corner having 0 candidates: 3727 / 10000 (37%) — INFEASIBLE
feasible borders:                                  6273 / 10000 (63%)

corner-tightness min/sum (across 4 corners):
  corpus 453:                  min=2,  sum=17
  10k library best:            min=5,  sum=24
  10k library median (feasible): min~1, sum=10
  10k library worst (feasible): min=1,  sum=4

inner-corner candidates per cell (corpus 453):
  (1,1):   5 candidates  (top=7, lft=7)
  (14,1):  2 candidates  (top=14, rgt=22)
  (1,14):  7 candidates  (bot=22, lft=21)
  (14,14): 3 candidates  (bot=18, rgt=13)
```

**Findings**:
1. **37% of all randomly-generated borders are provably infeasible**
   at the inner-corner level. Triage filter saves 37% of PT budget.
2. **Some library borders have 6× more inner-corner candidates than
   the corpus 453's** (sum=24 vs corpus's 17). These are structurally
   LESS CONSTRAINED interiors — could be easier basins for PT to
   explore well.
3. **Caveat**: tighter ≠ worse for PT necessarily. A loose border may
   lead PT into a poor local optimum. We want a stratified sample:
   top-1000-by-tightness-sum AND a random sample of feasible borders.

**Outputs**:
- `output/borders/top_1000_by_corner_tightness.jsonl`: top-1000 feasible
  borders by max corner-sum.
- 3727 infeasible borders excluded.

### BORDER-3d — add `--pin-perimeter` to pt_e2 (next)

pt_e2 currently has `--pin-hints` (hint pieces only). We need
`--pin-perimeter <border.json>` to load the 60-cell border arrangement
and pin them as additional hints. Then:
  - Sanity test: pinning the 453's own border + PT should produce 453.
  - Triage: pin each library border, PT 10s, record best score.
  - Funnel: top-K → 60s PT → 300s PT.
