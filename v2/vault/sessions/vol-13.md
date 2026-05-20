# Session — vol-13

**Theme**: Boundary-MPS tensor-network contraction. Rare-color geography. 10¹⁰¹ overcounting.
**Raw**: [[archive/raw/RESEARCH_NOTES_13|RESEARCH_NOTES_13.md]]

## What was attempted

- Liang 2025-style boundary-MPS contraction (`χ ∈ {1,4,8,16,32,64}`).
- Partition-function log Z computation.
- Per-row piece multiplicity audit.
- Self-consistent MPS supply tracking (unimplemented).
- Rare-color spatial distribution survey.

## What was measured / kept

- **[[boundary-mps]] χ-sweep**: log Z monotone 213.69 → 216.72 nats. **χ=1 already paramagnetic**; higher χ doesn't sharpen.
- **Z* ≈ 7×10⁹³ boundary-consistent colorings** vs true E2 ~10⁻⁸ expected solutions.
- **10¹⁰¹ overcounting gap**: local matching admits 10¹⁰¹× more colorings than respect piece-uniqueness. **Global piece-uniqueness is the binding rigidity, not local matching.**
- **[[rare-color-rule]] geography (vol-13 sharpening)**: all 120 rare-color edges live on the 60-piece border ring's internal matchings. 196 interior pieces have **0** rare edges. 56 edge pieces have 2 rare E/W each.
- Interior tile tensor: 784 nonzeros / 279,841 entries (0.28% dense, all distinct signatures). Per-leg marginal entropy 4.087 bits.

## What was refuted

- **MPS sharpening from row-multiplicity tracking**: χ=4 → χ=16 already paramagnetic.
- **Local method sufficiency**: 10¹⁰¹ gap proves global piece-uniqueness binding. **All BP/SP/MPS variants bounded by this.**
- **Stripe-extension propagator utility**: interior pieces have 0 rare edges, so logically vacuous on canonical E2.

## Concepts touched

- [[boundary-mps]] (introduced + refuted)
- [[rare-color-rule]] (border-ring exclusivity established)
- [[selby-riordan-generator]] (the design choice that makes rare colors border-only)

## Implication

**Stop trying message-passing / tensor-contraction methods.** They quantify the same gap (10¹⁰¹) and cannot close it. Per [[dead-ends]] in [[survey-propagation]] notes.

## Linked memory

- `project_e2_mps_relaxation_null`
- `project_e2_rare_color_geography`
