---
name: tunnel-pt-destroy-ladder
description: aggressiveness, not just SA temperature)
status: partial
metadata:
  type: concept
---
# TUNNEL — PT with Destroy-Aggressiveness Ladder

**Status**: `partial` (Vol-141, 2026-05-19 — built but inert in
limited benchmark)
**Origin**: Brainstorm reservoir round-4 (twist: temper destroy
aggressiveness, not just SA temperature)
**Files**:
- `crates/bench-audit/src/bin/v141_tunnel.rs`

## Algorithm

Parallel tempering with N chains, where each chain uses **different
destroy operators of varying aggressiveness**:

- Chain 0 (coldest): RandomRegion{2}, WorstWindow{3}, MwpmDefectPair{6}
- Chain 1: + ConflictDriven{20}
- Chain 2 (medium): basic preset (WorstBand{4} added)
- Chain 3: + WorstBand{6}, ConflictDriven{50}
- Chain 4 (hottest): WorstBand{8}, ConflictDriven{80}

Temperature ladder: t_min=0.5, t_max=4.0, geometric.

## Measurements

**From 461 record, 5min, seed 42**:
- 5 chains, 30 rounds, 60 exchange proposals (all 60 accepted)
- Final scores per chain: [461, 461, 461, 461, 461]
- **No improvement over 461 seed.**

## Honest interpretation

100% exchange acceptance ⇒ temperatures too close, replicas didn't
see different effective landscapes. Chains converged to the same
basin. The TUNNEL effect (replica diversity → barrier penetration)
didn't materialize.

## What's still open

- Wider temperature ladder (t_max=10+).
- Longer budget (1-4h).
- Heterogeneous repair kinds per chain.
- Stricter exchange criterion (reciprocal acceptance only).

## Linked

- [[concepts/intaglio-forbidden-patterns]]
- [[plans/EXTERNAL_BRAINSTORM_2026-05-18]]
