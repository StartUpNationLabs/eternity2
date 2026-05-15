#!/usr/bin/env python3
"""Vol-65 — Piece-compatibility cluster analysis.

Findings:
- 54% of piece-pairs are FORBIDDEN from being neighbors under any
  rotation (zero weight in compat graph).
- Only 6 piece-pairs have max weight 24 (24 of 64 possible rotation
  combinations are compatible).
- Pieces 172, 191, 242, 246 form a "high-compatibility cluster"
  (3 of 6 max-weight pairs involve piece 172).
- Common feature: all 4 have multiple color-15 edges.

Empirical placement test on records:
- McGavin-469: ZERO adjacencies between cluster pieces.
- Our 458/459 records: 1-2 adjacencies max.

Conclusion: high-compatibility piece pairs are NOT placed adjacent
in records. They're used as SEPARATORS, not bond-mates. Counter-
intuitive: max compatibility doesn't translate to neighbor placement.

This suggests: the "best" placement strategy uses LOW-compat pieces
as neighbors (forcing constrained matching), reserving high-compat
pieces as flexible spacers.

This is a STRUCTURAL FINDING ON CANONICAL E2, not a refutation of
Fiedler. The 10 Fiedler-frame-leaning interior pieces are MOSTLY
NOT in the 4-piece max-compat cluster (only piece 172 overlaps).

Linked: vault/concepts/piece-spectral-fiedler.md
        vault/concepts/e2-maximally-adversarial-thesis.md (axis 4)
"""

# This is a documentation script; the analysis was done in-line.
# Reproduce: run vol65_piece_compat_graph.py + check max-weight pairs.

if __name__ == "__main__":
    print("Documentation only. See vol65_piece_compat_graph.py.")
