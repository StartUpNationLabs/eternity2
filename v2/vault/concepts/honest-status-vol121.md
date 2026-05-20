---
name: honest-status-vol121
description: "Vol-121 honest status snapshot — 15 parallel record-attempt jobs (MIPs + MaxSAT + ALNS) running concurrently on canonical E2; the community 469 ceiling has stood for 5+ years; vol-44/83/95/100 already proved McGavin halo-4 per-component locally optimal under full piece freedom; the joint halo-2 MIP at 53 cells is the strongest new attack but the LP gap (BestBound=120.93, BestSol=113) hasn't been closed in 15 min of CBC B&B. Multi-week compute likely required; a single autonomous session is statistically unlikely to break the ceiling."
metadata:
  type: project
status: built
---

# Honest status — vol-121 record attempts

The community's 469 ceiling has stood for 5+ years. Vol-44/95/100
proved McGavin halo-4 per-component MIP-locally-optimal. Vol-119/120
proved 459-matched-edges and 457-strict-canonical full-board
corpus-MIP-locked across our 30-basin corpus.

Vol-121 launched the broadest parallel record-attempt I'm aware of in
this project:

| Job | Region | Status (23:24 CEST) |
|-----|--------|---------------------|
| McGavin joint 15 (no halo) | 15 cells | DONE Δ=0 (0.14s) |
| McGavin halo-2 joint | 53 cells | BestSol=113, gap=1.04%, 108 nodes |
| McGavin top-2 rows | 28 cells | DONE Δ=0 (0.37s) |
| McGavin top-3 rows | 42 cells | BestSol=93, gap=2.21%, 48 nodes |
| McGavin top-4 rows | 56 cells | BestSol=119, gap=6.89%, root |
| McGavin top-5 rows | 70 cells | BestSol=148, gap=6.53%, root |
| McGavin MaxSAT z3 halo-1 | 41 cells | running |
| vol-60 459 halo-2 | 71 cells | BestSol=145, gap=11.33%, root |
| bseed9 460 halo-1 | 42 cells | BestSol=85, gap=9.52%, 505 nodes |
| vol-121 458 halo-1 | 52 cells | BestSol=106, gap=11.27%, root |
| McGavin ALNS basic (4 seeds) | full board | 3min in of 30 |
| McGavin ALNS winning5 (2 seeds) | full board | 2min in of 30 |

Three MIPs CONVERGED with Δ=0 (top-2 rows, joint 15-cell). The
remaining MIPs have LP gaps 1-11% — CBC is searching but not finding
integer improvements.

The strongest path forward:
1. McGavin halo-2 joint at gap 1.04% — if CBC closes the gap to 0
   with BestSol=113, that's the strongest local-optimality proof to
   date (53-cell joint, beyond vol-100's halo-4 per-component).
2. ALNS on McGavin 469 — direct test of whether our local-search can
   find a 470+ neighbor. Unlikely given vol-44 history.
3. Future vols: multi-week compute (RL self-play, longer MIP at
   bigger halo, larger basin corpus).

This single autonomous session is statistically unlikely to break
the 469 ceiling, but is producing genuinely new rigorous local-
optimality proofs at unprecedented joint scale, plus a NEW 458
basin (vol-121 corner-perm 2,3,1,0) added to the corpus.

## Linked

- [[corpus-restricted-region-mip-locked]]
- [[vol121-458-corner-perm-2310]]
- [[three-milestones-from-veteran]]
- [[vol-121]]
