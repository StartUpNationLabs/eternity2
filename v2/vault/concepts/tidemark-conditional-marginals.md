---
name: tidemark-conditional-marginals
description: "TIDEMARK (vol-210) — conditional placement marginals of the free tail GIVEN a committed perfect-prefix board, via the χ-truncated boundary MPS with pins. Tests whether conditioning on a good 60-80% board sharpens the hard tail (exploitable for tail-resolution) or stays flat (rigorous negative). KEY: the perfect-matching contractor requires a PERFECTLY-matched prefix (McGavin's 11-mismatch prefix gives Z=0 past row 1); condition on constructor-style perfect partials."
status: refuted-as-tool
metadata:
  type: concept
---

# TIDEMARK — conditional marginals for tail-resolution (vol-210)

**Origin**: vol-210 (2026-06-10), the next step after vol-209 ISENTROPE proved the
interior is UNCONDITIONALLY grammar-uniform (95.5%). User-chosen ("not dumb brute
force; conditional-marginal is the next step").
**Files**: `crates/peps/src/bin/isentrope_marginals.rs` (`--pin-board --pin-rows
--pin-shuffle`), `crates/peps/src/mps_proper.rs::cell_marginals` (validated).

## The question
vol-209: unconditional interior marginals ~uniform (no local signal). But the MPS
contractor takes PINS → CONDITIONAL marginals of the free cells given a partial board
come for free. Does conditioning on a committed good prefix make the remaining hard
tail near-forced (sharp conditional marginals → exploitable for "smart" tail
resolution) or does it stay flat (the tail is information-theoretically undetermined
until ~complete → the area-law is irreducible even with global conditioning)?

## ★ Methodological KEY (found vol-210)
The contractor counts **PERFECT colorings** (all internal edges matched). So a pinned
prefix must be **perfectly matched internally**. McGavin 469 has **11 mismatches**, so
pinning ≥2 of its rows forces a mismatched seam → **Z=0** (no perfect completion).
- Pin McGavin top-1 row: works (Z>0). Top-2: Z=0 (its row-1/row-2 seam has a mismatch).
- → TIDEMARK must condition on **constructor-style PERFECT partials** (a board whose
  top-K rows are 0-mismatch). `KEYSTONE_456_cp2310_novel.json` has 0 mismatches in its
  top 10 rows — a valid perfect prefix. This is actually the RIGHT setup: it models a
  constructor that builds perfectly until the tail, asking "given my perfect prefix,
  what does the global grammar say about the tail?"
- (A soft/Boltzmann μ≠0 variant could condition on imperfect boards by penalizing
  mismatches instead of forbidding — open extension.)

## ★★ CORRECTED VERDICT (vol-210) — the apparent sharpening is a χ-TRUNCATION ARTIFACT
Initial χ=6 runs showed free-tail interior n_eff collapsing 749→19 at K=8 (a "40×
sharpening"). **This is NOT REAL — it is a low-χ MPS truncation artifact.** A
χ-convergence check at FIXED pin-rows=8 (`KEYSTONE_456` prefix):

| χ | free-interior n_eff |
|--:|--:|
| 2 | 1.94 |
| 4 | 2.43 |
| 6 | 19.1 |
| 8 | **242.8** |

n_eff is **monotonically increasing with χ and NOT converged** at χ=8 (already back up
to ~243, approaching the unconditional ~749). Low χ severely distorts the CONDITIONAL
marginal: pinning a prefix creates long-range entanglement the truncated MPS can't
represent, so it drops small-weight branches and *artificially concentrates* the
distribution. **The conditional tail is far flatter than the low-χ result suggested —
likely nearly as flat as unconditional.** The "K=6→64, K=8→19" curve was the artifact
sharpening with the *same* (too-small) χ at every K.

**Why this matters / lesson (anti-pattern caught):** UNCONDITIONAL entropy (vol-209)
converged fine at χ=16-32 (validated vs brute on 4×4/6×6) because it's low-entanglement.
CONDITIONAL contractions need χ ≫ what's tractable at K=23 — so the conditional MPS
marginal is **not reliably computable for E2** at usable χ, and any sharpening read off
low χ is untrustworthy. (Almost reported "40× conditioning sharpening" before the
χ-check — exactly anti-pattern #10/#4: believe a number only after convergence/variance.)

**Net:** conditional marginals do NOT give a trustworthy tail-resolution signal at
computable χ for E2. The unconditional finding stands (interior grammar-uniform); the
conditional refinement is **inconclusive-bordering-negative** — consistent with the
area-law (the tail stays high-entropy under the grammar until almost-complete).

### (superseded) raw χ=6 curve — kept for the record, NOT a valid result
pin K=2→567, K=4→396, K=6→64, K=8→19, K=10→0(Z=0). All at χ=6 = under-converged.

## Control — feasibility check (χ-INDEPENDENT, still valid)
`--pin-shuffle` (same pieces, permuted positions) → **Z=0** (no perfect completion).
This is a *feasibility* statement (χ-independent): a spatially-scrambled-but-same-pool
prefix has no perfect tiling, while the real prefix does. Valid finding — but it only
says the real prefix is *feasible*, NOT that its conditional marginal is *sharp* (that
claim was the truncation artifact above).

## Predictive lift — measured at χ=8 (under-converged → unreliable)
At χ=8, the conditional top-1 matched the 456 board's actual tail piece 12/128=9.4%
(vs ~0.5% random). BUT χ=8 is under-converged (n_eff still climbing), so this "19×
lift" is not trustworthy — at higher χ the marginal flattens and the lift would shrink.
Recorded but NOT a reliable result.

## Implication — TIDEMARK constructor NOT pursued (the signal isn't real at computable χ)
The intended lever (build perfect prefix → conditional marginals resolve the tail) is
**undercut by the χ-truncation finding**: at the χ reachable for E2 (K=23), the
conditional marginal is not converged and the apparent sharpening is artifact. So a
marginal-guided tail constructor would be steering by noise. Binding item 2 (the
constructor) is therefore **wont-do** on this basis — pursuing it would be building on
an unvalidated signal (the exact anti-pattern). The honest conclusion: conditional
marginals via χ-truncated MPS are **not a usable tool for E2's tail** (conditional
entanglement too high for tractable χ); the tail stays high-entropy under the grammar,
consistent with the area-law being irreducible. A higher-χ or exact contractor (or a
fundamentally less-entangled conditional encoding) would be needed to revisit.

## Linked
- [[isentrope-entropy-growth]] — unconditional uniform interior (the contrast)
- [[lattice-forced-chains]] — unconditional no-forced-placements (conditional may differ)
- [[mcgavin-n-row-scaling]] — vol-68: top-14 pin forces 469 under ALNS (conditioning
  DOES sharpen on the right full prefix; TIDEMARK measures the marginal-entropy curve)
- [[watershed-frontier-flow]] — piece-theft (the tail starvation conditioning might pre-empt)
- [[MATH_NOTES_2026-06-10_isentrope_entropy_theorem]] — the area-law TIDEMARK tests
