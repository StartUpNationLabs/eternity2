"""LATTICE — unconditional forced adjacencies for any 480 solution.

Edge model: an interior edge joins two pieces. Consider a HORIZONTAL edge:
left piece shows color c on its E side, right piece shows c on its W side.
For a 480 board, EVERY interior edge matches. So every (piece, side) that ends
up on an interior edge is paired with another (piece, side') of the SAME color
on the opposite side.

A piece-orientation-side that presents color c: how many DISTINCT OTHER PIECES
can present c on the geometrically-opposite side (E<->W, N<->S)? If exactly 1,
that piece-side has a FORCED partner (whenever it lies on an interior edge of
that orientation). We count distinct pieces (not orientations) since a piece is
used once.

We compute, per ORDERED adjacency type (horizontal: left.E=right.W ; vertical:
top.S=bottom.N), the bipartite compat and find forced (degree-1) sides.
This is the first deduction layer; closure/propagation comes after.
"""
import sys
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from collections import defaultdict

size,pieces,hints=load_puzzle()
NP=len(pieces)

# Enumerate piece orientations: (pid, rot, edges)
orient=[]
for p,base in enumerate(pieces):
    seen=set()
    for r in range(4):
        ed=rot_edges(base,r)
        orient.append((p,r,ed))

# For HORIZONTAL adjacency: a left-cell shows E=c, right-cell shows W=c.
# Build: for color c, set of pieces that can show c on E (in some rotation,
# with the OTHER border sides valid for an interior cell -> no BORDER on the
# matched side; we allow interior placement so the E side is c (not border)).
# We track distinct PIECES.
showE=defaultdict(set); showW=defaultdict(set)
showN=defaultdict(set); showS=defaultdict(set)
for (p,r,ed) in orient:
    if ed[E]!=BORDER: showE[ed[E]].add(p)
    if ed[W]!=BORDER: showW[ed[W]].add(p)
    if ed[N]!=BORDER: showN[ed[N]].add(p)
    if ed[S]!=BORDER: showS[ed[S]].add(p)

# For a given piece p showing color c on its E side, its right-neighbor must be a
# piece (!=p) in showW[c]. Forced if |showW[c] \ {p}| == 1.
def forced_partners(p, c, partner_set):
    cand = partner_set[c] - {p}
    return cand

# Count forced horizontal-right adjacencies
forced_h=0; forced_v=0; total_sides=0
forced_pairs=set()
for (p,r,ed) in orient:
    if ed[E]!=BORDER:
        total_sides+=1
        cand=showW[ed[E]]-{p}
        if len(cand)==1:
            forced_h+=1
            q=next(iter(cand)); forced_pairs.add(('H',p,q))
    if ed[S]!=BORDER:
        cand=showN[ed[S]]-{p}
        if len(cand)==1:
            forced_v+=1
            q=next(iter(cand)); forced_pairs.add(('V',p,q))

# Distinct forced piece-pairs (unordered within direction)
print(f"orientations: {len(orient)}")
print(f"colors on E side: {len(showE)}; supply sizes (distinct pieces per color):")
for c in sorted(showW):
    print(f"  color {c:2d}: showW={len(showW[c])} pieces, showE={len(showE[c])}, showN={len(showN[c])}, showS={len(showS[c])}")
print(f"\nForced horizontal partner instances (degree-1): {forced_h}")
print(f"Forced vertical partner instances (degree-1): {forced_v}")
print(f"Distinct forced directional pairs: {len(forced_pairs)}")
