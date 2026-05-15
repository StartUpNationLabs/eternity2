# Current vol — vol-50 (opening) — 2026-05-15

**Predecessor**: vol-49 closed with adaptive-ES negative result.
See [[../sessions/vol-49]].

This file rolls forward five drifted volumes (45→50) in one update
because the previous CURRENT-VOL was last touched at vol-45 open.
Vols 46–49 produced four documented negative results:

- **Vol-46**: per-class LP UB diagnostic — no record lever.
- **Vol-47**: lifted-LP McCormick formulation — intractable at scale; column-gen variants invalid. [[../sessions/vol-47]].
- **Vol-48**: vanilla ES (sigma=0.2) — collapsed at 277/480 vs vol-29 imitation baseline 282. [[../sessions/vol-48]].
- **Vol-49**: adaptive-sigma ES — improved peak to 280, still below baseline. [[../sessions/vol-49]].

## Vol-50 binding item (1 max per audit-at-open)

**Q-learning value-order PoC.**

Vol-48 + vol-49 closed cleanly with the same diagnosis: the engine's
`ValueOrder::Learned` argmax is structurally invariant to small policy
perturbations, so ES gradient estimates collapse. The natural pivot:
**Q-learning**, where the gradient is on Q-values (not on the argmax),
which sidesteps the discreteness obstruction.

### Concrete plan

1. **Reuse vol-29 v3 architecture** as Q-net (position-relative GNN,
   ~63k params). Output = scalar Q(state, candidate) instead of
   classification logit.
2. **Episode-based TD target**: for a trajectory `s_1, a_1, r_1, … s_T, r_T`
   from engine, fit Q(s_t, a_t) ← r_t + γ·max_a Q(s_{t+1}, a). Reward
   shaping: matched-edge count on episode close (sparse) + small
   per-step shaping on `pieces_placed` to densify (optional).
3. **Data collection**: drive engine with `ValueOrder::Learned`, log
   (state, candidate-set, chosen, depth-at-end, matched-at-end).
   Reuse `crates/rl-search` infrastructure from vol-48.
4. **Gate at 6×6/5c first** (cheap; same testbed as vol-26 gate).
   Train Q-net on N=200 episodes from random-policy. Compare to
   vol-29 imitation model. PASS = median nodes ≤ vol-29 v3
   on the same 200-puzzle benchmark.
5. **If 6×6 PASS, scale to canonical 16×16/22c**: gather 100+ episodes
   from `joe_depth150_bp` baseline, train, measure depth + post-ALNS
   score. PASS = depth ≥ 165 (match imitation ceiling) AND post-ALNS
   ≥ 458 (match all-time record on at least one seed).

### Risk budget

- **5 days**: full pipeline (Q-net + training loop + 6×6 + canonical gate).
- **2-day kill-switch**: if 6×6 Q-net is below random-policy after
  3 training rounds, kill. The vol-48/49 pattern (collapse to
  below-baseline) should be detectable within hours, not days.

## Audit-at-open compliance

Aged `unbuilt` items from BACKLOG (≥ 3 vols old; require decision):

| Item | Since | Decision |
|---|---|---|
| `rl-self-play-value-order` | vol-30 (vol-38 defer) | **picked-up as vol-50** (this binding item is the Q-learning variant of self-play) |
| `mcgavin-prune-restart-bound-trigger` | vol-36 | defer to vol-51+ (one binding item this vol) |
| `code-refactor-vol25-batch` | vol-25 | **wont-do**: 10 vols without picking, never a record-mover; ship only if a specific extraction unblocks a record-track item |
| `unsat-soft-value-order-vol37` | vol-34 | defer to vol-51+ (one binding item) |
| `joe-iteration-budgeted-prune` | vol-32 | defer to vol-51+ |
| `learned-on-ties-long-pt` | vol-31 | **wont-do**: post vol-32 bug fix, LOT lift is +3 edges not +9; 1-2h PT lottery on the smaller signal is not record-level |
| `multi-cell-bound-ascent` | vol-22 | **wont-do**: bound-ascent ALNS-collapse was confirmed vol-21/22; multi-cell variants share the same recovery-collapse mode |
| `bound-floor-alns-with-per-step-check` | vol-22 | defer (still partial, invasive build, vol-50 scope is ML) |
| `diverse-457-search` | vol-21 | overnight job, fire-and-forget eligible — not vol-50 scope |
| `tight-joint-bound-survey` | vol-22 | **wont-do** (blocked on `kissat-rc2-maxsat` which is already wont-do) |

Resolved/promoted from this audit:
- 1 picked, 4 deferred (one-binding-item discipline), 4 wont-do.
- BACKLOG.md must be amended with the 4 wont-do decisions when this
  vol closes.

## Linked

- [[../sessions/vol-48]] — vanilla ES result
- [[../sessions/vol-49]] — adaptive ES result
- [[../concepts/learned-value-order]] — imitation context
- [[../concepts/rl-es-pipeline]] — predecessor RL design
- [[../concepts/rl-self-play-value-order]] — original RL design
