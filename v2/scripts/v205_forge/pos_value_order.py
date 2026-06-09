"""Isolate VALUE-ORDER effect under POSITION variable order (the strong order).
pos + random value vs pos + reserve-scarce (rare_last) vs pos + scarce-first.
Uses full 4-neighbor constraint (in position order only N,W are placed, so this
reduces to N,W constraint — matches the earlier scarcity test but with the
min-damage mismatch handling)."""
import sys, random
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from collections import defaultdict
import numpy as np
size,pieces,hints=load_puzzle()
ncell=size*size;NP=len(pieces)
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
def greedy(policy,seed):
    rng=random.Random(seed);used=[False]*NP;place=[None]*ncell
    for c in range(ncell):
        x=c%size;y=c//size
        nreq=place[c-size][2][S] if y>0 else BORDER
        wreq=place[c-1][2][E] if x>0 else BORDER
        avail=[t for t in cell_pr[c] if not used[t[0]]]
        match=[t for t in avail if t[2][N]==nreq and t[2][W]==wreq]
        if match:
            if policy=='random': t=rng.choice(match)
            elif policy=='rare_last':
                mx=max(scarcity[u[0]] for u in match); t=rng.choice([u for u in match if scarcity[u[0]]==mx])
            elif policy=='scarce_first':
                mn=min(scarcity[u[0]] for u in match); t=rng.choice([u for u in match if scarcity[u[0]]==mn])
        else:
            # min-damage mismatch among available, tie by reserve-scarce if rare_last
            bestmis=9;pool=[]
            for u in avail:
                mis=(u[2][N]!=nreq)+(u[2][W]!=wreq)
                if mis<bestmis:bestmis=mis;pool=[u]
                elif mis==bestmis:pool.append(u)
            if policy=='rare_last':
                mx=max(scarcity[u[0]] for u in pool);pool=[u for u in pool if scarcity[u[0]]==mx]
            t=rng.choice(pool)
        used[t[0]]=True;place[c]=t
    matched=0
    for c in range(ncell):
        x=c%size;y=c//size
        if x+1<size and place[c][2][E]==place[c+1][2][W]:matched+=1
        if y+1<size and place[c][2][S]==place[c+size][2][N]:matched+=1
    return matched
for policy in ['random','rare_last','scarce_first']:
    a=np.array([greedy(policy,s) for s in range(60)])
    print(f"pos + {policy:12s}: mean={a.mean():.1f} median={np.median(a):.0f} max={a.max()}")
