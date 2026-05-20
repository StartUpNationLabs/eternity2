---
name: spectral-border-signature
description: Naming: SPECTRA — Latin \"image\", as in spectrum.
status: partial
metadata:
  type: concept
---
# Spectral Border Signature (V173 SPECTRA)

Status: `partial` (signature measured 2026-05-20; predictive use unbuilt)
Origin: vol-173 (planned)
Files: `scripts/v173_spectral_signature/probe.py`.
Naming: **SPECTRA** — Latin "image", as in spectrum.

## Idea

The 60 perimeter cells of an E2 board carry 60 interior-facing edge colors. Walk the ring clockwise: $c_0, c_1, \ldots, c_{59}$. Apply the DFT:

$$
\hat c(k) = \frac{1}{60} \sum_{t=0}^{59} c_t \cdot e^{-2\pi i k t / 60}, \quad k = 0, \ldots, 30.
$$

The amplitude spectrum $|\hat c(k)|$ characterizes the **rotational structure** of the border. Boards in different basins have different spectra.

## What was measured

Over 938 corpus boards (database-400-480/, score 400-480):

| Score bin | n | Top 5 freqs (median amplitude) |
|---|---|---|
| ≥440 | many | k=11, 13, 20, 7, 15 (medians 0.6-0.7) |
| ≥458 | 58 | k=8, 26, 10, 11, 5 (medians 0.8-1.0) |
| ≥460 | 19 | k=7, 14, 22, 1, 2 (medians 0.7-0.9) |
| ≥469 | 3 | k=**15**, 5, 16, 20, 29 (medians 0.99-1.53) |

The 469-tier signature shows much higher amplitude across the board (peak 1.5+, vs 0.7 in 460-tier). This may reflect that the 469 cluster has only 3 σ-related boards in DB, so the "median" is over essentially identical boards.

### Discriminating frequencies (≥460 vs <460)

**Original 2026-05-20 probe with WRONG `BORDER='0000000000000000'`** had incorrect ring extraction (interior matches were not filtered). Recomputed 2026-05-20 with corrected `BORDER='1111111111111111'`:

n=23 high vs n=1255 low:

| k | Δmedian | high med | low med |
|---|---|---|---|
| **12** | **+0.321** | 0.766 | 0.446 |
| 7 | +0.283 | 0.765 | 0.482 |
| 13 | +0.202 | 0.756 | 0.555 |
| 16 | −0.151 | 0.420 | 0.571 |
| 26 | −0.134 | 0.441 | 0.575 |
| 29 | −0.029 | 0.494 | 0.523 |
| 5 | −0.021 | 0.511 | 0.531 |
| 19 | +0.010 | 0.606 | 0.596 |

Key signal: **k=12 and k=7 amplitudes are HIGHER in ≥460 boards**. k=12 corresponds to a period-5 oscillation around the 60-cell border ring (60/12 = 5). k=7 ≈ period-8.6.

High-score boards over-express short-period structure (k=29 ≈ alternating period-2 pattern around the border) and under-express k=19 / k=13.

**Interpretation**: a specific alternating color pattern around the border ring is associated with high-score basins. This is consistent with the [[rare-color-geography]] finding (vol-13: all 120 rare-color slots are on the border ring's interior matchings) — rare colors create constraints that ripple through specific frequencies.

## Application — predictive use

### 1. Beam pruning

During V155 build, after placing all 60 border pieces (depths 0..59 in border-first scan), compute the partial border spectrum. Reject children whose discriminating frequencies (k=29, k=16, k=12, k=5, k=7) are below the ≥460 25th-percentile threshold. This is a *post-border-pre-interior* pruning step — cheap.

### 2. Constructive constraint

Add a per-edge bias during V155 border placement: prefer placements that increase $|\hat c(29)| + |\hat c(16)| + \ldots$ — a sum of target frequency amplitudes. Implementation: a $O(1)$ update per placement using running DFT coefficients.

### 3. Basin similarity metric

Two boards are spectrally close if their border spectra are L2-close. Use as a basin-cluster signature, complementing corner-perm + Hamming.

## What's still open

- Is the k=29 signal causal (constraint on solutions) or correlational (artifact of 3 σ-related 469 boards)? Probe by testing the discrimination on 458 vs 460 (smaller gap, n still small for 460+).
- Per-side (north / east / south / west) spectra separately. Asymmetric basins might have asymmetric per-side spectra.
- Phase information ($\arg \hat c(k)$), not just amplitude.
- Reverse: synthesize a target spectrum and reconstruct candidate border placements.

## Linked

- [[vol-173]]
- [[rare-color-geography]] (vol-13)
