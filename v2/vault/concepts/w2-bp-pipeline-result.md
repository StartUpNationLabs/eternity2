---
name: w2-bp-pipeline-result
description: "W2 BP-decimation pipeline: validated end-to-end on canonical 16×16 Eternity II. BP-decim gives 435/480 in 11 min; ALNS basic lifts to 448 in 10 min more. The full pipeline (~50 min) gives 448 matched. Not a record but a real CANDIDATE METHOD."
metadata:
  type: project
---

# W2 BP-decimation pipeline — canonical 16×16 result

## End-to-end pipeline tested 2026-05-17

```
canonical E2 puzzle (16×16, K=24, 5 hints)
  │
  ▼ (pin 5 canonical hints)
SP factor graph (cell multi-class variables, color-match factors)
  │
  ▼ (BP-decimation, ~11 min)
256-cell partial board with 435/480 matched edges
  │
  ▼ (ALNS basic 10min × 4 seeds, in parallel)
Best lift: 448/480 (seed 7)
```

Total time: ~50 minutes.

## Why it works (and why it doesn't break the record)

**It works because**:
- BP correctly identifies the constraints from hints + propagates them.
- Color-match factors are LOCAL (2-cell), well-suited to BP.
- Greedy decimation commits to the highest-confidence cell each round.
- ALNS then explores neighborhoods around the BP-found basin.

**It doesn't break the record because**:
- BP's marginals are WEAK at canonical scale (mean max_prob = 0.04).
- Early commits (prob ~0.1-0.3) are essentially guesses.
- Once you commit to wrong cells, downstream BP marginals reinforce errors.
- ALNS can fix local mistakes but not many at once → +9 to +13 lift.

## Full ALNS lift testing (final results)

| Preset | Time | Start | Best result | Lift |
|--------|------|-------|-------------|------|
| basic | 10 min × 4 seeds | 435 | 448 (s=7) | +13 |
| basic | 30 min × 2 seeds | 448 | 448 (no improvement) | 0 |
| winning5 | 10 min × 4 seeds | 435 | 447 (s=1) | +12 |

**Plateau confirmed at 448.** ALNS basic 30 min on 448 stuck — 6× more
iterations gives no improvement. The basin around 448 is operator-locked.

## Comparison with other methods

| Method | Total time | Best matched | Notes |
|--------|-----------|-------------|-------|
| McGavin 469 (community) | 12 days | 469/480 | Blackwood algorithm |
| Our 459 (vol-60) | hours | 459/480 | Pipeline + ALNS |
| Our 458 strict-canonical (vol-122) | hours | 458/480 | All 5 hints obeyed |
| vol-12 BP value-order + CSP | minutes | 442/480 | BP just gives value-order |
| vanilla CSP cold | minutes | ~445/480 | No BP |
| **W2 BP-decim alone** | 11 min | **435/480** | Greedy commit |
| **W2 BP-decim + ALNS basic** | 50 min | **448/480** | New combination |

W2 BP-decim + ALNS reaches matched-edges comparable to vanilla CSP + ALNS.

## What the negative result tells us

**The big learning**: BP marginals on canonical E2 are TOO WEAK to drive a
record-class solve.

Reason: the 22-color edge-matching constraint has too many "almost
consistent" assignments. BP cannot distinguish them. Vol-12 already showed
this (18.84% interior reduction); W2 confirms at canonical scale.

The only way W2-style decimation could break records is with **stronger
marginals**, which means:
- W1 PEPS marginals (chi-truncated, computed on cloud) — pending
- W3 Vandermonde-LP marginals — never built
- Some quantum-inspired stronger marginal computation

## What to do next

1. **Cloud W1 PEPS at chi=128-256 on canonical**.
   - Output: per-cell-piece-rotation marginals.
   - These should be MUCH stronger than BP (PEPS captures piece-uniqueness).
   - Then re-run BP-decim with PEPS marginals replacing BP marginals.

2. **Backtracking-SP (Marino-Parisi 2016)**.
   - Adds backtracking when BP-decim gets stuck.
   - Could break out of the 448 basin.

3. **Stronger value-order in solver-engine CSP**.
   - Use BP-decim's 435 as a *hint set* (frozen) and CSP-fill the rest.
   - vs. ALNS, this is exact search constrained to the BP-decim region.

## Code artifacts

- `scripts/w2_sp/sp_e2.py` — SP solver core (multi-class BP messages).
- `scripts/w2_sp/bp_decimation.py` — greedy BP-decim algorithm.
- `scripts/w2_sp/bp_confident.py` — threshold-based variant.
- `scripts/w2_sp/export_marginals.py` — dump BP marginals to JSON.
- `scripts/w2_sp/verify_partial.py` — verify partial board outputs.
- `output/vol-123/w2/canonical_bp_decim.json` — the 435 board.
- `output/v17_alns_only/basic_sa_t1_s7_*.json` — the 448 lifted board.

## Linked

- [[w2-sp-for-e2-derivation]]
- [[w2-sp-empirical-result]]
- [[w1-peps-design-derivation]] (the PEPS analog)
- [[bp-marginals]]
- [[edge-bp-measurement]]
- [[SOLVING-E2-VISION]]
