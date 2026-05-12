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
