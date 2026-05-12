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

---

### Structure of this notes file

Each candidate gets its own subsection. Per experiment:
- Hypothesis (what we expect, why)
- Setup (exact command, parameters, predicted outcome)
- Result (numbers + interpretation)
- Verdict (next step)
