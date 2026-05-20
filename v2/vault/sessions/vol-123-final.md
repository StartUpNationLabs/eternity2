---
name: vol-123-final
description: "Vol-123 final summary for user. Built and validated W1/W2/W4/W7 methods. Pipeline 448 canonical, standing 458 unchanged. Path to solve = cloud W1 chi=128+."
metadata:
  type: project
---

# Vol-123 — final message for user

User's goal: **find the way to solve Eternity II**, not just records.
Cloud compute available if a real method needs it.

## What we built today (30 commits)

| Method | Status | Best canonical result |
|--------|--------|----------------------|
| W1 PEPS-Lagrangian | Solves 4×4 (1s), 6×6 (5min) | OOM at chi=32 (cloud needed) |
| W1 Rust port | Exact contraction validated 3/3 tests | (works at small scale) |
| W2 SP-Lagrangian | REFUTED on 4×4 | n/a |
| W2 plain BP | Converges in 3.6s | Marginals weak (mean 0.04) |
| W2 BP-decimation | Solves 4×4 (0.1s) | 435/480 in 11 min |
| W2 + ALNS basic | Pipeline complete | 448/480 (plateau) |
| W4 LKH-chain | Implemented | Stuck at 459 (5min) |
| W7 backbone | Measured | 1/256 frozen cells in 459 basin |

## Key insight

**Record-breaking and method-finding diverge.** Heuristics like Blackwood
(McGavin 469) don't scale to 480. The path to actually solving E2 is
"make marginals progressively more accurate" → CSP completes the rest.

W1 PEPS at chi → ∞ is exact. **The natural path: rent cloud machine,
run W1 at chi=128-256 on canonical 16×16, dump marginals, feed to CSP.**

## Concrete deliverables

Code:
- `crates/peps/` — Rust port (cell tensor + exact contraction)
- `scripts/w1_peps/` — Python W1 (production)
- `scripts/w2_sp/` — W2 SP/BP-decim toolkit
- `scripts/w7_frozen_backbone/` — W7 analysis

Documents:
- `vault/plans/SOLVING-E2-VISION.md` — 6-path strategy
- `vault/concepts/method-vs-record-divergence.md` — fundamental insight
- `vault/concepts/w1-*.md` — W1 derivation, results, scaling plan
- `vault/concepts/w2-*.md` — W2 derivation, results, pipeline analysis
- `vault/sessions/vol-123*.md` — session journals

Data:
- `output/vol-123/w2/canonical_bp_decim.json` — 435 board
- `output/v17_alns_only/basic_sa_t1_s7_*.json` — 448 lifted board
- `output/vol-123/w2/canonical_bp_marginals.json` — 134k marginals
- `output/vol-123/w7/frozen_backbone_459.json` — W7 data

## Standing 458 strict-canonical record unchanged

No record broken today, but two end-to-end candidate METHODS validated:
- W1 (PEPS at small scale) — needs cloud for canonical
- W2 (BP-decim + ALNS) — pipeline complete on canonical, plateaus at 448

## Recommended next session

1. **Rent a cloud machine** (64-128 GB RAM, e.g., AWS r6i.4xlarge for ~$1/hour).
2. **Run W1 PEPS-Lagrangian on canonical 16×16** at chi=128. Expected 1-2 days
   to convergence. Output: per-cell-piece-rotation marginals JSON.
3. **Feed marginals to W2 BP-decimation** (in place of plain BP marginals).
4. **Compare** the resulting matched-edge score against the W2-only 435.
5. If W1+W2 hybrid reaches ≥ 470, you have a record-breaking pipeline.

## Linked

- [[vol-123]] (full session journal)
- [[vol-123-close]] (definitive close)
- [[SOLVING-E2-VISION]]
- [[method-vs-record-divergence]]
