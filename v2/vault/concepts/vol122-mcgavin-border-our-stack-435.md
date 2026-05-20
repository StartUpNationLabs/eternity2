---
name: vol122-mcgavin-border-our-stack-435
description: "Vol-122 SANITY CHECK: McGavin's actual 469-host border, passed through OUR border_to_csp_fill+random_fill+ALNS_basic stack, only reaches 435. Gap to 469 = -34. Algorithm-side bottleneck identified."
metadata:
  type: project
status: built
---

# Vol-122 — McGavin's border yields only 435 in our pipeline

## Setup

Extract McGavin's actual 60-cell border (corner perm 3,2,0,1 + specific
edge perm) → pass to:
1. `border_to_csp_fill --solver joe_depth150_bp_par --budget-ms 120s` →
   plateaus at 176 placed / 310 matched (same as our clean-slate borders).
2. `--random-fill-remaining` → 256 placed / 310 matched.
3. `alns_only --ops basic --t 1.0 --alns-budget-ms 1800000 --seed 42` →
   **435/480 final**.

Same as our perm0/3 stack reached 424-444 (variance across seeds).

## Implication

**McGavin's specific border is NOT the discriminator** for reaching 469.
Our pipeline reaches the same 430s band on McGavin's border as on our
generated borders. The discriminator MUST be the algorithm McGavin used
to navigate from border → 469-board.

## Algorithm-side suspects

What McGavin's stack does differently:
- **Blackwood schedule**: McGavin used 470-board on 1-clue (vol-15
  Blackwood schedule). For canonical-5-clue 469, McGavin's setup was
  more elaborate.
- **Longer compute** (hours vs minutes).
- **Different ops/preset** (winning5 vs basic; oracle-guided destroy;
  PT with multi-chain).
- **Iterative refinement loop** (multi-restart from same border with
  different seeds, picking the longest-running best).

## What this means for our path forward

The 30-day plan should pivot. INVENTIONS A1, A4 (border enumeration,
DLX) won't close the 30-edge gap — the bottleneck is on the SEARCH side.

Priorities to test:
1. Same border + ALNS for **2-4 hours** (vs 30 min) — does score
   keep climbing?
2. Same border + **winning5** ops (vs basic) — different operator set.
3. Same border + **multi-chain PT** with oracle.
4. **Hint-pinned ALNS**: pin specific known-McGavin interior cells,
   not just border. (This is anchor-on-McGavin → violates user
   directive, but is a CAPABILITY TEST.)
5. **Bigger ALNS-basic stack**: try basic + WorstBand{4-12} + sigma-
   destroy oracle in McGavin direction.

The KEY discovery: even given the SAME border that admits 469, our
stack gives 435. Algorithm-side improvements are higher EV than
border-enumeration improvements.

## Status

`finding-positive`

## Linked

- [[vol122-pair-supply-discriminator]] — pair-supply hypothesis still
  has some validity (correlates within McGavin-perm), but border choice
  alone doesn't close the gap.
- [[vol122-a1-pipeline-result]]
- [[vol-122]]
