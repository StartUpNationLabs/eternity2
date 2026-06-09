"""MOSAIC v2: boundary matches are SOFT, so blocks NEVER go infeasible (any
available pieces of the right border-class fill a block). Each block solved to
MaxSAT maximizing internal + boundary matches given the placed boundary as soft
targets. Sequential fill (no backtrack first) -> always completes. Measures the
full-board score from pure exact-block composition.

This is the right MaxScore composition: it can't 'die', it pays for mismatches.
"""
import sys, time
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from collections import defaultdict
size,pieces,hints=load_puzzle()
NP=len(pieces)
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
def bbs(c):
    x=c%size;y=c//size;s=set()
    if y==0:s.add(N)
    if y==size-1:s.add(S)
    if x==0:s.add(W)
    if x==size-1:s.add(E)
    return s
def solve_block(cells,pool,boundary,pin=None):
    """boundary: cell->{side:color} SOFT targets (from placed outside neighbors).
    pin: cell->(pid,rot) HARD pins (canonical hints). Maximize internal+boundary
    matches. Border-class HARD only (plus pins)."""
    pin=pin or {}
    cellset=set(cells);cand={};var={};nv=0
    for c in cells:
        if c in pin:
            pid,rot=pin[c]; ed=rot_edges(pieces[pid],rot)
            cand[c]=[(pid,rot,ed)]
            nv+=1; var[(c,pid,rot)]=nv
            continue
        bb=bbs(c);lst=[]
        for p in pool:
            for r in range(4):
                ed=rot_edges(pieces[p],r)
                if {i for i in range(4) if ed[i]==BORDER}!=bb:continue
                lst.append((p,r,ed))
        cand[c]=lst
        for t in lst:nv+=1;var[(c,t[0],t[1])]=nv
    wcnf=WCNF()
    for c in cells:
        lits=[var[(c,t[0],t[1])] for t in cand[c]]
        if not lits:return None
        wcnf.append(lits)
        for a in range(len(lits)):
            for b in range(a+1,len(lits)):wcnf.append([-lits[a],-lits[b]])
    bypiece=defaultdict(list)
    for c in cells:
        for t in cand[c]:bypiece[t[0]].append(var[(c,t[0],t[1])])
    for p,lits in bypiece.items():
        for a in range(len(lits)):
            for b in range(a+1,len(lits)):wcnf.append([-lits[a],-lits[b]])
    # internal edges: soft (pay if mismatch)
    edges=[]
    for c in cells:
        x=c%size;y=c//size
        if x+1<size and c+1 in cellset:edges.append((c,E,c+1,W))
        if y+1<size and c+size in cellset:edges.append((c,S,c+size,N))
    nint=len(edges)
    for (c1,s1,c2,s2) in edges:
        for t1 in cand[c1]:
            for t2 in cand[c2]:
                if t1[0]==t2[0]:continue
                if t1[2][s1]!=t2[2][s2]:
                    wcnf.append([-var[(c1,t1[0],t1[1])],-var[(c2,t2[0],t2[1])]],weight=1)
    # boundary edges: soft (reward match = pay if NOT match). For each boundary
    # demand (cell,side,col): pay 1 if the placed piece's side != col.
    nb=0
    for c,d in boundary.items():
        for side,col in d.items():
            nb+=1
            for t in cand[c]:
                if t[2][side]!=col:
                    wcnf.append([-var[(c,t[0],t[1])]],weight=1)
    with RC2(wcnf) as rc2:
        m=rc2.compute();cost=rc2.cost
    if m is None:return None
    mset=set(v for v in m if v>0);assign={}
    for c in cells:
        for t in cand[c]:
            if var[(c,t[0],t[1])] in mset:assign[c]=(t[0],t[1])
    # cost = internal_mismatch + boundary_mismatch; matched = (nint+nb)-cost
    return assign,(nint+nb)-cost,nint,nb
def _block_order(nb, order):
    cells=[(br,bc) for br in range(nb) for bc in range(nb)]
    if order=='row':
        return cells
    if order=='spiral':
        # outer ring inward
        res=[];seen=set();lo=0;hi=nb-1
        while lo<=hi:
            for c in range(lo,hi+1):
                for rc in [(lo,c),(hi,c)]:
                    if rc not in seen:res.append(rc);seen.add(rc)
            for r in range(lo,hi+1):
                for rc in [(r,lo),(r,hi)]:
                    if rc not in seen:res.append(rc);seen.add(rc)
            lo+=1;hi-=1
        return res
    if order=='corners':
        # 4 corner blocks first, then border ring, then interior (by ring)
        center=(nb-1)/2.0
        return sorted(cells, key=lambda rc: -(abs(rc[0]-center)+abs(rc[1]-center)))
    return cells

