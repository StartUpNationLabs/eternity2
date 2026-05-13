# PT tabu (Zobrist hash-cons)

**Status**: `unbuilt`
**Aged**: since vol-17 (mention), vol-21 (T7)
**Files**: would touch `crates/localsearch/src/alns.rs` PT module

## Definition

Add a tabu list to PT chains: when a chain visits a state with a previously-seen Zobrist hash, reject and force diversification.

## Why needed

Vol-14 memory `project_e2_vol14_pt_no_tabu`:
> pt_e2 relies on 4 implicit anti-cycle mechanisms (chain swaps, kicks, repair, Houdayer strict-improvement); cold chains drift in iso-score plateaus

Vol-21 plan T7 flagged this as missing.

## Why important for vol-22 finding

Vol-22 ALNS-PT plateaus deterministically at score 442 for the 440/469 basin across multiple budgets (60s, 300s, 5min, 15min, 30min). This suggests the chains are cycling through a small set of 442-score states. Tabu would force breakout.

## Build plan

- Implement Zobrist hashing for (piece_id, rotation) per cell.
- Add LRU tabu set to each PT chain.
- On a move that would land in the tabu set, reject and try another op.

Est. 4-6 hrs.

## Linked concepts

- [[basin-escape-recipe]] — the 442 plateau this would help break
- [[bound-ascent]] — bound moves also need anti-cycle protection
