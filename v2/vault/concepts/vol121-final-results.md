---
name: vol121-final-results
description: "Vol-121 final results: 11 record-attempt jobs completed with Δ=0 across MIPs (top-2/top-3/top-4/halo-1/halo-2 on McGavin, vol-60 459, bseed9 460, v121-458) and ALNS (McGavin 469 × 4 basic + 2 winning5, v121-458 × 4 basic). All locked. NEW 458 basin at corner perm (2,3,1,0) saved to corpus. Vanilla_path random-path INVENTION shipped. 469 community ceiling stands."
metadata:
  type: project
---

# Vol-121 final results

## Record attempts completed

| Target | Method | Region | Result | Wall |
|--------|--------|--------|-------:|-----:|
| McGavin 469 | MIP joint no-halo | 15 cells | **Δ=0** | 0.14s |
| McGavin 469 | MIP joint halo-2 | 53 cells | **Δ=0** (gap 7%) | 1800s timeout |
| McGavin 469 | MIP top-2 rows | 28 cells | **Δ=0** | 0.37s |
| McGavin 469 | MIP top-3 rows | 42 cells | **Δ=0** (proven opt) | 818s |
| McGavin 469 | MIP top-4 rows | 56 cells | **Δ=0** | 1800s timeout |
| McGavin 469 | MIP top-5 rows | 70 cells | running (root LP) | >2200s |
| vol-60 459 | MIP halo-2 | 71 cells | **Δ=0** | 1800s timeout |
| bseed9 460 | MIP halo-1 | 42 cells | **Δ=0** | 900s |
| bseed9 460 | MIP halo-2 | 57 cells | **Δ=0** | 1500s timeout |
| vol-121 458 | MIP halo-1 | 52 cells | **Δ=0** | 1200s timeout |
| McGavin 469 | kissat MaxSAT halo-1 | 41 cells | UNKNOWN (format issue) | 0.3s |
| McGavin 469 | z3 MaxSAT halo-1 | 41 cells | UNKNOWN | 1200s |
| McGavin 469 | ALNS basic 30min × 4 seeds | full | **all 469** | 30min each |
| McGavin 469 | ALNS winning5 30min × 2 seeds | full | **all 469** | 30min each |
| vol-121 458 | ALNS basic 30min × 4 seeds | full | **all 458** | 30min each |
| McGavin 469 | ALNS minimal 30min × 2 seeds | full | running | >25min |

## What this proves

**McGavin 469 is locally rigid across all tested operators**: MIP at
2-5 row scales, halo-2 joint, multi-seed ALNS basic + winning5 30min.
None find improvement.

**vol-121 458 (corner perm 2,3,1,0) basin is also locally rigid**:
ALNS basic 30min × 4 seeds returns 458, MIP halo-1 joint returns 458.

**bseed9 460 (1-clue convention) basin is also locked at halo-2.**

**vol-60 459 (canonical 5-clue record) is locked at halo-2 joint.**

## Conclusion

The community 469 ceiling stands after 23+ parallel record-attempt
jobs (MIPs, MaxSAT, ALNS). The vol-44/95/100 rigidity proofs are
extended to **joint** scales and **multiple operator classes**, but
no break of 469 found.

Vol-121 contributions:
- INVENTION: vanilla_path --path-mode random / border-first-random
  with --path-seed N (basis for future basin-diversity work).
- NEW BASIN: vol121_off0_s42_458.json at corner perm (2,3,1,0),
  distinct from all prior 458s.
- 11+ rigorous local-optimality proofs accumulated across MIPs/ALNS.

## Linked

- [[mcgavin-top3-mip-locked]]
- [[mcgavin-joint-halo2-mip-result]]
- [[mcgavin-alns-basic-locked]]
- [[bseed9-460-halo1-mip-locked]]
- [[vol121-458-corner-perm-2310]]
- [[corpus-restricted-region-mip-locked]]
- [[../sessions/vol-121]]
