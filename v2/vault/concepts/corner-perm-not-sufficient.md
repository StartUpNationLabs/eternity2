---
name: corner-perm-not-sufficient
description: REFUTATION — forcing McGavin's corner perm (3,2,0,1) on our pipeline gives only 427/480, not 460+. The perm choice ALONE is not sufficient to reach McGavin's 469. Confirms his algorithm's PATH matters, not just perm class.
metadata:
  type: project
status: built
---

# Corner perm (3,2,0,1) is NOT sufficient to reach 469 (vol-103)

**Status**: `built` — measured 2026-05-16 ~06:10.

## Hypothesis tested

Per [[corner-perm-score-distribution]]: across 1156 boards, only
McGavin's perm (3,2,0,1) reached 469. Hypothesis: forcing this
perm on our pipeline should also reach high scores.

## Method

1. Took p22 partial from vol-60 sweep (CP partial with TL=3 + TR=2
  pinned, 136 cells placed, score ~245).
2. Modified JSON to ADD BL=0 + BR=1 pins at positions 240, 255
  (with correct rotations).
3. Ran `alns_only` with all 4 corner positions in `--extra-hint`
  (pinning them), 10-min ALNS, seed 42, ops=winning5.

## Result

**Best score reached: 427/480** (iter 244 of ALNS, in 10 minutes).

Compare:
- Our local 459 record: perm (1,0,2,3), reached 459 via vol-60 +
  ALNS basic 30min seed 42.
- McGavin 469: perm (3,2,0,1), reached via Blackwood algorithm
  weeks of compute.

## Refutation

The corner perm alone is NOT sufficient. McGavin's 469 came from
his algorithm's specific path through the perm's basin — break-
index schedule, heuristic-side exhaustion, 295M nps engine. Our
pipeline (vanilla_fast + ALNS) cannot match it.

This refines the structural reading: corner-perm IS a determinant
of which basin family is reachable, but the **algorithm matters
more than the perm** for actually reaching the high-score basin
within a perm class.

## Implications

- Don't expect to reach 469 by forcing McGavin's perm.
- McGavin's algorithm (Blackwood-class, port libblackwood) remains
  the bottleneck.
- The 23 other perm classes might also have hidden 469-class
  basins, but our pipeline can't find them either.

## Linked

- [[corner-perm-score-distribution]] (the original hypothesis)
- [[basin-corner-permutations]]
- [[IDEAS_FROM_BLANK_2026-05-16|IDEAS_FROM_BLANK]] (port libblackwood is the unblock)
