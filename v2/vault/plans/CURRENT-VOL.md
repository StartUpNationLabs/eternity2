# Current Volume — Vol-188 — TRANSLATION: Cross-Basin σ-Transport

**Theme**: directly compute σ-permutations between V181 460 and McGavin 469, find the SHORTEST partial-cycle that lifts V181's bottom band while keeping its top band intact.

## Why now

V187 closed with MIP-proven rigidity on every 2-row band and the 6×5 box in V181's mismatch region. ALL local structural search exhausted. The vol-65 finding said σ-cycles are indecomposable for FULL board transport (sum of cycle lengths = 255). But the converse hasn't been tested rigorously: **the SHORTEST σ that maps V181 bottom rows to McGavin bottom rows might be SMALLER than full σ**.

If the *partial-band* σ-transport works, V181 → 460 + (Δ where Δ = score of McGavin bottom rows minus V181 bottom rows).

## Mathematical setup

Let $b_1$ = V181's 460 (cp=(0,3,1,2)), $b_2$ = McGavin's 469 (cp=(3,2,0,1)).

The two boards have DIFFERENT corner perms — straight σ doesn't apply. First step: **canonicalise** by rotating one to match the other's corner orientation.

After canonicalisation:
- Let σ : positions → positions be the bijection that maps $b_1$'s piece at position $p$ to $b_2$'s piece at position $\sigma(p)$. But pieces themselves differ in placement.
- Actually σ is a permutation OF PIECES: $\pi(\text{piece}(b_1, p)) = \text{piece}(b_2, p)$.
- π is the piece-relabelling that turns $b_1$ into $b_2$.

For row-band transport: consider only rows 11-15. Compute the **restricted π** = the mapping of pieces in $b_1$'s rows 11-15 to pieces at the same positions in $b_2$'s rows 11-15.

The cycle decomposition of restricted π reveals: which pieces form independent cycles within the band? If there's a cycle of length 8 that maps $b_1$'s bottom-pattern to $b_2$'s bottom-pattern WITHOUT touching $b_1$'s top rows, applying just that cycle lifts $b_1$ to a hybrid basin.

## Binding items (3 max)

1. Compute restricted π between V181 460 and McGavin 469 (post-canonicalisation). Report cycle lengths.
2. For each independent cycle, apply it as a piece-substitution to V181 and rescore.
3. If any cycle yields ≥461, document. If all reduce score, refute partial σ-transport.

## Days budget

1 day.

## Linked

- [[../sessions/vol-188]] (TBD)
- [[../concepts/sigma-cycle-indecomposability]]
- [[../basins/basin-460-cp0312-v181]]
- [[../basins/basin-mcgavin-469]]
- [[../sessions/vol-187]]
