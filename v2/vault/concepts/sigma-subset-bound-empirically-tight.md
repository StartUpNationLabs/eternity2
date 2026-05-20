---
name: sigma-subset-bound-empirically-tight
description: "Vol-119 T3 — DIRECT empirical measurement of Δ(S) for the thinnest σ-subsets in our basin corpus confirms the vol-118 MATH_NOTES theorem (Δ(S) ≈ -B(S)·p) is tight with p ≈ 1.0. Even at ratio B/|S| as low as 0.67 (k=45 on the largest cross-cluster cycle), Δ(S) = -30 (= -B), no lift possible."
metadata:
  type: project
status: built
---

# σ-subset bound empirically tight (vol-119 T3)

## Question

Vol-118 MATH_NOTES_2026-05-16_SIGMA_SUBSET_THEOREM left open: are
there σ-cycle pairs where one cycle is nearly contiguous (low B/|S|
ratio)? If yes, the σ-subset attack might reactivate.

## Method

1. Built `scripts/vol119_sigma_thin_pair_search.py`: for all pairs in
   basin corpus, decompose σ, find MIN B(S)/|S| via exhaustive (N≤18)
   or greedy local-opt search.
2. Built `scripts/vol119_sigma_subset_apply_measure.py`: for the
   winning pair-cycles, DIRECTLY apply σ_S (replace board_A's pieces
   in subset S with board_B's pieces at same positions) and measure
   actual score delta.

## Findings

**Min ratio found**: B(S)/|S| = 0.67 at k=45 on the largest σ-cycle
(N=190) between bseed6_score459 (cluster A) and RECORD_TIE_459_p06
(cluster B). Earlier coarser search reported 0.356 — refined exhaustive
gives 0.67 across cleaner subset enumeration.

**Direct Δ(S) measurement**: on this exact thinnest subset:
- B(S) = 30 → Δ predicted = -30 (theorem with p=1)
- Δ measured = -30  ✓ exact match

Across all (k, subset) tuples measured (200+ trials on 5 σ-cycles):
- Δ(S) ≤ 0 in all cases.
- Maximum Δ = -3 (at k=1, B=4) — boundary loss dominates singleton.
- Δ matches -B(S) within ±2 for k ≤ 50.
- p (boundary-realization rate) empirically = 0.92 - 1.00.

## Conclusion

**σ-subset attack on the 459-level set is bounded by Δ ≤ -B(S) with
p ≈ 1.0 even at the thinnest empirical subsets.** No subset has been
found with Δ > 0.

The vol-118 theorem is **empirically tight** across a wider range than
the original 3-row spot check.

## Implication

The "σ-thin cycle" pathway to break 459 is **closed**. To break 459
from current corpus via permutation-style attacks would need:
- A subset where boundary edges ALIGN by chance (vol-118 noted: this
  doesn't happen in our cycles).
- A FUNDAMENTALLY new basin pair where some cycle has B/|S| ≪ 0.5
  (none found in current corpus; pending corpus enlargement in T1).

## Pending

T1 sweep (in progress) will enlarge the basin corpus from 7 to ~20-30
basins. If a new basin pair has a structurally thinner cycle, the
question re-opens. If not, σ-subset attack stays closed across the
larger corpus too.

## Linked

- [[MATH_NOTES_2026-05-16_SIGMA_SUBSET_THEOREM]]
- [[basin-mix-mip-refuted]]
- [[vol-119]]
