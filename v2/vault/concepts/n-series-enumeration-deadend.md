---
name: n-series-enumeration-deadend
description: "Vol-122 evening N-series (N1-N11) explored exhaustive enumeration of 3×3/4×4 corner/center clusters. Bottom-line: spaces are too large to enumerate, cross-products too large to store. Pipeline cap: ~50M 3×3 around-hint per positioning. Session closed with cleanup."
metadata:
  type: project
---

# N-series enumeration → computational dead end

## Sequence built (2026-05-17 late evening)

- **N1**: corner 3×3 clusters with all 12 internal edges matched. **12,958 clusters** stored in SQLite. Successful, useful seed dataset.
- **N2**: 4-corner combinations with piece-disjoint check. Raw space 1.08×10^14, ~1% piece-disjoint → ~10^12 valid 4-tuples. **Not enumerable**.
- **N3, N4**: feasibility checkers with L1+border-reachability+hint-(8,7) neighborhood. Found all L1-passing 4-tuples also pass these = filters don't filter. **Refuted as discriminators**.
- **N5**: extended 3×3 + 5-cell row/col strips. Exploded to 5.7 GB SQLite within minutes on position TL alone. **Killed for unbounded growth**.
- **N6**: tight 4-chain joint backtracker. Hit exponential dead-zones on some tuples, threads stuck for minutes. **Killed**.
- **N7**: pre-enumerate all valid 10-cell border-segment paths per (start, end) color pair. Single direction took >12 min single-threaded. **Killed**.
- **N8**: streaming sampler architecture (no full enumeration). Built but not run.
- **N9**: 4×4 around-hint enumerator. **Yielded 3M+ in 60 sec on position alone**, exploded SQLite via transaction-buffer growth. Math estimated 5e9 to 1e11 total. **Killed**.
- **N10**: 3×3 around-hint with periodic-commit. Better disk behavior. Position 0 alone yielded 11M+ in ~3 min, projection to 50M+ for position 0 → 200-500M for all 9 → 15-30 GB SQLite. **Killed**.
- **N10b**: producer-consumer split (Rust raw-bytes writer + Python sidecar SQLite indexer). Architecture excellent: 78k/sec sustained without lock contention. Position 0 reached 41M rows / 2.4 GB SQLite in ~9 min before manual stop.
- **N11**: cross-product joiner (4 corners × center 3×3) → 45-cell partial board sampler. Built but not run.

## Architectural lessons

1. **Single-transaction SQLite + 5M+ inserts = killer**. Either commit periodically OR producer-consumer split.
2. **Tight backtrackers on 4-chain joints have exponential worst-case branches**. Node budget needed to prevent stalls.
3. **Filters that ALWAYS pass don't filter**. L1 (piece-disjoint) + structurally weak loose checks gave ~7% L1-pass rate and ~100% loose-pass rate.
4. **Cross-product enumeration of independent local CSPs explodes combinatorially**. 12,958^4 × 50M = 10^21 4-tuples = unstorable.

## What this means for E2

- **Exhaustive enumeration of overlapping local CSPs is not the path forward.** The space is too large at every level.
- **Sampling + downstream pipeline** is the only computationally feasible approach. N11 (sample 1000 5-cluster anchors, feed CSP-fill + ALNS) is the natural next step but was not run this session.
- **The 458 strict-canonical record** (from cross-domain methodology earlier in vol-122) remains the most significant outcome.

## State at close

- All N10b/N9 datasets deleted (freed ~3 GB).
- N1 dataset (12,958 corner clusters, 733 KB) kept.
- N-series binaries committed for future reuse.
- 41 GB free disk.

## Linked

- [[record-break-458-strict-canonical-2026-05-17]] (the day's actual win)
- [[k11-corpus-cross-validation]] (cross-domain methodology that worked)
- [[synthesis-457-equiv-459]] (cross-domain corrected synthesis)
