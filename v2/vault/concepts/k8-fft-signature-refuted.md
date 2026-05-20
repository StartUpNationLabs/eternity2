---
name: k8-fft-signature-refuted
description: "K8 = FFT signature: treat board as 16×16×4 image, compute 2D FFT. Hypothesis: high-score boards have characteristic low-frequency dominance. REFUTED — all complete boards (444-459) have identical low_frac ≈ 0.903."
metadata:
  type: project
status: refuted
---

# K8 — FFT signature analysis (refuted)

## Refutation

- **Refuted**: vol-122 K8.
- **Evidence**: all complete boards (score 444-459) have identical low-frequency fraction ≈ 0.903. The 2D FFT signature carries **zero discriminative information** for score on canonical 16×16 E2.
- **What's refuted**: image-processing lens for board scoring — the hypothesis that high-score boards have a distinguishable smooth-color-transition signature.
- **What's NOT refuted**: other cross-domain lenses (signal processing, group theory, etc.) — FFT specifically is null; this doesn't generalize.

## Origin

Per user directive 2026-05-17 evening "innovate cross-domain (waves,
lights, images, etc.)", tried image-processing lens: treat the 16×16
board as a 4-channel image (per-cell TRBL edge colors), compute 2D FFT.

## Hypothesis

High-score boards (459 record) should have distinct frequency signatures
from medium-score boards (444 J1) and random boards. Specifically:
- High-score → smooth color transitions → low-frequency dominance.
- Random → flat spectrum.

## Measurement

`scripts/vol122_fft_signature.py`. For each board, computed per-channel
2D FFT, then `total_low_frac` = mean over channels of the fraction of
power in the 9 lowest non-DC frequencies + DC.

## Results

| Board | matched | low_frac |
|---|---:|---:|
| Standing 459 (vol-60) | 459 | 0.9043 |
| Vol-32 RECORD 458 | 458 | 0.9033 |
| Vol-35 RECORD TIE 458 | 458 | 0.9033 |
| Vol-35 RECORD TIE 457 | 457 | 0.9038 |
| J1-hinted-v2 ALNS s7 | 445 | 0.9037 |
| J1-hinted-v2 ALNS s42 | 444 | 0.9040 |
| J1-FLH 447 raw | 447 | 0.9035 |
| J1-FLH 444 raw | 444 | 0.9033 |
| Random shuffle | n/a | 0.7425 |

## Conclusion

All complete boards (256 cells, scores 444-459) have low_frac in
[0.9033, 0.9043] — a difference of 0.001, well within numerical noise.
FFT signature does NOT discriminate high-score vs medium-score complete
boards.

**Why**: Selby-Riordan E2 has 22 interior colors distributed across
pieces such that ANY complete board (regardless of match quality) has
similar global color distribution. The matched-edges metric depends on
LOCAL adjacency, not GLOBAL frequency content.

Random shuffle gets 0.74 because it has true uniform distribution
across cells. Real boards have piece-uniqueness constraints that force
a specific color distribution → ~0.90 low_frac regardless of how
"matched" the board is.

## Implication for image-processing lens

The standard 2D FFT operates on cell COLORS, not on the matched/mismatch
adjacency structure. To detect matching quality with image-processing
tools, we'd need to work on the EDGE-MISMATCH map (a 15×16 + 16×15
binary image of mismatched horizontals + verticals). That's a different
analysis — feasible but not yet tried.

## Status

`built-tested-refuted`. The naive FFT-on-colors approach doesn't work.
A refined version on the EDGE-MISMATCH GRAPH might be informative —
left for future cross-domain exploration.

## Linked

- [[vol-122]] (today)
- [[feedback-invent-cross-domain]] (the directive that motivated this)
