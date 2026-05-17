---
name: vol-123-close
description: "Vol-123 definitive close. Builds: W1 PEPS-Lagrangian (solves 4×4/6×6), Rust port (exact contraction works, chi-trunc TODO), W2 BP-decimation (canonical 16×16 → 435 in 11min, +ALNS → 448), W4 LKH-chain (built, no record-class lift), W7 backbone analysis. Standing 458 strict-canonical unchanged. Path to solve: cloud W1 chi=128+ for stronger marginals."
metadata:
  type: project
---

# Vol-123 — definitive close

## What we wanted

User clarified mid-session: find **the way to solve** Eternity II, not
incremental record-breaking. Cloud compute on the table if a real
algorithmic candidate needs it.

## What we built and validated

### W1 PEPS-Lagrangian (Tier S — leading candidate)

Math derivation: vault/concepts/w1-peps-design-derivation.md.
Encoding C resolves the vol-13 piece-uniqueness obstruction via Lagrangian
dual on per-piece supply constraint.

Empirical results:
- 4×4 generated: complete solve in **1 second** (verified 16/16 pieces).
- 6×6 generated: complete solve in **5 minutes** (verified 36/36).
- Canonical 16×16: **OOM at chi=32 on laptop**. Needs cloud (64-128 GB).

Rust port progress:
- Cell tensor builder: parallel via Rayon. **3/3 tests pass**.
- Exact contraction (no chi truncation): **3/3 tests pass on 2×2, 4×4, 6×6**.
- Chi-truncated boundary MPS: correct but doesn't save memory (TODO).

### W2 BP-decimation (Tier B — works at canonical scale)

Pipeline:
1. Build factor graph: cells as multi-class variables, color-match factors.
2. Run plain BP (no Lagrangian).
3. Greedy decimation: fix most-confident cell, re-run BP.
4. Result: 256-cell partial board.
5. ALNS basic 10min lift × 4 seeds.

Canonical 16×16 results:
- BP-decim alone: **435/480 matched** in 11 minutes
- + ALNS basic 10min: **448/480** (best seed)
- + ALNS basic 30min extension: **still 448** (no further improvement)

Conclusion: W2 BP gives weak marginals (mean_max_prob = 0.04 on canonical).
Decimation forces low-confidence guesses. Result is comparable to vanilla
CSP cold-start. Not record-class.

### W4 LKH-chain operator (Tier C — operator portfolio addition)

`crates/localsearch/src/alns.rs`: LkhChainDestroy. Adaptive-cardinality
gain-chain destroy (vs fixed-K like other ops). Available as `basic_lkh`
and `lkh_only` presets in alns_only.

Tested on 459 basin × 4 seeds × 5min: **all stuck at 459** (same as basic).
LKH doesn't break the K≤5 operator-lock at short budget.

### W7 frozen-variable backbone analysis

47 boards at matched=459 analyzed.
- **1 frozen cell out of 256** (= (1, 15) piece 56 rot 1)
- 76.6% of cells have exactly 3 distinct piece-rotations
- Confirms vol-20 "no deep backbone in 459 basin" empirically.

### W2 SP-Lagrangian REFUTED

Attempted SP-style BP with Lagrangian on piece-uniqueness on 4×4.
**Does not converge** — BP zeros out some pieces structurally; Lagrangian
cannot recover them.

The Lagrangian trick (which works for tensor-network methods W1) does NOT
generalize to BP-based methods, because BP itself is too lossy.

## Strategic documents produced

- `vault/plans/SOLVING-E2-VISION.md` — 6-path strategy doc
- `vault/concepts/web-roam-2026-05-17.md` — web roam for new candidates (W1-W8)
- `vault/concepts/w1-was-it-promising.md` — honest W1 assessment
- `vault/concepts/method-vs-record-divergence.md` — fundamental insight
- `vault/concepts/w1-peps-design-derivation.md` — W1 math
- `vault/concepts/w1-peps-empirical-results.md` — W1 results
- `vault/concepts/w1-canonical-scale-plan.md` — W1 scaling
- `vault/concepts/w2-sp-for-e2-derivation.md` — W2 math
- `vault/concepts/w2-sp-empirical-result.md` — W2 results
- `vault/concepts/w2-bp-pipeline-result.md` — W2 pipeline analysis
- `vault/concepts/n-series-enumeration-deadend.md` — close of N-series

## Concrete artifacts

- `output/vol-123/peps/marginals_8x8_chi64.json` (W1, partial)
- `output/vol-123/w2/canonical_bp_decim.json` (W2, 435 matched)
- `output/v17_alns_only/basic_sa_t1_s7_*.json` (W2+ALNS, 448 matched)
- `output/vol-123/w2/canonical_bp_marginals.json` (W2 marginals, 134k)
- `output/vol-123/w7/frozen_backbone_459.json` (W7 analysis)
- `crates/peps/` — Rust port (exact contraction working)
- `scripts/w1_peps/peps_quimb_lagrangian.py` (Python W1 production)
- `scripts/w2_sp/sp_e2.py` — W2 BP solver
- `scripts/w2_sp/bp_decimation.py` — greedy decimation
- `scripts/w2_sp/bp_confident.py` — threshold-based variant

## Standing record

**458 strict-canonical (5/5 hints obeyed) from vol-122 UNCHANGED.**

No new record today. The W2 pipeline (448) is below standing.

## Path to actually solving (next sessions)

1. **Days 1-3: Cloud W1 canonical** at chi=128-256 with 64-128 GB RAM.
   - Single Lagrangian dual round. Output: per-cell marginals JSON.
   - Cost: ~$50-100 cloud.

2. **Days 4-7: F1 hybrid**. W1 marginals → solver-engine CSP value-order.
   - Compare against W2 BP marginals baseline.
   - Target: 50%+ interior reduction (vol-12 BP gave 18.84%).

3. **Days 8-14: W3 Kovalsky-Glasner Vandermonde-LP**.
   - Different relaxation (algebraic vs tensor-network).

4. **Days 15-21: Backtracking-SP (Marino-Parisi 2016)**.
   - Add backtracking to BP-decim to escape low-confidence wrong commits.

5. **Days 22-28: GBP / region-based BP**.
   - Pair-cluster marginals capture stronger correlations than 1st-order BP.

The "way" to solve: **make marginals progressively more accurate**.
W1/PEPS at chi → ∞ is exact. With cloud compute, chi=128-256 should be
enough to get marginals strong enough to drive CSP to completion.

## Linked

- [[vol-122]] (previous session)
- [[../plans/SOLVING-E2-VISION]]
- [[../plans/INVENTIONS_BACKLOG]]
- [[../concepts/w1-was-it-promising]]
- [[../concepts/method-vs-record-divergence]]
