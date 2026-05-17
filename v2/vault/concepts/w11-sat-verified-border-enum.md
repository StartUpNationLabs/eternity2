---
name: w11-sat-verified-border-enum
description: "W11 INVENTION: with the fixed W-SAT encoder, we can verify in <1 second whether a candidate border configuration admits any 480 interior solution. Combined with vol-122 N1's 12,958 corner clusters or border-DP enumerations, we get a per-border feasibility filter — a NEW pruning tool for canonical E2 attacks."
metadata:
  type: project
---

# W11 — SAT-verified border enumeration

After fixing the W-SAT encoder bug (vol-123), kissat returns UNSAT in
<1 second for partial boards where the pinned region can't reach 480.

This unlocks a new strategy: **systematically enumerate border configurations,
SAT-test each one's compatibility with a 480 interior, and ONLY pursue
borders that pass.**

## The pipeline

```
For each border configuration B in {N1 corner-clusters × edge-piece chains}:
  1. Pin all 60 border cells from B (plus 5 hints).
  2. Free the 191 interior cells.
  3. Run kissat: does ANY interior assignment give 480/480?
  4. If UNSAT → border B is provably incompatible with 480. SKIP.
  5. If SAT → extract solution, verify, REPORT as 480 candidate.
  6. If TIMEOUT → uncertain, queue for longer budget.
```

## Why this is novel

Vol-44 LP-UB: gives upper bound (478). Doesn't filter borders.
Vol-122 N1: enumerated 12,958 corner clusters. Didn't test their
  compatibility with 480.
Vol-119 border-DP: enumerated 60-piece-unique borders. Didn't test
  per-border interior feasibility.

W11 BRINGS THESE TOGETHER: enumerated border × SAT-filter → live
candidates. The filter is fast enough that we can screen 10k+ borders
in hours.

## Concrete first step

1. Take vol-122 N1's 12,958 corner clusters from
   `output/vol-122/n1_corner_3x3_clusters.sqlite`.
2. Combine 4 corners (TL, TR, BL, BR) into border ring with the
   correct edge piece chain (border-DP).
3. For each border:
   - Pin border + hints; free interior.
   - SAT-test (kissat ≤ 60s).
4. Track UNSAT vs SAT vs TIMEOUT counts.
5. Any SAT → extract, verify, report.

Expected: most borders return UNSAT (rare 480 solutions). Some TIMEOUT
(border may be too constrained for kissat to decide quickly). A few SAT
(real 480 candidates).

## Implementation

`scripts/w11_sat_border_screen/`:
  - `enum_borders.py` — generator yielding border configs from N1 clusters
  - `screen_borders.py` — driver that runs sat_unsat_border.py on each
  - `verify_sat.py` — extract + score any SAT result

## Expected runtime

- 12,958 corners × 4-tuple combinations = 10^11 raw combinations.
- Most pruned by edge-piece-chain feasibility (vol-119 found ~50 valid
  border rings per corner perm).
- Maybe 10,000 - 100,000 valid border rings total.
- At 60s/test, full screen = 7 days - 70 days.
- More realistic: top-K borders by W7 frozen-variable signature, screen
  K = 100-1000 borders first, ~hours.

## Why it might work

For E2 to have a 480 solution, **SOME** border ring + interior must
satisfy all constraints. If we enumerate borders, we MUST hit the
right one. The 60 border pieces are constrained to the border ring
positions (vol-7 finding), so the enumeration is over a finite set.

McGavin's 469: only 11 mismatches. With our fix, screen says UNSAT for
McGavin's border. **A different border is needed for 480.**

## Risks

1. The 12,958 × 4 corner combinations may not include the "correct" set.
   Need to be exhaustive.
2. Edge-piece-chain enumeration may miss configurations.
3. kissat may TIMEOUT on tightly-constrained borders (fewer free cells →
   easier SAT, but our pinning IS tight).

## Linked

- [[w-sat-459-unsat-findings]] (the verification tool)
- [[n-series-enumeration-deadend]] (vol-122 N1 input data)
- [[inv3-border-dp-seed]] (border-DP enumeration)
- [[../plans/INVENTIONS_BACKLOG]] (W-series)