def run(BS=4,order='row',reserve_frac=0.0,use_hints=False,verbose=True):
    nb=size//BS
    blocks=_block_order(nb, order)
    # canonical hints: cell -> (pid,rot). hints dict from loader is pos->(pid,rot).
    hintmap=dict(hints) if use_hints else {}
    hint_pieces=set(pid for (pid,rot) in hintmap.values())
    place=[None]*(size*size);pe=[None]*(size*size);used=[False]*NP;tsec=0
    for bi,(br,bc) in enumerate(blocks):
        cells=[(br*BS+dy)*size+(bc*BS+dx) for dy in range(BS) for dx in range(BS)]
        cellset=set(cells)
        boundary=defaultdict(dict)
        for c in cells:
            x=c%size;y=c//size
            # check all 4 neighbors; soft-target if placed AND outside this block
            if y>0 and (c-size) not in cellset and place[c-size] is not None:
                boundary[c][N]=pe[c-size][S]
            if y<size-1 and (c+size) not in cellset and place[c+size] is not None:
                boundary[c][S]=pe[c+size][N]
            if x>0 and (c-1) not in cellset and place[c-1] is not None:
                boundary[c][W]=pe[c-1][E]
            if x<size-1 and (c+1) not in cellset and place[c+1] is not None:
                boundary[c][E]=pe[c+1][W]
        # hints inside this block -> pin; remove hint pieces from pool always
        pin={c:hintmap[c] for c in cells if c in hintmap}
        pool=set(p for p in range(NP) if not used[p] and p not in hint_pieces)
        if reserve_frac>0 and bi<len(blocks)-1:
            av=sorted(pool,key=lambda p:scarcity[p])
            pool=pool-set(av[:int(len(pool)*reserve_frac)])
            if not all(True for c in cells):pass
        t0=time.time();res=solve_block(cells,pool,boundary,pin=pin)
        if res is None:
            res=solve_block(cells,set(p for p in range(NP) if not used[p] and p not in hint_pieces),boundary,pin=pin)
        tsec+=time.time()-t0
        assign,m,nint,nbd=res
        for c,(p,r) in assign.items():place[c]=(p,r);pe[c]=rot_edges(pieces[p],r);used[p]=True
        if verbose:print(f"  block {br},{bc}: matched {m}/{nint+nbd} (int {nint}+bnd {nbd}), {time.time()-t0:.1f}s")
    matched=0
    for c in range(size*size):
        x=c%size;y=c//size
        if x+1<size and pe[c][E]==pe[c+1][W]:matched+=1
        if y+1<size and pe[c][S]==pe[c+size][N]:matched+=1
    return matched,tsec,place,pe
def count_hints_obeyed(place):
    ok=0
    for pos,(pid,rot) in hints.items():
        if place[pos] is not None and place[pos][0]==pid and place[pos][1]==rot: ok+=1
    return ok

if __name__=="__main__":
    BS=int(sys.argv[1]) if len(sys.argv)>1 else 4
    rf=float(sys.argv[2]) if len(sys.argv)>2 else 0.0
    uh = (len(sys.argv)>3 and sys.argv[3] in ('1','hints','true','yes'))
    order = sys.argv[4] if len(sys.argv)>4 else 'row'
    print(f"MOSAIC-soft BS={BS} reserve={rf} hints={uh} order={order}")
    r=run(BS=BS,reserve_frac=rf,use_hints=uh,order=order)
    ho=count_hints_obeyed(r[2])
    print(f"\nFINAL matched={r[0]}/480  hints_obeyed={ho}/5  solve={r[1]:.0f}s")
    # persist (never overwrite): timestamped JSON + Bucas URL + history CSV
    from mosaic_io import save_run
    place=r[2]
    lbl=f"mosaic_soft_BS{BS}_rf{rf}_{order}"+("_HINTED" if uh else "")
    d,url=save_run(pieces, place, r[0], lbl,
                   extra={"block_size":BS,"reserve_frac":rf,"hints_obeyed":ho,
                          "use_hints":uh,"order":order,"solve_secs":round(r[1],1)})
    print(f"saved -> {d}")
    print(f"bucas: {url}")
