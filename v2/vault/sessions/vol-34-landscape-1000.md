# Vol-34 / Vol-35-prep — 1000-LO landscape probe at 6×6/5c

**Date**: 2026-05-14 (vol-34 close + vol-35 T1 pilot).
**Command**:
```
landscape_explorer --size 6 --colors 5 --puzzle-seed 1 \
    --n-restarts 1000 --alns-budget-ms 5000 --threads 8 \
    --out-dir output/vol-35/landscape_6x6_1000
```
**Cost**: ~10 min wall-clock on M1's 8 cores.

## Score distribution

Max edges at 6×6 = 60 internal. Score distribution across 1000 LOs:

| Score | Count | % |
|---:|---:|---:|
| 41 | 2 | 0.2 |
| 42 | 6 | 0.6 |
| 43 | 22 | 2.2 |
| 44 | 29 | 2.9 |
| 45 | 68 | 6.8 |
| 46 | 90 | 9.0 |
| 47 | 154 | 15.4 |
| 48 | 172 | 17.2 |
| 49 | 188 | 18.8 |
| 50 | 116 | 11.6 |
| 51 | 82 | 8.2 |
| 52 | 47 | 4.7 |
| 53 | 19 | 1.9 |
| 54 | 5 | 0.5 |

mean=48.2, max=54 (90% of optimum), min=41 (68%).

Bell-curve centered at 48-49 (peak ~18.8% of restarts). No score
reaches the optimum (60) — the landscape has many sub-optimal
attractors and ALNS-5s doesn't escape them.

## Hamming distribution

Pairwise Hamming on (piece_id, rotation) per position, 500-sample
(O(n²) memory budget):

| H range | Count of pairs |
|---:|---:|
| 25-29 | 5 |
| 30-34 | 14,616 |
| 35-39 | 110,129 |

mean H = 35.4 / 36. **Virtually every pair of LOs differs at 35 of
36 positions.** No pair is "close".

## Cluster count by Hamming threshold

| Threshold | Clusters |
|---:|---:|
| H ≤ 5 | 500 |
| H ≤ 10 | 500 |
| H ≤ 15 | 500 |
| H ≤ 20 | 500 |
| H ≤ 25 | 500 |

**No clustering at any reasonable threshold.** All 500 sample LOs
remain in their own cluster.

## Fitness-distance correlation

```
FDC Pearson r = -0.031
```

Essentially zero. The score of a LO has no relationship to its
Hamming distance from the best LO.

## Key finding

**6×6/5c has a rugged, random-looking fitness landscape under
ALNS-5s+polish.** There is NO big-valley structure: the best LO
(score=54) is not "surrounded" by other high-score LOs in
configuration space. Each LO sits in its own micro-basin of radius
~tiny.

This refutes the simple "map basins → understand structure" plan.
Two alternatives remain:

1. **Stronger super-basin discovery**: run ALNS with MUCH longer
   budgets (30s, 5min) and stronger destroy operators (k=15+,
   mega_mix). If super-basins emerge with more compute, the
   landscape IS structured — just at a coarser scale.

2. **Brute-force LO enumeration**: the user's original suggestion.
   At 6×6/5c, enumerate ALL boards with score ≥ 52 (only ~70
   configurations from this sample, but the brute-force set will
   be much larger). Check each for LO-ness exhaustively.

3. **Try a different puzzle size**: maybe 8×8 or 12×12 has more
   structure than 6×6. The Selby-Riordan generator's randomness
   may dominate small sizes.

## Vol-35 implications

The straightforward "ALNS-sample → cluster → predict" plan is
**REFUTED at 6×6/5c**. Vol-35 T1 needs to pivot to one of:
(a) super-basin discovery, (b) brute-force LO enumeration,
(c) larger puzzle size.

Alternative interpretation: maybe ALNS at 5s isn't a strong enough
attractor finder. With longer budgets the bell-curve might collapse
to a few discrete super-LOs. Worth testing.

## Update — 30s ALNS comparison

| Metric | 5s ALNS (n=1000) | 30s ALNS (n=100) |
|---|---:|---:|
| Mean | 48.2 | 48.0 |
| Max | 54 | 54 |
| Mean H | 35.4 | 35.4 |
| Clusters (H≤25) | 500/500 | 100/100 |
| FDC r | -0.031 | -0.049 |

