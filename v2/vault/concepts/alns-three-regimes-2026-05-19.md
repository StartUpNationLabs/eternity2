# ALNS 3-Regime Characterization (V133, 2026-05-19)

**Status**: `built`
**Origin**: Vol-133 saturation test (refutes the +80 rule from V132)
**Files**:
- `scripts/v133_density_saturation.py`
- `scripts/v133_reparse.py`
- `output/vol-133/reparse.json`

## Summary

V132 found ALNS extracts ~80 percentage points above the random-
placement baseline across all measured puzzles. V133 tested this at
extreme densities and discovered THREE regimes:

| Regime | $p_{\text{match}}$ | ALNS % | gap |
|--------|--------------------|--------|-----|
| **HIGH density** | $\ge 0.20$ | 100% (capped) | +72 to +78 (compressed) |
| **MEDIUM density** | 0.13 – 0.20 | 96 – 100% | **+80 to +82** ⭐ |
| **LOW density** | $\le 0.06$ | 68 – 78% | **+65 to +72** (sub-linear) |

The +80 law from V132 holds ONLY in the medium-density regime.

## Data

Median per config (3 seeds each, 60s ALNS basic):

| Config | size×size/c | $p_{\text{match}}$ | random% | ALNS% | gap |
|--------|--------|-----|------|------|------|
| high_4×4_c2 | 4×4/2  | 0.283 | 28.3% | 100%  | +71.7 |
| high_5×5_c3 | 5×5/3  | 0.222 | 22.2% | 100%  | +77.8 |
| high_6×6_c3 | 6×6/3  | 0.238 | 23.8% | 100%  | +76.2 |
| med_8×8_c4  | 8×8/4  | 0.197 | 19.7% | 100%  | +80.3 |
| med_10×10_c5 | 10×10/5 | 0.164 | 16.4% | 97.2% | +80.4 |
| med_12×12_c6 | 12×12/6 | 0.141 | 14.1% | 96.2% | +82.2 |
| low_8×8_c16 | 8×8/16  | 0.052 | 5.2%  | 77.7% | +72.5 |
| low_10×10_c20 | 10×10/20 | 0.045 | 4.5% | 73.9% | +69.5 |
| low_12×12_c24 | 12×12/24 | 0.037 | 3.7% | 68.2% | +64.5 |

## Where does canonical 16×16/22 sit?

V132 measured canonical: $p_{\text{match}} = 0.042$, ALNS 96.0%, gap
+91.8.

That's $p_{\text{match}}$ in the LOW regime (≤ 0.06) — but the gap
(+91.8) is FAR higher than the low-regime suite (+64 to +72).
**Canonical is an anomaly relative to the V133 model.**

Possible explanations:
1. **Canonical has structure** (Selby-Riordan generator) that
   makes ALNS effective beyond what raw density predicts.
2. **The 5 canonical hints** anchor solutions.
3. **Long ALNS work history**: canonical has been studied for years;
   our 461 record is the cumulative output of many algorithms, not
   one 60s ALNS run.

## What's still open

- Test the LOW-density regime with longer budgets (30 min instead of
  60s) to see if ALNS converges to the +80 line.
- Test MEDIUM-density at sizes 16×16 (with proportional colors,
  e.g. 16×16/c8) to see if the +80 holds at canonical-scale.
- Predict canonical's reachable upper bound from the 3-regime model.

## Linked

- [[constraint-density-vs-alns-gap]] (V132 — sets up the question)
- [[scaling-curve-2026-05-19]] (V131 — first scaling data)
- [[plans/MONTH_AHEAD_2026-05-19]]
