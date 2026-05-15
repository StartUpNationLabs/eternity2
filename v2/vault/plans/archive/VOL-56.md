# VOL-56 — dual-track: basin lottery (bg) + CDCL no-good math (fg)

**Open**: 2026-05-15 (same autonomous session as vols 54+55)

## Mandate

Per `feedback_autonomous_dont_wait` (new memory this vol):
- User: "Do not wait for me!!! Continue researching you are autonomous.
  You can do as many volumes on as many [directions] for how much long
  we want."
- → no more "queueing for next session". Pick highest-EV, ship.

## Why this direction

Vol-55 confirmed the **LP-tightening arc is closed** for record-breaking
(458 MIP-locally-optimal on multi-cluster). The two productive paths
forward are:

1. **Basin-finding** — empirical search for a basin with MIP cap > 458.
2. **Genuinely novel algorithm** — CDCL, RL, neural-MCTS.

Dual-track is the right play because (1) is compute-bound (can run
overnight in background) and (2) is math-bound (needs my foreground
cycles). Running them in parallel wastes no clock.

## T1 (background) — basin lottery, 50+ starting partials, ~6-12h

Vol-22's basin-escape recipe (bound-ascent + Hungarian + ALNS) is the
empirically-validated big-K move. Vol-22 found basins with bound-ascent
ceiling up to 471 (community 469 reachable). The question for vol-56:
**at sufficient lottery breadth, does any basin's MIP cap exceed 458?**

Plan:
- Pick or generate 50 distinct starting partials (e.g., from
  `vanilla_fast` snapshots at various seeds, or from the existing
  cluster reps).
- Run vol-22 recipe on each: bound-ascent → Hungarian repair → ALNS
  at depth-150 partial → PT.
- 30 minutes per seed × 50 seeds in parallel-batches.
- Save all >440 scores to `output/vol-56/`.
- After all complete: pick top-5 by score, run vol-55's MIP-on-cluster
  on each to see if MIP > current-score.

Compute estimate: ~25-30 wall-clock hours on 8 cores. Fits the
"days are in scope" mandate.

## T2 (foreground) — CDCL no-good learning math

Math foundation for an actually-novel propagator. Vol-29 showed
imitation has a ceiling (Δ=−1 vs teacher). RL is one path past it
(vol-30+ work). **No-good learning** is the other classic CSP technique
that hasn't been touched, and unlike RL it's deterministic + sound
(any record found by an engine with no-good learning is provably valid,
no training-distribution issues).

What I'll write tonight (vol-56 T2):
- `concepts/cdcl-no-good-e2.md`: precise definition for the E2 CSP.
- Soundness lemma (a no-good blocks only provably-infeasible
  sub-assignments).
- Propagation rule (when does a no-good fire during search).
- Storage / indexing scheme (no-goods are conjunctions of unit
  literals; index by hash).
- Sketch of engine plumbing (where in solver-engine to learn + check).

NO CODE this vol. The math is the deliverable. Engine work is vol-57+
once the spec is sound.

## Audit-at-open

Aged items: no change since vol-54 audit. Same set of defers.

## Linked

- [[../sessions/vol-55]] — predecessor result
- [[../sessions/vol-56]] — this vol's journal
- memory: `feedback_autonomous_dont_wait.md`
- memory: `project_e2_vol55_local_optimality_multi_cluster.md`
