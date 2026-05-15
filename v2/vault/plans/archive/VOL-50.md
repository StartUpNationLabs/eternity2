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

## Vol-50 binding item — PIVOTED (2026-05-15)

The original Q-learning / REINFORCE plan was pivoted twice:

1. Q-learning → REINFORCE+Plackett-Luce: cleaner gradient.
2. REINFORCE+PL → engine-side `LearnedStochastic`: ONNX Gumbel probe
   showed `RandomUniformLike` is deterministic within a session, so
   the "no engine change" trick is dead. See
   [[reinforce-plackett-luce-value-order]] "quick probe" section.

3. **(final) Engine-side `LearnedStochastic` → drop ML for vol-50.**

   Honest assessment: ML on E2 value-ordering has produced no
   record-class lift across vols 26-29 (imitation: best Δ=−1)
   and vols 48-49 (ES: collapsed below baseline). Vol-50 REINFORCE
   would be the 6th attempt on the same axis. Records actually broke
   from search-side innovation (vol-22 basin-escape, vol-32
   vanilla_fast).

   Pivoting vol-50 binding item to a search-side build that's been
   sitting unbuilt for 14 volumes.

## Vol-50 binding item — Joe's iteration-budgeted prune-restart

**Build**: `joe-iteration-budgeted-prune` (BACKLOG, unbuilt since vol-32 open).

Joe's published recipe (msg #11725 in [[../reference/reference-e2-community-corpus|community corpus]]):
"99% of canonical-E2 cold-start time is spent at depth > 132; with
150 correctly-placed tiles a solution is found in <1500 iters;
therefore prune to depth 150 every 2000 iters when depth > 150 has
consumed > 2000 iters without progress. 30-49% search-space reduction."

Vol-23 shipped `mcgavin-prune-restart` with a CP-depth trigger:
restart whenever current depth ≤ some threshold. Joe's trigger is
**iteration-count based**: restart when N iters at depth > D haven't
produced a new-best. Different policy, same engine plumbing.

### Concrete build

1. Add `SolveOpts.iteration_budget_at_depth: Option<(u32, u32)>` —
   `Some((depth, iters))` means "if iters at depth > `depth` exceeds
   `iters` without best-improvement, trigger restart".
2. Engine: extend the existing prune-restart hook
   (`crates/solver-engine/src/lib.rs` recurse) to fire on this new
   condition.
3. A/B on canonical E2: vanilla_fast cold-start vs joe-IB cold-start
   at 5min budget × 8 seeds. Measure depth + matched.
4. If positive: feed best partials into ALNS-5min. Compare records.

### Risk budget

- **1 day**: engine plumbing + bin + A/B run.
- **2 day kill-switch**: if A/B at 5min shows < +2 matched on
  median, mark `wont-do` and pivot vol-51 to another search-side
  item (`mcgavin-prune-restart-bound-trigger`, vol-36 T2).

### Why this beats both vol-48 ES and pure Q-learning

- **vs ES**: gradient is propagated by backprop through the policy
  network, not estimated from reward-weighted Gaussian noise. No
  argmax-invariance collapse.
- **vs Q-learning**: REINFORCE updates the policy directly toward
  observed reward; no TD target, no target network, no replay buffer
  needed for the PoC. Less infrastructure, faster turnaround.

### Concrete plan — Gumbel-trick stochastic policy (NO engine change)

Build insight: the engine sorts by ONNX score. If we inject Gumbel
noise into the model's output BEFORE the engine sees the scores, the
engine's deterministic argmax becomes a sample from the Plackett-Luce
distribution over rotations. The log-probability of the resulting
order has a closed form. **No engine code change needed.**

1. **Python episode runner (~half day)**:
   - At score time, model outputs raw logits `z_i` per candidate.
   - Add `g_i ~ Gumbel(0, 1)` to each: `s_i = z_i + T·g_i`.
   - Export `s_i` to the engine via ONNX. Engine argmax-sorts → samples
     Plackett-Luce permutation. log P(permutation) is computable
     from the original `z_i` after-the-fact (PL log-prob = sum of
     log softmaxes at each step).

2. **Wrap in `ml/reinforce_step.py`** (~half day):
   - Run N episodes by invoking the existing `run_learned` Rust bin
     with the Gumbel-perturbed ONNX (re-exported once per episode).
   - Engine returns `matched_at_close` per episode.
   - REINFORCE loss: `-mean[log_prob_episode * (R_episode - baseline)]`
     where `log_prob_episode = sum over steps of log P(chosen rot | scores)`.
   - Backprop, SGD step, re-export ONNX.

   Open question: we need per-step `(cell, candidates, chosen_rot)`
   to compute the per-step PL log-prob. Currently `run_learned`
   doesn't log this. Need to either:
   - (a) extend the Rust bin to log the trajectory; OR
   - (b) re-implement the engine's CP loop in Python at small scale
     for the 6×6 gate (model is so fast at 6×6 that this might be
     faster than the Rust round-trip).

3. **Gate at 6×6/5c**. K=10 training rounds × N=32 episodes / round.
   PASS = mean `matched` STRICTLY ABOVE vol-29 v3 baseline on the
   same 200-puzzle benchmark.

4. **If 6×6 PASS**, scale to canonical (5 days) or document and stop.

### Risk budget — TIGHT

- **1 day kill-switch**: if no infrastructure path to per-step
  log-prob exists, stop and re-pivot to engine-side
  `LearnedStochastic` build (the 5-day variant).
- **2 day kill-switch**: if 6×6 REINFORCE doesn't beat vol-29 v3
  after 10 rounds, document and close vol-50 as third ML negative
  result. Pivot to search-side records-of-records (the only axis
  that has produced post-vol-32 lift signal).

### Wider reflection

After vol-28 (transfer null), vol-29 (imitation ceiling), vol-30/31
(misattributed bug), vol-48 (ES vanilla collapse), vol-49 (ES adaptive
collapse), this is the **6th attempt** to lift records via ML on
value-ordering. Two-day kill-switch is non-negotiable. The records that
exist (458 vol-32, 457 vol-22) came from SEARCH-side innovation, not
ML. If vol-50 fails, vol-51 must pivot OFF the ML track.

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
