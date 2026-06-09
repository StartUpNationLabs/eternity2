"""Diagnose WHERE and (first cut at) WHY edge-strict DFS dies on canonical E2.
Run edge-strict row-major DFS (no hints, no MaxScore — pure feasibility) for a
fixed node budget; whenever we reach a cell with ZERO candidates (a dead-end),
record the depth. Also track the running max depth. This profiles the death
distribution that any deeper-search streamliner must beat.
"""
import sys, time, random
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from collections import defaultdict, Counter

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

def run(node_budget=2_000_000, seed=0, shuffle=True):
    used=[False]*len(pieces);place=[None]*ncell
    deaths=Counter()  # depth -> count of dead-ends at that depth
    nodes=[0];maxd=[0];rng=random.Random(seed)
    sys.setrecursionlimit(100000)
    done=[False]
    def cands(c):
        x=c%size;y=c//size
        nkey=place[c-size][2][S] if y>0 else BORDER
        wkey=place[c-1][2][E] if x>0 else BORDER
        cs=[t for t in bucket[c].get((nkey,wkey),()) if not used[t[0]]]
        return cs
    def dfs(c):
        if done[0]:return
        if nodes[0]>=node_budget:done[0]=True;return
        if c>maxd[0]:maxd[0]=c
        if c==ncell:done[0]=True;return  # solved (won't happen)
        cs=cands(c)
        if not cs:
            deaths[c]+=1
            return
        if shuffle: rng.shuffle(cs)
        for t in cs:
            nodes[0]+=1
            used[t[0]]=True;place[c]=t
            dfs(c+1)
            used[t[0]]=False;place[c]=None
            if done[0]:return
    dfs(0)
    return deaths,nodes[0],maxd[0]

t0=time.time()
deaths,nodes,maxd=run(node_budget=3_000_000, seed=1)
dt=time.time()-t0
print(f"nodes={nodes:,} max_depth_reached={maxd} ({dt:.1f}s)")
tot=sum(deaths.values())
print(f"total dead-ends recorded: {tot:,}")
# death distribution by depth band
bands=defaultdict(int)
for d,n in deaths.items():
    bands[(d//16)]+=n   # by row
print("row | dead-ends in this row (cells row*16..row*16+15)")
for r in sorted(bands):
    print(f"  {r:2d} ({r*16:3d}-{r*16+15:3d}) | {bands[r]:,}")
# where is the MASS of deaths
import numpy as np
ds=[]
for d,n in deaths.items(): ds+= [d]*min(n,100000)
if ds:
    a=np.array(ds)
    print(f"\ndeath depth: min={a.min()} p25={np.percentile(a,25):.0f} median={np.percentile(a,50):.0f} p75={np.percentile(a,75):.0f} max={a.max()}")
