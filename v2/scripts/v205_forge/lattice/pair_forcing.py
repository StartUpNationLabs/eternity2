"""Pair-level unconditional forcing check + AC-3-from-hints fixpoint.
1) Does any INTERIOR piece have so-rare colors it can sit in few cells?
   (count, per interior piece, # of interior cells where SOME rotation could
    match ALL determined neighbors — but with empty board, all interior cells
    are symmetric, so instead measure: # of (N,W,S,E) all-interior color combos
    the piece can satisfy = its 'placement flexibility').
2) Domain-1 cells after propagating hints to AC-3 fixpoint (approx via repeated
   single-edge filtering)."""
import sys
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from collections import defaultdict
size,pieces,hints=load_puzzle()
ncell=size*size;NP=len(pieces)
# classify pieces
def cls(base):
    nb=sum(1 for c in base if c==BORDER)
    return nb  # 2=corner,1=edge,0=interior
corner=[p for p in range(NP) if cls(pieces[p])==2]
edge=[p for p in range(NP) if cls(pieces[p])==1]
interior=[p for p in range(NP) if cls(pieces[p])==0]
print(f"corners={len(corner)} edges={len(edge)} interior={len(interior)}")
# flexibility: for each interior piece, # of distinct (N,E,S,W) interior 4-color
# combos it can present across rotations (max 4). All have >=1. This bounds how
# 'pinnable' it is. Min flexibility pieces are most constrained.
flex=[]
for p in interior:
    combos=set()
    for r in range(4):
        ed=rot_edges(pieces[p],r)
        combos.add(ed)
    flex.append((len(combos),p))
flex.sort()
from collections import Counter
fc=Counter(f for f,_ in flex)
print("interior piece rotation-distinctness (orbit size) histogram:", dict(fc))
# The real unconditional question: is there an interior cell-context with a
# UNIQUE piece? On empty board no. So unconditional pin count = 0 (beyond
# corners-to-corners as a CLASS, not specific cell).
# Corner SPECIFICITY: can we pin WHICH corner each corner-piece goes to?
# Each corner piece has 2 border sides; the corner position requires specific
# 2 border sides (NW needs N,W border). All 4 corner pieces can rotate to fit
# any corner -> NOT pinned to a specific corner unconditionally.
# Check: does any corner piece fit only ONE corner? (it can always rotate)
print("\nCorner pieces can each rotate to fit any of the 4 corners (2 border")
print("sides adjacent) => NOT pinned to a specific corner unconditionally.")
# Verify
def corner_fits(p):
    base=pieces[p]; fits=[]
    # corner positions need 2 ADJACENT border sides
    needs={'NW':{N,W},'NE':{N,E},'SW':{S,W},'SE':{S,E}}
    for name,need in needs.items():
        for r in range(4):
            ed=rot_edges(base,r)
            bs={i for i in range(4) if ed[i]==BORDER}
            if bs==need: fits.append(name);break
    return fits
for p in corner:
    print(f"  corner piece {p}: fits corners {corner_fits(p)}")
