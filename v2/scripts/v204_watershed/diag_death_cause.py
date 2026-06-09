"""At each deep death (cell D has no available candidate matching its N,W):
how many pieces that COULD fit cell D (right N,W colors, some rotation) are
ALREADY USED elsewhere? And were they used 'recently' (last 16 placements) or
'long ago'? This distinguishes:
  - LOCAL surprise (0 fitting pieces ever existed -> color demand itself rare)
  - PIECE THEFT (fitting pieces existed but got consumed earlier)
"""
import sys, random
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from collections import defaultdict
import numpy as np

size,pieces,hints=load_puzzle()
ncell=size*size
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
bucket=[defaultdict(list) for _ in range(ncell)]
for c in range(ncell):
    for (p,r,ed) in cell_pr[c]:
        bucket[c][(ed[N],ed[W])].append((p,r,ed))

def run(node_budget=300_000, seed=1, sample=300):
    used=[False]*len(pieces);place=[None]*ncell;placed_at=[-1]*len(pieces)
    nodes=[0];done=[False];rng=random.Random(seed)
    recs=[]  # (depth, n_fit_total, n_fit_used, recent_steal)
    sys.setrecursionlimit(100000)
    def cands(c):
        x=c%size;y=c//size
        nkey=place[c-size][2][S] if y>0 else BORDER
        wkey=place[c-1][2][E] if x>0 else BORDER
        return [t for t in bucket[c].get((nkey,wkey),()) if not used[t[0]]]
    def analyze(c, depth):
        x=c%size;y=c//size
        nkey=place[c-size][2][S] if y>0 else BORDER
        wkey=place[c-1][2][E] if x>0 else BORDER
        fitting=bucket[c].get((nkey,wkey),())  # all pieces (used or not) fitting
        pids=set(t[0] for t in fitting)
        n_total=len(pids)
        n_used=sum(1 for p in pids if used[p])
        # of the used fitting pieces, how many placed in last 16 steps
        recent=sum(1 for p in pids if used[p] and placed_at[p]>=depth-16)
        recs.append((depth,n_total,n_used,recent))
    def dfs(c):
        if done[0]:return
        if nodes[0]>=node_budget:done[0]=True;return
        if c==ncell:done[0]=True;return
        cs=cands(c)
        if not cs:
            if c>=140 and len(recs)<sample:
                analyze(c,c)
            return
        rng.shuffle(cs)
        for t in cs:
            nodes[0]+=1
            used[t[0]]=True;place[c]=t;placed_at[t[0]]=c
            dfs(c+1)
            used[t[0]]=False;place[c]=None;placed_at[t[0]]=-1
            if done[0]:return
    dfs(0)
    return recs,nodes[0]

recs,nodes=run(node_budget=300_000, seed=1, sample=400)
a=np.array(recs)
print(f"sampled {len(recs)} deep deaths, nodes={nodes:,}")
print(f"At death cell D (no available fit for its N,W demand):")
print(f"  # pieces that fit D's (N,W) at ALL (used or not): mean={a[:,1].mean():.2f} median={np.median(a[:,1]):.0f} min={a[:,1].min()} max={a[:,1].max()}")
print(f"  # of those ALREADY USED: mean={a[:,2].mean():.2f}")
print(f"  # used in last 16 steps (recent theft): mean={a[:,3].mean():.2f}")
nz=a[a[:,1]==0]
print(f"  deaths where ZERO pieces EVER fit D's (N,W) [rare color demand]: {len(nz)}/{len(recs)} = {100*len(nz)/len(recs):.0f}%")
stolen=a[(a[:,1]>0)]
print(f"  deaths where pieces existed but all used [piece theft]: {len(stolen)}/{len(recs)} = {100*len(stolen)/len(recs):.0f}%")
