"""Does scarcity-aware value ordering beat greedy on FROM-SCRATCH MaxScore
completion? Row-major, fill every cell (allow mismatches, count matches).
Greedy-edge-first dies a lot, so use a 'soft' MaxScore: at each cell, among
AVAILABLE pieces, choose by a value-order policy; if an edge-matching piece
exists prefer matches, breaking ties by policy. We do a single greedy descent
per seed (no backtracking) to isolate the VALUE-ORDER effect on final score.

Policies:
 'random'   : random available piece (matching preferred)
 'rare_last': among matching pieces, place the one whose (N,W) supply-rank is
              HIGHEST (least scarce) -> reserve scarce pieces. Tie: random.
 'rare_first':opposite (place scarce first) -- control.
We score final matched edges. Compare distributions over seeds.
"""
import sys, random
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
# global scarcity: # pieces that can present (N,W) interior
supply_pieces=defaultdict(set)
for p,base in enumerate(pieces):
    for r in range(4):
        ed=rot_edges(base,r)
        if ed[N]!=BORDER and ed[W]!=BORDER:
            supply_pieces[(ed[N],ed[W])].add(p)
# scarcity score of a piece = min over its interior (N,W) presentations of
# supply-count (how "unique" it is for its rarest pair). Low => scarce.
piece_scarcity=[99]*len(pieces)
for p,base in enumerate(pieces):
    best=99
    for r in range(4):
        ed=rot_edges(base,r)
        if ed[N]!=BORDER and ed[W]!=BORDER:
            best=min(best, len(supply_pieces[(ed[N],ed[W])]))
    piece_scarcity[p]=best

def greedy(seed, policy):
    rng=random.Random(seed)
    used=[False]*len(pieces);place=[None]*ncell
    for c in range(ncell):
        x=c%size;y=c//size
        nreq = place[c-size][2][S] if y>0 else BORDER
        wreq = place[c-1][2][E]   if x>0 else BORDER
        avail=[t for t in cell_pr[c] if not used[t[0]]]
        if not avail:  # shouldn't happen (border classes always have supply early)
            return None
        # matching pieces (both placed-neighbor edges agree)
        match=[t for t in avail if t[2][N]==nreq and t[2][W]==wreq]
        pool = match if match else avail
        if policy=='random':
            t=rng.choice(pool)
        elif policy=='rare_last':
            # prefer LEAST scarce (reserve scarce). tie random.
            mx=max(piece_scarcity[t[0]] for t in pool)
            cand=[t for t in pool if piece_scarcity[t[0]]==mx]
            t=rng.choice(cand)
        elif policy=='rare_first':
            mn=min(piece_scarcity[t[0]] for t in pool)
            cand=[t for t in pool if piece_scarcity[t[0]]==mn]
            t=rng.choice(cand)
        used[t[0]]=True;place[c]=t
    # score
    matched=0
    for c in range(ncell):
        x=c%size;y=c//size
        if x+1<size and place[c][2][E]==place[c+1][2][W]:matched+=1
        if y+1<size and place[c][2][S]==place[c+size][2][N]:matched+=1
    return matched

import numpy as np
for policy in ['random','rare_last','rare_first']:
    scores=[greedy(s,policy) for s in range(60)]
    scores=[s for s in scores if s is not None]
    a=np.array(scores)
    print(f"{policy:10s}: n={len(a)} mean={a.mean():.1f} median={np.median(a):.0f} max={a.max()} min={a.min()}")
