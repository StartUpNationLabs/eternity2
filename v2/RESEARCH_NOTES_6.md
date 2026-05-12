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

### Structure of this notes file

Each candidate gets its own subsection. Per experiment:
- Hypothesis (what we expect, why)
- Setup (exact command, parameters, predicted outcome)
- Result (numbers + interpretation)
- Verdict (next step)
