# Session — vol-07

**Theme**: Structural characterization without score breakthrough. MaxSAT-locally-optimal 45-cell defect zone.
**Raw**: [[archive/raw/RESEARCH_NOTES_7|RESEARCH_NOTES_7.md]], [[archive/raw/NIGHT7_SUMMARY|NIGHT7_SUMMARY.md]]

## What was attempted

- 11 parallel analysis/exploration tracks.
- [[z22-vertex-charge]] fingerprint computation.
- Rediscovery of Selby-Riordan generator's rare-opposite rule.
- Verhaard 2×2 (corrected from 2×3) tilability metric — see [[reference-verhaard-actual-method]].
- Chessboard parity lower bound.
- Map-Elites quality-diversity infrastructure.
- Blank-interior PT (test if 454 basin is wide).

## What was measured / kept

- **45-cell defect zone of 454 board: MaxSAT-locally-optimal in 83s** (EvalMaxSAT minimal encoder). 26 mismatches confirmed optimum.
- **[[rare-color-rule|Selby-Riordan rare-opposite-edge rule]] discovered**: rare colors never adjacent within a piece. Novel to our team — not in 26-year community corpus.
- **[[z22-vertex-charge]] fingerprint**: 44-50 nonzero charges per plateau board, spatially localized in the same hotspot as universal-mismatch geometry.
- **454 is byte-identical PT-deterministic** across 4 seeds (vol-6 measurement extended).

## What was refuted

- **Selby-generator-bias**: MC-falsified at color-pair-surprise level. The generator is uniformly random except for the rare-opposite rule.
- **Chessboard parity** as lower bound: cross-class cancellation, zero net.
- **Reverse-Selby interior-first ordering**: CP exhausts on partial-match boards; this is an *optimization* technique, not a search technique.
- **Cross-border GA**: noise within families; between-basin crossover destroys structure.
- **Border-diversity surrogate** alone: caps at 449-450 on non-corpus borders even with 20× compute.
- **Houdayer-PT within corpus**: zero improving swaps; replicas too similar.
- **Blank-interior PT** test (438/480): the 454 basin is narrow, not wide.

## Concepts touched

- [[inner-k-optimality]] (extended to 45-cell zone)
- [[rare-color-rule]] (opposite-edge rule discovered)
- [[z22-vertex-charge]] (introduced)
- [[verhaard-set-sa]] (corrected per `reference_verhaard_actual_method`)
- [[selby-riordan-generator]] (characterized)

## Open at close

- Community-export mining (delivered vol-8).
- Constructive solution-compatible border enumeration (open).

## Linked memory

- `reference_verhaard_actual_method`
- `project_e2_rare_opposite_rule`
- `project_e2_rare_color_geography`
