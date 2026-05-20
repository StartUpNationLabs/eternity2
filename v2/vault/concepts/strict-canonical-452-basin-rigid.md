---
name: strict-canonical-452-basin-rigid
description: "Vol-118 — the 452/480 strict-canonical board from par-pipeline is basin-rigid. Bound-ascent UB=455 (only +3 above score). Hungarian re-pass yields Δ=0. ALNS polish from bound-ascent output stays at 452. The 452-basin's structural ceiling is 455. To exceed strict-canonical 457 record, need a different basin (par-bf with different seed-offset, OR different starting partial)."
metadata:
  type: project
status: built
---

# Strict-canonical 452 basin rigidity (vol-118)

**Status**: `built` — measured 2026-05-16.

## Context

Vol-118 T5b's parallel hint-preserving pipeline reaches 452/480
strict-canonical (5/5 hints OK). To check whether iterated polish
can lift to 457+:

## Test

| step                              | score | UB    |
|-----------------------------------|------:|------:|
| Initial ALNS output               |   452 |       |
| Bound-ascent on 452               |   452 |   455 |
| Hungarian on bound-ascent output  |   452 |       |
| ALNS polish (winning5, seed=200)  |   452 |       |

**The 452 basin's local UB is 455** (only +3 above the realized score).
Hungarian permutation yields Δ=0 — piece set is already locally optimal.
ALNS polish stays at 452 — no improvement in 60s.

## Implication

The strict-canonical record (457) is UNREACHABLE from this basin's
neighborhood by any local operator. Even an idealized "saturate to UB"
move would only reach 455 < 457.

To break 457, we need a DIFFERENT basin — one with UB ≥ 458. Approach:
1. Run par-bf with diverse seed-offsets (each finds a different partial).
2. Bound-ascent on the resulting Hungarian-rebuilt partial → measure UB.
3. ALNS-recover only on partials with UB ≥ 458.

## Comparison

| par-bf seed-offset | bf depth | Hungarian score | bound-ascent UB | ALNS max |
|-------------------:|---------:|----------------:|----------------:|---------:|
| 0 (60s)            |      232 |             432 |             460 |      452 |
| 200 (5min)         |      244 |             440 |             454 |  pending |

Seed-offset 0 partial had UB=460, ALNS reached 452 (gap +8 from UB).
Seed-offset 200 partial UB=454 — strict-canonical 457 STRUCTURALLY
unreachable from this basin even with perfect ALNS.

The filter "discard partials with UB < 458" is necessary for
strict-canonical record work.

## Linked

- [[parallel-hint-preserving-bf]] — the pipeline.
- [[bound-ascent]] — the UB measurement tool.
- [[hint-pin-conflict-propagation-fix]] — what unblocked this work.
- [[vol-118]].
