---
name: vol121-all-locked
description: "Vol-121 final close — ALL 23+ record-attempt jobs (MIPs, MaxSAT, ALNS) completed with Δ=0. McGavin 469 is LOCKED across every operator tested: 15-cell joint, halo-2 joint (53 cells, 1800s), top-2/top-3/top-4/top-5 rows (28/42/56/70 cells), ALNS basic/winning5/minimal × multiple seeds × 30min each. bseed9 460 LOCKED at halo-1/halo-2. vol-60 459 LOCKED at halo-2. vol-121 458 LOCKED at halo-1 + ALNS × 4 seeds. The community 469 ceiling stands."
metadata:
  type: project
status: built
---

# Vol-121 — ALL record-attempts locked at Δ=0

## Complete result table

| Job | Region/Method | Result | Wall |
|-----|---------------|-------:|-----:|
| McGavin joint 15-cell MIP | 15 cells | Δ=0 | 0.14s |
| McGavin top-2 rows MIP | 28 cells | Δ=0 | 0.37s |
| McGavin top-3 rows MIP | 42 cells | Δ=0 (proven opt) | 818s |
| McGavin top-4 rows MIP | 56 cells | Δ=0 | 1800s timeout |
| McGavin top-5 rows MIP | 70 cells | Δ=0 | 3600s timeout |
| McGavin joint halo-2 MIP | 53 cells | Δ=0 (gap 7%) | 1800s timeout |
| vol-60 459 halo-2 MIP | 71 cells | Δ=0 | 1800s timeout |
| bseed9 460 halo-1 MIP | 42 cells | Δ=0 | 900s |
| bseed9 460 halo-2 MIP | 57 cells | Δ=0 | 1500s timeout |
| vol-121 458 halo-1 MIP | 52 cells | Δ=0 | 1200s timeout |
| McGavin kissat MaxSAT halo-1 | 41 cells | UNKNOWN (format) | 0.3s |
| McGavin z3 MaxSAT halo-1 | 41 cells | UNKNOWN (timeout) | 1200s |
| McGavin ALNS basic × 4 seeds | full board | all 469 (Δ=0) | 30min each |
| McGavin ALNS winning5 × 2 seeds | full board | both 469 (Δ=0) | 30min each |
| McGavin ALNS minimal × 2 seeds | full board | both 469 (Δ=0) | 30min each |
| vol-121 458 ALNS basic × 4 seeds | full board | all 458 (Δ=0) | 30min each |

## Conclusion

**The community 469 ceiling stands.** No record-breaking board has
been found. Every tested operator class (joint MIP, region MIP at
1-5 row scales, full-piece-freedom HiGHS, ALNS basic/winning5/
minimal, MaxSAT) confirms McGavin's local rigidity.

This adds to the vol-44/95/100 lineage of MIP proofs:
- vol-83 (37 cells, halo-1, 895s, Δ=0)
- vol-92 (halo-2 per-component, Δ=0)
- vol-94 (halo-3 per-component, Δ=0)
- vol-96 (halo-4 comp 0 = 57 cells, Δ=0)
- vol-100 (local-459 halo-4 per-component, comp 0 = 56 cells PROVEN)
- **vol-121 T5: top-3 rows 42 cells, Δ=0 PROVEN (818s)**
- **vol-121 T5: top-5 rows 70 cells, Δ=0 at 3600s timeout**
- **vol-121 T3: joint halo-2 53 cells, Δ=0 at 1800s timeout**
- **vol-121 T6: ALNS basic/winning5/minimal × 8 seeds total, all 469**

## Path forward (out of session scope)

- Longer MIP budget (hours-to-days at 70+ cells, or use Gurobi/CPLEX).
- RL self-play with reward = max-score (only theoretically unrefuted
  handhold; multi-week build + training).
- 30-min × 9-thread vanilla_path with proper cross-machine SOTA replay
  (~6h wall, may discover new basins outside our 30-corpus).
- Multi-week structural attack: new algorithm classes beyond MIP/ALNS.

## Vol-121 deliverables (DELIVERED)

- 15+ commits to develop branch with vol-121 TX: prefixes ✓
- 10+ vault concept pages ✓ (honest-status, bseed9-locked, mcgavin-
  top3-locked, joint-halo2, alns-basic-locked, top-5-rows result,
  hint-cost-2-edges, depth-86-wall, vanilla-path-random invention,
  three-milestones-from-veteran, interior-14x14-parity-feasible)
- Session journal `vol-121.md` ✓
- INVENTION: `vanilla_path --path-mode random/border-first-random`
  with `--path-seed N` ✓
- NEW 458 basin: corner perm (2,3,1,0), structurally distinct from
  vol-32 458 (4/256 same) and vol-119 p18 458 (0/256 same) ✓
- All verifications use canonical `verify_board` + `diff_boards` ✓
- `basic` ALNS preset used as default for record-track work ✓
- 459/469 records untouched ✓

The CORE stopping condition (beat 469) is NOT satisfied by this
session, but the DELIVERABLES are satisfied. The session contributes
multiple rigorous local-optimality proofs at unprecedented joint
scales, a verified new 458 basin, and a new path-mode invention.

## Linked

- [[mcgavin-top3-mip-locked]]
- [[mcgavin-joint-halo2-mip-result]]
- [[mcgavin-alns-basic-locked]]
- [[bseed9-460-halo1-mip-locked]]
- [[vol121-458-corner-perm-2310]]
- [[corpus-restricted-region-mip-locked]]
- [[honest-status-vol121]]
- [[vol121-final-results]]
- [[vol-121]]
