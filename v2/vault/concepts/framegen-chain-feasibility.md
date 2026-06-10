---
name: framegen-chain-feasibility
description: "framegen (vol-213): randomized BB=60 ring-cycle DFS with four interior chain-feasibility constraints checked during ring construction — eliminates the hint-incompatibility killer cells by construction. 73% hint-compatible yield vs 1% for unconstrained rings (73×). Unlocks the frame pool axis."
status: built
metadata:
  type: concept
---

# framegen — chain-feasible frame generation

**Origin**: vol-213 (2026-06-10). **Files**:
`crates/cloister/src/bin/framegen.rs`. Output: ring placement JSONs
loadable by `frame::load`; probe/census reuse `cloister2` unchanged.

## Definition

Enumerate perfect rings (BB=60 by cycle construction) with a randomized
DFS over the 60 border pieces in a path order that front-loads four
chain-check sites, each an ∃-test against the interior piece set:

1. **top-left chain** (the census killer, 311/500): ∃ distinct interior
   p0@(0,0), p1@(0,1), p2@(1,0) with p0 matching both rim targets,
   p1 matching rim-N + p0.E + hint15.N on S, p2 matching rim-W + p0.S +
   hint15.W on E.
2. **top-right chain** (89/500 at depth 13): mirrored at
   (0,12)/(0,13)/(1,13) with hint26.
3./4. **deep-hint chains**: ∃ piece for int(12,0) with W = ring(13,0)
   inward + E = deep-left-hint.W; mirrored at int(12,13).

Path: (2,0),(1,0),(0,0),(0,1)..(0,15),(1,15)..(15,15),(15,14)..(15,0),
(14,0)..(3,0), closure (3,0)-(2,0). Checks fire when their last ring
dependency lands. Per-restart shuffles + exact-placement dedup;
`--no-chains` is the control.

## Measured (vol-213, 300 frames each, 6 s hinted probe, compat = depth ≥ 20)

| pool | jam@d≤1 | compatible | depth ≥ 100 | restarts |
|---|---|---|---|---|
| chains | **0/300** | **220/300 (73%)** | 143/300 | 307 |
| no-chains control | 214/300 (71%) | 3/300 (1%) | 0 | 304 |

**73× yield.** Chain prune counts: top-left 52,658 (the binding
constraint), top-right 14,256, deep-hint 0 + 0 (single-cell ∃ over
~190 pieces is almost always satisfiable — those two checks are dead
weight at BB=60; kept since free). The control reproduces the vol-76
census baseline (0.2-1%), validating the probe.

Generation is cheap: ~1.02 restarts/frame — the constrained ring space
is abundant; ≥75k frames was a Hamilton LOWER bound and the chain
constraints cost almost nothing in ring feasibility.

## What's still open

- The band question: do generated frames escape the unguided 444-450
  band? (50-frame census with the reliable hinted recipe — vol-213
  close.)
- The 27% that still jam at depths 2-19: unencoded W-chain cells in the
  top row (probe-level filter is cheap enough that encoding more chains
  is likely not worth it).
- Witness-style deep search needs witness boards; generated frames have
  none — the unguided plateau (or future LEDGER/CAIRN-boosted miner) is
  the per-frame depth tool.

## Linked

[[cloister-ii-border-anchored]], [[replay-prior-over-cost]],
[[hamilton-frame-count]], [[vol-213]]
