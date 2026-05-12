#!/usr/bin/env python3
"""H2 color-parity lower bound on minimum mismatches (NEGATIVE result).

Quasicrystal-agent (vol-7) proposed: count per-color c-edges on
chessboard-white vs chessboard-black cells; the difference forces
unmatched edges.

Implementation: for each interior color c, compute T_c = c-edges on
all 256 pieces. Then T_c must split between white cells and black
cells (128 each). Since pieces have class constraints (4 corners,
56 edges, 196 interior, with white/black quota each), we compute
min imbalance via subset-sum DP on each class.

Result: when imbalances in different classes can have OPPOSITE
signs (= |W-B| in one class compensates by placing the other
class with opposite sign), the per-color minimum total imbalance
is 0 for EVERY color. The "loose" lower bound of 4 unmatched edges
disappears under proper cross-class accounting.

VERDICT: H2 simple chessboard parity gives NO lower bound on E2's
mismatches. Negative result.
"""
