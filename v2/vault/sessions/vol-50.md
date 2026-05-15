# Vol-50 — Joe's iteration-budgeted prune-restart (search-side pivot from ML)

**Theme**: After vol-48/49 ES collapse and a vol-50 Gumbel-via-ONNX probe
(dead end), pivoted from ML to search-side and shipped a node-budget
axis for the engine. A/B-tested Joe's "iteration-budgeted prune-restart"
policy against the existing time-budgeted single-round baseline.

**Status**: in-progress.

## What was shipped

### Engine — node-budget axis (`SolveOpts.node_budget: u64`)

- `crates/solver-trait/src/lib.rs`: new field, default 0 (= unlimited).
- `crates/solver-engine/src/lib.rs`: `node_budget_exhausted()` helper;
  checked at the existing rate-limited safety hook in `recurse`. Returns
  `RecurseResult::TimedOut` when exceeded.
- **Per-worker semantics**: with RootSplit parallelism (default for
  `joe_depth150_*_par`), each worker holds its own `node_id` counter,
  so `node_budget` caps per-worker nodes, not aggregate. With 8
  workers the aggregate cap is 8× node_budget. This is honest; the
  alternative would be a shared atomic which adds contention.

### Driver — `--node-budget N` flag on `prune_restart`

`prune_restart` accepts `--node-budget N` alongside existing
`--cp-budget-ms`. Both can be set; the engine stops at whichever
fires first.

## What's being measured

A/B at canonical-E2 cold-start, seed=1:

| Variant | Rounds | Per-round budget | Total wall |
|---|---:|---:|---:|
| Baseline | 1 | 300s time | ~5 min |
| Joe-IB | 5 | 60s time each | ~5 min |

Both use the same total wall-clock. The hypothesis: 5 short rounds
with prune-restart between them produce a HIGHER-SCORE basin than
1 long round, because each restart resets the search from the partial
of the previous round (pinning) without getting stuck.

## Findings

### F1. Node-budget produces non-stationary round durations (real, modest)

A/B on canonical-E2 cold-start, seed=1, 5 rounds:

| Variant | R1 (s, depth, score) | R2 | R3 | Total wall |
|---|---|---|---|---:|
| time-budget 60s/round | 60s/d27/23 | 60s/d147/284 | 60s/d77/**412** | ~3 min |
| node-budget 525k/worker | 76s/d27/23 | **488s**/d163/**319** | 17s/d61/410 | ~10 min |

Joe-IB node-budget round 2 ran 488 seconds (8× longer than time-budget)
and reached depth 163 vs 147 (+16 depth) / score 319 vs 284 (+35). But
the deeper round-2 partial led to a slightly LOWER round-3 score
(410 vs 412). Net result: similar final partial, 3× more wall-clock.

**Interpretation**: node-budget is a real distinct trigger axis. It
exposes the engine's effective node-rate variation across depths (round
2 has small domains → low nps → long wall). On this specific cold-start
trajectory, the differential doesn't translate to higher final score.

### F2. ALNS-5min from prune_restart-multi-round partial reaches 428

ALNS-5min × 4 seeds from the time-budget round-3 partial (score 412):
| Seed | Final |
|---:|---:|
| 1 | 421 |
| 2 | 426 |
| **3** | **428** |
| 4 | 418 |

vs vol-23's published prune_restart + ALNS = 424. **+4 best, +0 median**.
Modest positive signal; not record-class.

### F3. PT-1h from 428 reached 437 in 10 seconds, then …

(filled when PT-1h completes)

### F4. Q-learning + ONNX-Gumbel-trick are dead ends

(see vol-50-pivot-trail)

## Vol-50 also documented two prior dead-ends

1. **Q-learning design** (`vault/concepts/q-learning-value-order.md`):
   premise was sound (sidesteps argmax-invariance) but infrastructure
   gap (no per-step trajectory logging) made the build expensive.

2. **REINFORCE via Plackett-Luce / ONNX Gumbel-trick**
   (`vault/concepts/reinforce-plackett-luce-value-order.md`):
   Goal was to enable a stochastic policy without modifying the
   engine. Probe: re-exported vol-29 v3 model with `torch.rand_like`
   Gumbel noise. **5 identical runs at fixed engine seed gave
   identical `matched=275 placed=167`** — ORT's `RandomUniformLike`
   with no seed attribute is deterministic within a session. The
   "no engine change" path is dead. The engine-side
   `LearnedStochastic` variant would work but represents a 6th
   ML attempt across 5 negative ML volumes (26-29 imitation,
   48-49 ES) — wrong move from an EV standpoint.

## Decision trail

See [[vol-50-pivot-trail]] for the full reasoning chain.

## Linked

- [[../plans/CURRENT-VOL|CURRENT-VOL]]
- [[../concepts/prune-restart]] — existing infra
- [[vol-48]], [[vol-49]] — ES predecessor sessions
- [[vol-50-pivot-trail]] — decision trail
