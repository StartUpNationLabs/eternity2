---
name: k12-completely-different-models
description: "K12 brainstorm — model E2 as something fundamentally non-combinatorial: hydrodynamics/fluids, electrical circuits, DNA sequence, music chord progression, foam topology, etc. Picked foam topology for first PoC (connects to K9/K11 findings)."
metadata:
  type: project
status: built
---

# K12 — Completely Different Models of E2

User directive 2026-05-17 ~16:06 CEST: "Let's model the puzzle as
something completely different please".

## Candidates

### M1. Hydrodynamics / fluid flow
- Pieces = fluid cells; colors = fluid types.
- Matched edges = no interface; mismatched = surface tension.
- Minimize total tension via capillary dynamics.
- **2D foam topology**: matched clusters = bubbles. Plateau's law: 3-way junctions at 120°.

### M2. Electrical circuit
- Pieces = resistors with 4 terminals; colors = resistance values.
- Matched edges = wire connections.
- Total impedance = "matchability" metric.
- Kirchhoff's laws give global constraints.

### M3. DNA / sequence alignment
- Each piece's 4 colors = a 4-base codon.
- Matching = Watson-Crick base-pairing.
- Smith-Waterman alignment on row/column sequences.
- (Note: this might collapse to J1 column-DP.)

### M4. Crystallographic packing
- Pieces = molecules with 4 binding sites.
- Colors = binding affinities.
- Minimum-energy packing via lattice gas / Ising-type models.

### M5. Cellular automaton (CA) evolution
- 2D CA where each cell evolves based on 4 neighbors' colors.
- Rule: "rotate or swap if at least 2 of 4 edges mismatched".
- (Note: this collapses to ALNS-like behavior.)

### M6. Music chord progression
- Pieces = chords; colors = notes.
- Matched edges = consonant chord transitions.
- Voice-leading rules might give new neighborhood structure.

### M7. Recommender systems / matrix factorization
- 256×256 piece-compatibility matrix M.
- SVD: M = U Σ V^T.
- Latent factors reveal piece "preferences".
- (Note: this is what vol-122 J3 did; partial overlap.)

### M8. Knot / braid theory
- Piece-side permutations encode permutation group elements.
- Board = a braid; identify boards with TRIVIAL braid invariant.

### M9. Protein folding
- Pieces = amino acids; colors = hydrophobicity classes.
- Board = folded configuration.
- Minimize folding energy via HP-model.

### M10. Stock market / time series
- Each row/column = a time series of "prices" (colors).
- Matched = stable; mismatched = price jump.
- ARIMA model on row sequences.

### M11. Chemistry / molecular bonds
- Pieces = atoms; colors = bond types.
- Match = valid covalent bond.
- Synthesis pathway analogy.

### M12. Linguistics / parsing
- Piece edges = production rules.
- Board = a parse tree.
- Find boards that satisfy grammar.

## Pick: M1 foam topology

Strongest connection to existing findings:
- K9 (mismatch topology) and K11.4 (mismatch-zlib) both measure
  mismatch-region shape.
- Foam-physics adds the ANGLE structure at junctions (Plateau's
  120° rule).
- The 458 → 459 transition (2 big clusters → 4 small) is a
  BUBBLE-MERGER/SPLIT — a well-studied foam process.

## First PoC

For each candidate board:
1. Compute the matched/mismatched graph cells.
2. Identify junction points (vertices where 3+ regions meet).
3. Measure angles at each junction.
4. Compare to Plateau's law predictions.

If the records satisfy Plateau-like statistics, we have a NEW
geometric signature.

## Why might M1 work?

Foam physics tells us that in EQUILIBRIUM:
- Bubble area distribution follows a power law.
- Junction angles converge to 120° (3-way) or 109.5° (4-way).
- Smaller bubbles eventually merge into larger via Ostwald ripening.

If E2's high-score boards have foam-like equilibrium, then a board's
DISTANCE TO EQUILIBRIUM (= violation of Plateau statistics) might be
a basin signature.

## Status

`design-complete`. Implementation next.

## Linked

- [[k9-mismatch-topology-finding]]
- [[k11-4-mismatch-zlib-signature]]
- [[k11-cross-domain-brainstorm]]
- [[feedback-invent-cross-domain]]
