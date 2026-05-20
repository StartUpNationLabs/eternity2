---
name: pt-tabu
description: Add a tabu list to PT chains: when a chain visits a state with a previously-seen Zobrist hash, reject and force diver...
status: wont-do
metadata:
  type: concept
---
# PT tabu (Zobrist hash-cons)

**Status**: `wont-do` (resolved at vol-24 open)
**Aged**: since vol-17 (mention), vol-21 (T7), vol-22 (T?), vol-23 (T2)
**Files**: would have touched `crates/localsearch/src/alns.rs` PT module

## Definition

Add a tabu list to PT chains: when a chain visits a state with a previously-seen Zobrist hash, reject and force diversification.

## Why it was deferred 5 volumes

Vol-14 memory `project_e2_vol14_pt_no_tabu`:
> pt_e2 relies on 4 implicit anti-cycle mechanisms (chain swaps, kicks, repair, Houdayer strict-improvement); cold chains drift in iso-score plateaus

The hypothesis was that cycling caused the iso-score plateaus we kept hitting, and tabu would force breakout.

## Vol-24 decision: `wont-do`

The vol-22 saturation scan refutes the help-hypothesis. ALNS-PT plateaus at score 442 on the 440/469 basin across **60s, 300s, 5min, 15min, AND 30min** budgets — not just a small range. If the plateau were caused by chain cycling, longer wall-time would let chains escape eventually; instead the plateau is monotone-tight in budget.

The right interpretation: **442 is the saturation gap of ALNS's repair operators on a 440/469 basin, not a cycling artefact**. Tabu fights cycling. Cycling is not the binding constraint. So tabu cannot raise 442.

Symptom-vs-cause: tabu addresses "chains revisit states" (a symptom of weak operators on saturated regions). The cause is that ALNS's destroy-repair operators max out at the same gap regardless of how long you run them. Adding tabu would force chains to wander to *strictly worse* states (since strictly-better states aren't reachable from the saturated 442 cluster), which then snap back to 442 on the next strict-improvement move (Houdayer behaves this way by design).

## When to revisit

Only if a stronger repair operator (prune-restart-as-score-maximizer, McGavin-style global rerun, or component-sized k≥8 destroy) raises the plateau above 442 *and* PT chains start showing visible cycling. Tabu without a barrier-crossing operator first is treating the symptom.

## Linked concepts

- [[basin-escape-recipe]] — the 442 plateau which tabu would NOT have broken
- [[bound-ascent]] — bound moves also iso-score; same null applies
- [[prune-restart]] — the kind of upstream-repair work that would have to happen first
- [[score-optimizing-cp]] — vol-24 attempt at sharpening CP as a stronger repair
