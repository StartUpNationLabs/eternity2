"""Does a bipartite-matching (Hall) feasibility check on remaining
pieces<->cells fire EARLIER than the edge-strict death?

At each dead-end (depth Dd) in edge-strict DFS, walk back up the current
placement path and at each ancestor depth d in {Dd, Dd-1, ...} test:
  Is there a perfect matching between {remaining pieces} and {remaining cells}
  where piece p can go in cell c iff SOME orientation of p fits c's currently
  -placed neighbors (N from above if placed, W from left if placed)?
The shallowest d where matching FAILS = how many levels earlier WATERSHED prunes.

We only check cells whose ABOVE and LEFT neighbors are both placed OR border
(fully-constrained frontier cells) for the binding sub-bipartite, plus we can
use Hopcroft-Karp on the full remaining graph. To keep it tractable we test the
'fully-constrained cells' Hall condition (a NECESSARY sub-condition): the set of
remaining cells each of whose N and W are already determined must have a system
of distinct representatives among remaining pieces.
"""
import sys, time, random
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from collections import defaultdict
import networkx as nx

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
# index: for cell c, given required (Nreq,Wreq) (each maybe None=free), which
# pieces fit? Precompute per-cell maps keyed by constraints we actually hit.
# We'll compute on the fly using cell_pr filtered.

def pieces_fitting(c, place, used):
    """remaining pieces that have an orientation fitting cell c's placed
    neighbors. Returns set of piece ids."""
    x=c%size;y=c//size
    nreq = place[c-size][2][S] if (y>0 and place[c-size]) else (BORDER if y==0 else None)
    wreq = place[c-1][2][E]   if (x>0 and place[c-1])   else (BORDER if x==0 else None)
    out=set()
    for (p,r,ed) in cell_pr[c]:
        if used[p]: continue
        if nreq is not None and ed[N]!=nreq: continue
        if wreq is not None and ed[W]!=wreq: continue
        out.add(p)
    return out

def hall_ok(place, used, only_constrained=True):
    """Bipartite matching feasibility between remaining cells and remaining
    pieces. only_constrained: restrict to cells with BOTH N and W determined
    (binding frontier) — a NECESSARY condition (sub-bipartite must have SDR)."""
    rem_cells=[c for c in range(ncell) if place[c] is None]
    G=nx.Graph(); cell_nodes=[]; 
    for c in rem_cells:
        x=c%size;y=c//size
        n_det = (y==0) or (place[c-size] is not None)
        w_det = (x==0) or (place[c-1] is not None)
        if only_constrained and not (n_det and w_det):
            continue
        fits=pieces_fitting(c,place,used)
        if not fits:
            return False, c  # cell with no piece -> infeasible
        cn=('c',c); cell_nodes.append(cn)
        for p in fits:
            G.add_edge(cn, ('p',p))
    if not cell_nodes:
        return True, None
    m=nx.bipartite.maximum_matching(G, top_nodes=set(cell_nodes))
    matched_cells=sum(1 for cn in cell_nodes if cn in m)
    return (matched_cells==len(cell_nodes)), (None if matched_cells==len(cell_nodes) else 'no-SDR')

def run(node_budget=400_000, seed=1, sample_deaths=200):
    used=[False]*len(pieces);place=[None]*ncell
    nodes=[0];done=[False];rng=random.Random(seed)
    saved=[]  # for each sampled death: levels earlier Hall would've pruned
    deaths_checked=[0]
    sys.setrecursionlimit(100000)
    def cands(c):
        x=c%size;y=c//size
        nkey=place[c-size][2][S] if y>0 else BORDER
        wkey=place[c-1][2][E] if x>0 else BORDER
        return [t for t in bucket[c].get((nkey,wkey),()) if not used[t[0]]]
    def check_death(Dd):
        # walk up: at current path, test Hall at depths Dd, Dd-1, ... while >100
        # We have `place` filled 0..Dd-1 (Dd is the empty dead cell). Test Hall
        # at the current full path (depth Dd) and then progressively "unplace"
        # the last cells to find shallowest failing depth.
        # Save snapshot of placed pieces along path.
        path=[place[c] for c in range(Dd)]
        # test from depth Dd down to max(100, Dd-40)
        first_fail=None
        lo=max(100, Dd-40)
        for d in range(Dd, lo-1, -1):
            # build place/used for prefix of length d
            pl=[None]*ncell; us=[False]*len(pieces)
            for c in range(d):
                pl[c]=path[c]; us[path[c][0]]=True
            ok,_=hall_ok(pl,us,only_constrained=True)
            if not ok:
                first_fail=d
            else:
                break  # once feasible going shallower, stop (monotone-ish)
        if first_fail is not None:
            saved.append(Dd-first_fail)
        else:
            saved.append(0)
    def dfs(c):
        if done[0]:return
        if nodes[0]>=node_budget:done[0]=True;return
        if c==ncell:done[0]=True;return
        cs=cands(c)
        if not cs:
            if c>=140 and deaths_checked[0]<sample_deaths:
                deaths_checked[0]+=1
                check_death(c)
            return
        rng.shuffle(cs)
        for t in cs:
            nodes[0]+=1
            used[t[0]]=True;place[c]=t
            dfs(c+1)
            used[t[0]]=False;place[c]=None
            if done[0]:return
    dfs(0)
    return saved,nodes[0],deaths_checked[0]

t0=time.time()
saved,nodes,nd=run(node_budget=300_000, seed=1, sample_deaths=120)
dt=time.time()-t0
import numpy as np
a=np.array(saved) if saved else np.array([0])
print(f"sampled {nd} deep deaths (depth>=140), nodes={nodes:,}, {dt:.1f}s")
print(f"levels-earlier WATERSHED (constrained-Hall) would prune:")
print(f"  mean={a.mean():.1f} median={np.median(a):.0f} max={a.max()} ")
print(f"  fraction with >=1 level saved: {100*(a>0).mean():.0f}%")
print(f"  fraction with >=5 levels saved: {100*(a>=5).mean():.0f}%")