**Longer ALNS does NOT reveal super-basin structure**. Statistics
are essentially identical across budgets. The landscape is genuinely
rugged at 6×6/5c, not just under-sampled with short ALNS.

This refutes vol-35 T1 alternative (a) "stronger super-basin discovery
via longer ALNS". Path forward: alternatives (b) brute-force LO
enumeration or (c) larger puzzle size.

## Update — 12×12/8c probe

100 restarts × 30s × 8 thread = ~7 min wall-clock at 12×12/8c.

| Metric | 6×6/5c | 12×12/8c |
|---|---:|---:|
| Max edges | 60 | 264 |
| Max LO score | 54 (90%) | 222 (84%) |
| Mean LO score | 48.2 | 207.1 |
| Mean Hamming | 35.4 / 36 (98%) | 143.6 / 144 (99.7%) |
| Clusters (H≤25) | 100/100 | 100/100 |
| FDC r | -0.031 | -0.104 |

**Bigger puzzle has slightly more FDC structure** (r=-0.104 vs -0.031).
Still small, but consistently signed and an order of magnitude
larger.

Hypothesis for canonical 16×16/22c: the FDC might be measurable
(r ~ -0.3 to -0.5). If so, vol-35 should run a 100-restart probe
at canonical size with ~5min ALNS budget. That'd be 100 × 5min / 8
= ~1 hr compute. Worth doing in vol-35.

If canonical FDC is meaningful (r << 0), then there IS a big-valley
structure at 16×16 — operators that navigate toward high-score LOs
SHOULD be effective. The vol-32 458 record is potentially the "tip"
of such a valley.

## Update — full scaling scan (4×4 / 6×6 / 12×12 / 16×16)

| Size | Max edges | Best LO | Mean | Best/Max | FDC | Notes |
|---|---:|---:|---:|---:|---:|---|
| 4×4/4c (100×10s) | 24 | **24 (optimum!)** | 18.6 | 100% | -0.052 | 2 of 100 reached optimum; some clustering at H≤10 (top cluster=6 boards) |
| 6×6/5c (1000×5s) | 60 | 54 | 48.2 | 90% | -0.031 | rugged, no clustering |
| 6×6/5c (100×30s) | 60 | 54 | 48.0 | 90% | -0.049 | same as 5s — longer ALNS doesn't help |
| 12×12/8c (100×30s) | 264 | 222 | 207.1 | 84% | **-0.104** | weakest FDC structure |
| 16×16/22c (50×3min) | 480 | 316 | 289.0 | 66% | -0.068 | severely under-budgeted ALNS |

**Key findings**:
1. **Best/Max ratio DECREASES with size**: 4×4 ALNS finds optimum;
   16×16 ALNS-from-random reaches only 66% (vs 95.4% from a depth-200
   CP partial → 458/480). The starting partial matters enormously.
2. **FDC is non-monotonic**: peaks at 12×12 (r=-0.104), drops at
   16×16 (r=-0.068). Possibly because 16×16 ALNS-from-random is too
   shallow (3min only reaches 66%, not near actual LOs).
3. **4×4 shows clustering at H≤10** (6-board cluster). The smallest
   scale has measurable basin structure that ALNS partially uncovers.

**Hypothesis for vol-35**: the FDC measurement at 16×16 is biased by
ALNS budget. At 5min-from-deep-CP-partial (vol-32/34 actual record-
chase setup), the LOs reached are MUCH better (457) and probably
more clustered. Vol-35 T1 should measure FDC on the vol-32/34
record-class LOs, not random-init LOs.

## Caveat — measurement bias

The ALNS-from-random LOs at 16×16 (mean 289, max 316) are NOT the
same population as the vol-32/34 ALNS-from-CP-partial LOs (mean ~450,
max 457). The 50-restart 16×16 probe measures the wrong population.

For the canonical FDC question, we'd want: 50 different vanilla_fast
partials → 50 different basin attractors after 5-min ALNS. That's
effectively what vol-34 T3 did with 14 partials × 4 seeds. Treating
those 56 boards as "LOs" gives a cleaner FDC measurement at the
relevant score range.
