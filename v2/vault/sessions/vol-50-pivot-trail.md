# Vol-50 pivot trail (mid-session) — 2026-05-15

**Status**: in-progress.

This page documents the decision trail BEFORE vol-50's final binding
item is built, so the reasoning chain survives the session.

## Vol-50 binding item revisions

### v1: Q-learning value-order PoC

Motivation: vol-48/49 ES collapsed; Q-learning gradient is on
Q-values (continuous) instead of argmax (discrete) → bypasses
collapse mode.

Pivoted within 1 hour because:
- Q-learning still needs episode-level trajectory data the engine
  doesn't currently log.
- REINFORCE has cleaner theoretical guarantees AND simpler
  infrastructure (no replay buffer, no target network).

### v2: REINFORCE via Plackett-Luce ordering

Motivation: engine sorts deterministically by Learned scores at
`lib.rs:2515`. Adding Gumbel noise to the scores makes the sort
a sample from a Plackett-Luce distribution with closed-form log-prob.

Pivoted within ~1 hour because:
- Initial probe wrapped vol-29 v3 model with `torch.rand_like` +
  Gumbel transform, exported to ONNX with `RandomUniformLike`.
- A/B with 5 runs at fixed engine seed showed IDENTICAL output
  (`matched=275 placed=167`) across all 5.
- ORT's `RandomUniformLike` with no seed attribute is deterministic
  within a session. The "no engine change" path is dead.
- Engine-side `LearnedStochastic` build would work but is 1-2 days,
  and ML on E2 value-order has produced no record-class lift across
  vols 26-29 (imitation) + vols 48-49 (ES) = 5 negative ML
  volumes. A 6th ML attempt on the same axis is the wrong
  innovation move.

### v3: Joe's iteration-budgeted prune-restart (SEARCH-SIDE)

Motivation:
- The two records that exist (458 vol-32, 457 vol-22 basin-class)
  came from SEARCH-side innovations.
- BACKLOG `joe-iteration-budgeted-prune` (unbuilt since vol-32
  open) implements a different restart-trigger than vol-23's
  CP-depth trigger.
- Joe claimed 30-49% search-space reduction (community corpus
  msg #11725).
- Vol-23 prune_restart driver already exists; the new policy is
  a per-round budget axis.

### v3 final scope (smallest experiment first)

1. Add `SolveOpts.node_budget: Option<u64>` to solver-trait + plumb
   in engine recurse (check counter every K iterations, stop when
   exceeded).
2. Use existing `prune_restart` driver with `--node-budget N` (a
   new flag) instead of `--cp-budget-ms T`.
3. A/B on canonical E2: time-budget 5min vs node-budget X (calibrated
   from the time-budget's typical node count).
4. If node-budget round-trip gives non-trivially different (i.e.
   higher depth or higher matched) results, ship; if not, document
   null and pivot vol-51 to `mcgavin-prune-restart-bound-trigger`.

### Why not "do REINFORCE anyway with the engine-side change"

Worth recording explicitly: I am NOT giving up on RL on E2
permanently. The pivot is sequencing:

- ML has run hot for 5 vols and produced no record. The marginal
  EV of vol-50 doing it again is low.
- Search-side has produced records but has unfetched fruit
  (Joe's policy, McGavin's prune-restart trigger).
- If vol-50 ships the iter-budget axis cleanly and it gives nothing,
  THEN vol-51 can be RL with the engine-side `LearnedStochastic`
  with calibrated expectations.

## Linked
- [[CURRENT-VOL|CURRENT-VOL]]
- [[reinforce-plackett-luce-value-order]] — math + probe
- [[q-learning-value-order]] — earlier design
- [[prune-restart]] — existing infra
- [[vol-48]], [[vol-49]] — ES negative-result predecessors
