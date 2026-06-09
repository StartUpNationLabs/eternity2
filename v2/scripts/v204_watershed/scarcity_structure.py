"""Global scarcity structure: for each (N,W) interior color pair, how many
piece-orientations can produce it? This is the 'supply' per demand-type.
Also: the demand side — across high-score boards, how often each (N,W) pair
is demanded. Scarcity = pairs with low supply but nonzero demand."""
import sys
sys.path.insert(0,'.')
from e2lib import load_puzzle, load_board, rot_edges, BORDER, N,E,S,W
from collections import Counter, defaultdict

size,pieces,hints=load_puzzle()
# supply: count piece-orientations giving each (N,W) with neither = BORDER (interior cell)
supply=Counter()       # (n,w) -> # orientations across all pieces
supply_pieces=defaultdict(set)
for p,base in enumerate(pieces):
    for r in range(4):
        ed=rot_edges(base,r)
        if ed[N]!=BORDER and ed[W]!=BORDER:
            supply[(ed[N],ed[W])]+=1
            supply_pieces[(ed[N],ed[W])].add(p)
colors=sorted({c for base in pieces for c in base if c!=BORDER})
print(f"interior colors: {len(colors)}")
print(f"# distinct (N,W) interior pairs with >=1 supply: {len(supply)} / {len(colors)**2} possible")
# supply distribution
dist=Counter(supply.values())
print("supply (orientations per (N,W) pair) histogram:")
for s in sorted(dist):
    print(f"  {s:3d} orientations : {dist[s]} pairs")
# distinct PIECES (not orientations) per pair
pdist=Counter(len(v) for v in supply_pieces.values())
print("distinct-PIECES per (N,W) pair histogram:")
for s in sorted(pdist):
    print(f"  {s:3d} pieces : {pdist[s]} pairs")
# demand: from McGavin, count (above.S, left.E) per interior cell
board,_=load_board('../../output/vol-65/mcgavin_469.json')
def col(c):
    pid,rot=board[c];return rot_edges(pieces[pid],rot)
demand=Counter()
for c in range(size*size):
    x=c%size;y=c//size
    if x>0 and y>0:
        n=col(c-size)[S]; w=col(c-1)[E]
        if n!=BORDER and w!=BORDER:
            demand[(n,w)]+=1
# scarcity ratio: demand / supply_pieces
print("\nTightest (N,W) pairs by demand/supply (McGavin demand):")
rows=[]
for pair,d in demand.items():
    s=len(supply_pieces.get(pair,()))
    rows.append((d/max(s,1), d, s, pair))
rows.sort(reverse=True)
for ratio,d,s,pair in rows[:15]:
    print(f"  pair{pair}: demand={d} supply_pieces={s} ratio={ratio:.2f}")
