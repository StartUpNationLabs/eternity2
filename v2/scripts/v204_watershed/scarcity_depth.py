"""Does scarcity-aware VALUE ORDER let edge-strict DFS (with backtracking)
reach greater DEPTH before exhausting a node budget? Max-depth-reached is the
cleanest proxy for 'reduced piece theft'. Compare value orders within identical
edge-strict DFS + node budget.
"""
import sys, random
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from collections import defaultdict

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
supply_pieces=defaultdict(set)
for p,base in enumerate(pieces):
    for r in range(4):
        ed=rot_edges(base,r)
        if ed[N]!=BORDER and ed[W]!=BORDER: supply_pieces[(ed[N],ed[W])].add(p)
piece_scarcity=[99]*len(pieces)
for p,base in enumerate(pieces):
    b=99
    for r in range(4):
        ed=rot_edges(base,r)
        if ed[N]!=BORDER and ed[W]!=BORDER: b=min(b,len(supply_pieces[(ed[N],ed[W])]))
    piece_scarcity[p]=b

def run(policy, node_budget=500_000, seed=1):
    used=[False]*len(pieces);place=[None]*ncell
    nodes=[0];maxd=[0];done=[False];rng=random.Random(seed)
    sys.setrecursionlimit(100000)
    def order(c, cs):
        if policy=='random':
            rng.shuffle(cs); return cs
        if policy=='rare_last':   # least-scarce first (reserve scarce)
            return sorted(cs, key=lambda t:(-piece_scarcity[t[0]], rng.random()))
        if policy=='rare_first':
            return sorted(cs, key=lambda t:(piece_scarcity[t[0]], rng.random()))
    def dfs(c):
        if done[0]:return
        if nodes[0]>=node_budget:done[0]=True;return
        if c>maxd[0]:maxd[0]=c
        if c==ncell:done[0]=True;return
        x=c%size;y=c//size
        nkey=place[c-size][2][S] if y>0 else BORDER
        wkey=place[c-1][2][E] if x>0 else BORDER
        cs=[t for t in bucket[c].get((nkey,wkey),()) if not used[t[0]]]
        if not cs:return
        for t in order(c,cs):
            nodes[0]+=1
            used[t[0]]=True;place[c]=t
            dfs(c+1)
            used[t[0]]=False;place[c]=None
            if done[0]:return
    dfs(0)
    return maxd[0],nodes[0]

import numpy as np
for policy in ['random','rare_last','rare_first']:
    ds=[run(policy, node_budget=400_000, seed=s)[0] for s in range(8)]
    a=np.array(ds)
    print(f"{policy:10s}: max-depth over 8 seeds  mean={a.mean():.0f} median={np.median(a):.0f} best={a.max()} (cells)")
