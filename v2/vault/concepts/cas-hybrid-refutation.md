# CAS-prefix + ALNS-suffix hybrid: 418/480 — vol-74 refutation

**Status**: `built` (negative result) — vol-74 (2026-05-15).

## Test

Run CAS to get shells 0-2 (156 cells, 252/252 matched). Pin these,
run standard ALNS (120s, winning5, seed=1) on remaining 100 inner cells.

Result: 418/480 (= 252 from outer + 166 ALNS-filled inner edges).

## Compared to alternatives

| pipeline | score |
|---|---|
| CAS (greedy all 8 shells) | 433/480 |
| CAS-outer-3 + ALNS-inner | 418/480 |
| Standard ALNS pipeline | 459/480 |
| McGavin (Blackwood algorithm) | 469/480 |

CAS-hybrid is WORSE than pure CAS and WORSE than standard ALNS.

## Why?

CAS's shell-2-perfect commit is suboptimal globally. The pieces
used in shells 0-2 (156 frame+adjacent pieces) constrain the inner
100 cells in ways that prevent ALNS from reaching 459-class.

Standard ALNS pipeline finds frame+outer configurations that are
NOT 100% matched in MIP-sense but admit BETTER inner completions.

## Lesson

Greedy outer-perfect is NOT the right strategy. The puzzle requires
HOLISTIC consideration — outer choices must be made with awareness
of inner needs.

This rules out CAS-prefix hybrid pipelines.

## Linked

- vault/concepts/cas-greedy-433-result.md (parent: pure CAS)
- vault/concepts/concentric-annular-solving.md (concept)
