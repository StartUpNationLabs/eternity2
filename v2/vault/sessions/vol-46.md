# Vol-46 — CP+LP-UB skeleton + 479-UB basin discovery + lock proof

**Theme**: Build the CP-with-LP-UB-pruning frontier from vol-45's
design doc. Run broader LP UB sweep to find basins with UB > 478.

**Status**: shipped skeleton + discovered first 479-UB basin + proved
it locked. Multi-day frontier identified.

## What was built

- `crates/cp-lp-search/` crate — new workspace member.
- Library primitives:
  - `perimeter_placement_order` (60-cell clockwise order)
  - `valid_border_candidates` (corner/edge filter + outward-BORDER check)
  - `neighbor_b_b_compatible` (B-B color match constraint)
  - `b_b_matches` (count B-B matches in partial board)
  - `cheap_lb_passes` (Hall-condition prune)
  - `run_cp_lp_search` (depth-first driver)
  - `partial_lp_ub` (stub — requires LP refactor for empty perim)
- Bin: `cp_search` — 60s smoke test: 1.27M nodes explored, 116k
  perfect-bb leaves found (Hall never violated).

## Discoveries

### D1. First LP-UB-479 basin

`output/v17_alns_only/winning5_sa_t1_s1_1778670467.json`:
- Score 457 (currently)
- bb=60, bi_ub=55.48, ii_ub=363.52, **total UB = 479**

**This is the first basin in our archive with LP UB > 478.** The 478
cap from vol-44/45 was a sample artifact.

Per `board_diff`: essentially disjoint from class A and class B
(< 5/256 same cells). New family — call it **class D**.

### D2. Class D basin is locked at 457

- 8 ALNS-diverse seeds × 1h: all 8 plateau at 457.
- MIP on 28-cell union of all 10 mismatch clusters: delta=0 in 0.46s.
  **Proven locally optimal at 457.**

### D3. LP UB doesn't predict integer optimum

Cross-basin pattern:
| Class | LP UB | Integer best | Gap |
|---|---:|---:|---:|
| A | 478 | 458 | 20 |
| B | 477 | 457 | 20 |
| C | 476 | 457 | 19 |
| **D** | **479** | **457** | **22** |

**Every basin has ~20-point LP-integer gap that local search can't
close.** Finding higher-LP-UB basins doesn't directly help with
record-breaking — they're still locked at similar absolute scores.

### D4. v17_alns_only contains many untested basins

Of 12 v17_alns_only reps tested in vol-46: 1 hit 479+ (8% rate).
Of 561 total v17_alns_only files: ~561 × 8% ≈ 45 untested
479+ candidates (if rate holds). But finding them is low-EV given D3.

## What this changes about strategy

The fundamental obstruction is **NOT** LP UB ceiling. It's **the
integer-LP gap within each basin**. Finding higher-UB basins helps
the LP relaxation see further but doesn't help integer optimization.

**To break 458, need either**:
- A basin with much smaller LP-integer gap (none observed in 18+ tests).
- Multi-day MIP that closes the gap (1h MIP doesn't suffice).
- Fundamentally different algorithm (RL, CDCL, custom propagator).

## Deferred frontiers

- **Leaf-time LP UB filter in cp-lp-search**: LP at every leaf takes
  150s, infeasible at 116k leaves/min. Cheap proxies (Hall) don't
  violate. Need different design — sampling or property-targeted.
- **Multi-day RL self-play** (vol-30 T2, still deferred).
- **No-good CDCL learning** in solver-engine.
- **MIP with weeks-scale budget** on specific basins.

## Linked

- [[lp-ub-479-basin-found]] — D1 discovery
- [[479-basin-context]] — D2 + D3 analysis
- [[lp-ub-478-basins]] — vol-44/45 basin survey
- [[cp-with-lp-ub-pruning]] — design doc
- [[vol-45]] — predecessor
