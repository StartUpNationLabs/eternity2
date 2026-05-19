# ALNS Scaling Curve (V131-T2, 2026-05-19)

**Status**: `built`
**Origin**: Vol-131 after pivot from McGavin obsession
**Files**:
- `scripts/v131_scaling_benchmark.py`
- `output/vol-131/scaling_bench_20260519T123004/`

## Setup

For each $(\text{size}, n_{\text{colors}})$ pair, generate 3 puzzles
(seeds 42, 1, 7) via `gen_small_csv` (Selby-Riordan-style edge-matched
instances guaranteed to admit a solution). Run `alns_e2 --seconds 60
--skip-warmup` on each. Record best matched-edges score and whether
100% solved.

## Results

| Size | n_colors | Target edges | Median best | % | n_solved/3 |
|------|----------|--------------|-------------|----|-------------|
| 6×6  | 4 | 60  | 60  | **100%** | **3** |
| 7×7  | 5 | 84  | 82  | 97.6% | 1 |
| 8×8  | 6 | 112 | 104 | 92.9% | 0 |
| 10×10 | 8 | 180 | 164 | 91.1% | 0 |
| 12×12 | 10 | 264 | 228 | 86.4% | 0 |
| 14×14 | 12 | 364 | 297 | 81.6% | 0 |

## Key findings

1. **Algorithmic wall starts at 7×7**: 2/3 instances unsolved in 60s.
2. **8×8 onward: 0% solve rate** at 60s budget. Score plateaus below 100%.
3. **Monotonic % decline** with size: 100 → 97.6 → 92.9 → 91.1 → 86.4 → 81.6%.

## Comparison to canonical 16×16

Canonical 16×16/22 at our standing record 461/480 = **96.04%**.

Strikingly, this is BETWEEN 7×7 (97.6% median) and 8×8 (92.9% median)
on this scaling curve. Three interpretations:

- **Canonical has lower constraint density** than what the curve
  predicts for its size. 22 colors on 256 pieces is sparser than
  12 colors on 196 pieces (14×14) — each piece-side has more
  candidates.
- **Selby-Riordan generator is special**: deliberately maximises
  diversity / avoids forced moves. Generated puzzles via our
  `gen_small_csv` may be MORE constrained than canonical.
- **The score % is misleading** — getting to 96% on canonical is
  much harder in absolute terms than 81% on 14×14.

## Implications

- We have a baseline for future operator comparisons. Any new
  operator can be benchmarked on the same suite.
- The 8×8 instances at <93% are a useful **research-grade testbed**:
  hard enough to be informative, fast enough to iterate on.
- Time-to-solve for 6×6 is ~30s (median of 3 solves in 60s budget).
  This is the regime where exact (CP/MIP) and meta-heuristic
  (ALNS) both work; below this they're trivial, above they fail.

## What's still open

- Run ALNS basic with MUCH LONGER budget (e.g. 30min) on the
  8×8 instances — do they solve eventually, or genuinely wall?
- Compare bf_bw DFS vs ALNS basic on the same suite — which scales
  better?
- Add FILAMENT-repair head-to-head against SA-repair on this suite.
- Re-run with different `n_colors`: hold size constant, vary colors
  to see constraint-density effect.

## Linked

- [[concepts/filament-lk-2d]] (would benefit from this baseline)
- [[concepts/palimpsest-historical-consensus]]
- [[sessions/vol-131]]
