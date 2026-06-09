"""MOSAIC composition engine: fill the 16x16 board block-by-block, each block
solved to MaxSAT optimality given fixed boundaries (top + left already placed),
with optional scarcity reservation. Measures final matched-edge score.

Block grid: BS x BS blocks, row-major. Block at (br,bc) covers cells
rows [br*BS .. br*BS+BS-1] x cols [bc*BS .. bc*BS+BS-1].
When solving block (br,bc): cells above (row br*BS-1) and left (col bc*BS-1)
are already placed -> they impose fixed_outer demands on the block's top/left
window-edge cells. The block's bottom/right are free (filled later).
"""
import sys, time
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from collections import defaultdict

size,pieces,hints=load_puzzle()
NP=len(pieces)
# scarcity per piece (min over interior (N,W) presentations of #serving pieces)
supply_pieces=defaultdict(set)
for p in range(NP):
    for r in range(4):
        ed=rot_edges(pieces[p],r)
        if ed[N]!=BORDER and ed[W]!=BORDER: supply_pieces[(ed[N],ed[W])].add(p)
scarcity=[99]*NP
for p in range(NP):
    b=99
    for r in range(4):
        ed=rot_edges(pieces[p],r)
        if ed[N]!=BORDER and ed[W]!=BORDER: b=min(b,len(supply_pieces[(ed[N],ed[W])]))
    scarcity[p]=b

def board_border_sides(c):
    x=c%size;y=c//size;s=set()
    if y==0:s.add(N)
    if y==size-1:s.add(S)
    if x==0:s.add(W)
    if x==size-1:s.add(E)
    return s

def solve_block(cells, pool, fixed_outer, place):
    """Solve one block to MaxSAT. fixed_outer: cell->{side:color}. Returns
    (assign cell->(p,r), internal_matched, boundary_matched, secs) or None."""
    cellset=set(cells)
    cand={}; var={}; nv=0
    for c in cells:
        bb=board_border_sides(c); lst=[]
        for p in pool:
            for r in range(4):
                ed=rot_edges(pieces[p],r)
                bs={i for i in range(4) if ed[i]==BORDER}
                if bs!=bb: continue
                ok=True
                for side,col in fixed_outer.get(c,{}).items():
                    if ed[side]!=col: ok=False;break
                if not ok: continue
                lst.append((p,r,ed))
        cand[c]=lst
        for (p,r,ed) in lst: nv+=1; var[(c,p,r)]=nv
    wcnf=WCNF()
    for c in cells:
        lits=[var[(c,p,r)] for (p,r,ed) in cand[c]]
        if not lits: return None
        wcnf.append(lits)
        for a in range(len(lits)):
            for b in range(a+1,len(lits)): wcnf.append([-lits[a],-lits[b]])
    bypiece=defaultdict(list)
    for c in cells:
        for (p,r,ed) in cand[c]: bypiece[p].append(var[(c,p,r)])
    for p,lits in bypiece.items():
        for a in range(len(lits)):
            for b in range(a+1,len(lits)): wcnf.append([-lits[a],-lits[b]])
    edges=[]
    for c in cells:
        x=c%size;y=c//size
        if x+1<size and (c+1) in cellset: edges.append((c,E,c+1,W))
        if y+1<size and (c+size) in cellset: edges.append((c,S,c+size,N))
    nint=len(edges)
    for (c1,s1,c2,s2) in edges:
        for (p1,r1,e1) in cand[c1]:
            for (p2,r2,e2) in cand[c2]:
                if p1==p2: continue
                if e1[s1]!=e2[s2]:
                    wcnf.append([-var[(c1,p1,r1)],-var[(c2,p2,r2)]],weight=1)
    bmatch=sum(len(d) for d in fixed_outer.values())
    t0=time.time()
    with RC2(wcnf) as rc2:
        model=rc2.compute(); cost=rc2.cost
    secs=time.time()-t0
    if model is None: return None
    mset=set(v for v in model if v>0); assign={}
    for c in cells:
        for (p,r,ed) in cand[c]:
            if var[(c,p,r)] in mset: assign[c]=(p,r)
    return assign, nint-cost, bmatch, secs

def run(BS=4, reserve_frac=0.0, verbose=True):
    """Fill board with BSxBS blocks row-major. reserve_frac: fraction of the
    SCARCEST available pieces withheld from each non-final block's pool."""
    nb=size//BS
    place=[None]*(size*size)  # cell -> (p,r)
    pe=[None]*(size*size)     # cell -> edges tuple
    used=[False]*NP
    total_secs=0
    blocks=[(br,bc) for br in range(nb) for bc in range(nb)]
    for bi,(br,bc) in enumerate(blocks):
        cells=[ (br*BS+dy)*size + (bc*BS+dx) for dy in range(BS) for dx in range(BS)]
        # fixed_outer from placed above/left neighbors
        fo=defaultdict(dict)
        for c in cells:
            x=c%size;y=c//size
            if y>0 and place[c-size] is not None:
                fo[c][N]=pe[c-size][S]
            if x>0 and place[c-1] is not None:
                fo[c][W]=pe[c-1][E]
        pool=set(p for p in range(NP) if not used[p])
        # reservation: withhold scarcest pieces from non-final blocks
        blocks_left=len(blocks)-bi-1
        if reserve_frac>0 and blocks_left>0:
            avail=sorted(pool, key=lambda p: scarcity[p])  # scarcest first
            nres=int(len(pool)*reserve_frac)
            # but never reserve a piece this block NEEDS (border class match) — keep simple: reserve scarcest that are interior
            reserved=set()
            for p in avail:
                if len(reserved)>=nres: break
                # don't reserve corner/edge pieces if this block touches border
                reserved.add(p)
            pool=pool-reserved
        res=solve_block(cells,pool,fo,place)
        if res is None:
            # fallback: use full pool (reservation made it infeasible)
            res=solve_block(cells,set(p for p in range(NP) if not used[p]),fo,place)
        if res is None:
            if verbose: print(f"block {br},{bc}: INFEASIBLE even full pool"); 
            return None
        assign,nint,bmatch,secs=res
        total_secs+=secs
        for c,(p,r) in assign.items():
            place[c]=(p,r); pe[c]=rot_edges(pieces[p],r); used[p]=True
        if verbose: print(f"  block {br},{bc}: internal {nint} + boundary {bmatch} matched, {secs:.1f}s, pool {len(pool)}")
    # final score
    matched=0
    for c in range(size*size):
        x=c%size;y=c//size
        if x+1<size and pe[c][E]==pe[c+1][W]:matched+=1
        if y+1<size and pe[c][S]==pe[c+size][N]:matched+=1
    return matched, total_secs

if __name__=="__main__":
    BS=int(sys.argv[1]) if len(sys.argv)>1 else 4
    rf=float(sys.argv[2]) if len(sys.argv)>2 else 0.0
    print(f"MOSAIC BS={BS} reserve_frac={rf}")
    r=run(BS=BS, reserve_frac=rf)
    if r: print(f"\nFINAL matched = {r[0]}/480   total_solve={r[1]:.0f}s")
