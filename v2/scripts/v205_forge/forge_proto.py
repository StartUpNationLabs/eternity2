"""FORGE prototype: constraint-centric (MRV + scarcity) DFS for E2 MaxScore.

Genuinely different from E2's cell-position scan orders: at each step pick the
MOST-CONSTRAINED empty cell (fewest available edge-matching candidates =
dynamic MRV), break ties by a cell-urgency score (sum of scarcity of its few
candidate pieces). Value-order: place the LEAST-scarce-elsewhere candidate
(reserve scarce pieces). This makes branching decisions where the search is
tightest, not where position dictates.

We compare, as a single greedy descent AND as a bounded backtracking search:
  - position order (baseline, = vanilla)
  - MRV (most-constrained cell first)
  - MRV + scarcity value-order (FORGE)
Metric: matched edges of the completed/best board (greedy fills all cells,
forced to take a mismatch when no edge-match candidate, choosing min-damage).
"""
import sys, random, time
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from collections import defaultdict

size,pieces,hints=load_puzzle()
ncell=size*size
NP=len(pieces)
def mb(c):
    x=c%size;y=c//size;s=set()
    if y==0:s.add(N)
    if y==size-1:s.add(S)
    if x==0:s.add(W)
    if x==size-1:s.add(E)
    return s
cell_pr=[]
for c in range(ncell):
    m=mb(c);lst=[]
    for p,base in enumerate(pieces):
        for r in range(4):
            ed=rot_edges(base,r)
            bs={i for i in range(4) if ed[i]==BORDER}
            if bs==m:lst.append((p,r,ed))
    cell_pr.append(lst)
# piece scarcity = min over its interior (N,W) presentations of #pieces sharing it
supply_pieces=defaultdict(set)
for p,base in enumerate(pieces):
    for r in range(4):
        ed=rot_edges(base,r)
        if ed[N]!=BORDER and ed[W]!=BORDER: supply_pieces[(ed[N],ed[W])].add(p)
scarcity=[99]*NP
for p,base in enumerate(pieces):
    b=99
    for r in range(4):
        ed=rot_edges(base,r)
        if ed[N]!=BORDER and ed[W]!=BORDER: b=min(b,len(supply_pieces[(ed[N],ed[W])]))
    scarcity[p]=b

def neighbors_colors(c, place):
    """Return (Nreq, Ereq, Sreq, Wreq) from PLACED neighbors, else None (free).
    For border sides the requirement is BORDER."""
    x=c%size;y=c//size
    req=[None,None,None,None]
    # N
    if y==0: req[N]=BORDER
    elif place[c-size] is not None: req[N]=place[c-size][2][S]
    # S
    if y==size-1: req[S]=BORDER
    elif place[c+size] is not None: req[S]=place[c+size][2][N]
    # W
    if x==0: req[W]=BORDER
    elif place[c-1] is not None: req[W]=place[c-1][2][E]
    # E
    if x==size-1: req[E]=BORDER
    elif place[c+1] is not None: req[E]=place[c+1][2][N]  # bug guard below
    if x<size-1 and place[c+1] is not None: req[E]=place[c+1][2][W]
    return req

def candidates(c, place, used):
    req=neighbors_colors(c,place)
    out=[]
    for (p,r,ed) in cell_pr[c]:
        if used[p]: continue
        ok=True
        for s in range(4):
            if req[s] is not None and ed[s]!=req[s]: ok=False;break
        if ok: out.append((p,r,ed))
    return out

def greedy(policy, seed):
    rng=random.Random(seed)
    used=[False]*NP; place=[None]*ncell; filled=0
    # For MRV we recompute candidate counts among empty cells each step (O(ncell*..)).
    empty=set(range(ncell))
    while empty:
        if policy=='pos':
            c=min(empty)
            cand=candidates(c,place,used)
        else:
            # MRV: pick empty cell with fewest candidates
            best_c=None;best_cand=None;best_k=10**9;best_urg=None
            for cc in empty:
                cand=candidates(cc,place,used)
                k=len(cand)
                # urgency tiebreak: prefer cells whose candidates are scarce (must place now)
                urg = -min((scarcity[t[0]] for t in cand), default=99)
                if (k,urg)<(best_k, best_urg if best_urg is not None else 10**9):
                    best_k=k;best_c=cc;best_cand=cand;best_urg=urg
            c=best_c;cand=best_cand
        if not cand:
            # forced mismatch: take any available piece minimizing new mismatches
            req=neighbors_colors(c,place)
            bestt=None;bestmis=99
            for (p,r,ed) in cell_pr[c]:
                if used[p]:continue
                mis=sum(1 for s in range(4) if req[s] is not None and req[s]!=BORDER and ed[s]!=req[s])
                if mis<bestmis: bestmis=mis;bestt=(p,r,ed)
            if bestt is None:  # no available piece of this border class (rare)
                # take any available piece ignoring border (shouldn't matter for score much)
                for (p,r,ed) in [ (pp,rr,rot_edges(pieces[pp],rr)) for pp in range(NP) if not used[pp] for rr in range(4)]:
                    bestt=(p,r,ed);break
            t=bestt
        else:
            if policy in ('pos','mrv'):
                t=rng.choice(cand)
            else: # forge: reserve scarce -> place least-scarce
                mx=max(scarcity[u[0]] for u in cand)
                t=rng.choice([u for u in cand if scarcity[u[0]]==mx])
        used[t[0]]=True; place[c]=t; empty.discard(c); filled+=1
    # score
    matched=0
    for c in range(ncell):
        x=c%size;y=c//size
        if x+1<size and place[c][2][E]==place[c+1][2][W]:matched+=1
        if y+1<size and place[c][2][S]==place[c+size][2][N]:matched+=1
    return matched

import numpy as np
t0=time.time()
for policy in ['pos','mrv','forge']:
    sc=[greedy(policy,s) for s in range(20)]
    a=np.array(sc)
    print(f"{policy:6s}: mean={a.mean():.1f} median={np.median(a):.0f} max={a.max()} min={a.min()}")
print(f"({time.time()-t0:.1f}s)")
