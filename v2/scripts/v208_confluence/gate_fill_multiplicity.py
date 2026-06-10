"""
TRANSEPT gate part 4 (vol-208) — optimal-fill multiplicity.

The sharper design ('greedy with EXACT residual-pool lookahead') needs the top
strata to have MANY optimal fills with DIFFERENT leftover pools, so we can choose
the fill that leaves the bottom the most-completable pool. If the optimal stratum
fill is essentially unique (same pieces every time), there is no freedom and the
lookahead is impossible.

Measure on stratum 0 (rows 0-1, full pool) and a mid stratum:
  - solve to optimum cost,
  - enumerate up to K distinct optimal solutions by blocking the piece-SET
    (not placement) of each found optimum,
  - report how many distinct PIECE-SETS achieve the optimum, and the spread of
    leftover pools (how many pieces differ between optima).
"""
import sys, os, time, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v206_mosaic'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2

SIZE, PIECES, HINTS = load_puzzle()
NP=len(PIECES)

def board_border_sides(c):
    x=c%SIZE;y=c//SIZE;s=set()
    if y==0:s.add(N)
    if y==SIZE-1:s.add(S)
    if x==0:s.add(W)
    if x==SIZE-1:s.add(E)
    return s

def build(cells, pool, seam_demand):
    cellset=set(cells); cand={}; var={}; nv=0
    for c in cells:
        bb=board_border_sides(c); lst=[]
        for p in pool:
            for r in range(4):
                ed=rot_edges(PIECES[p],r)
                bs={i for i in range(4) if ed[i]==BORDER}
                if bs!=bb: continue
                lst.append((p,r,ed))
        cand[c]=lst
        for (p,r,ed) in lst:
            nv+=1; var[(c,p,r)]=nv
    return cand,var,nv,cellset

def solve_opt_enum(cells, pool, seam_demand, K=20):
    cand,var,nv,cellset=build(cells,pool,seam_demand)
    base=WCNF(); next_var=[nv]
    def newvar(): next_var[0]+=1; return next_var[0]
    def amo(lits):
        for a in range(len(lits)):
            for b in range(a+1,len(lits)):
                base.append([-lits[a],-lits[b]])
    for c in cells:
        lits=[var[(c,p,r)] for (p,r,ed) in cand[c]]
        if not lits: return None
        base.append(lits); amo(lits)
    bypiece=collections.defaultdict(list)
    for c in cells:
        for (p,r,ed) in cand[c]: bypiece[p].append(var[(c,p,r)])
    for p,lits in bypiece.items(): amo(lits)
    edges=[]
    for c in cells:
        x=c%SIZE;y=c//SIZE
        if x+1<SIZE and (c+1) in cellset: edges.append((c,E,c+1,W))
        if y+1<SIZE and (c+SIZE) in cellset: edges.append((c,S,c+SIZE,N))
    for (c1,s1,c2,s2) in edges:
        for (p1,r1,e1) in cand[c1]:
            for (p2,r2,e2) in cand[c2]:
                if p1==p2: continue
                if e1[s1]!=e2[s2]:
                    base.append([-var[(c1,p1,r1)], -var[(c2,p2,r2)]], weight=1)
    for c,dem in seam_demand.items():
        for (p,r,ed) in cand[c]:
            if ed[N]!=dem: base.append([-var[(c,p,r)]], weight=1)
    # enumerate optima: solve, record cost+piece-set, block this exact piece-set, repeat
    piece_sets=[]; opt_cost=None
    # we must re-create RC2 each time with added hard blocking clauses
    blocking=[]
    for it in range(K):
        w=WCNF()
        w.hard=list(base.hard)+list(blocking)
        w.soft=list(base.soft); w.wght=list(base.wght)
        with RC2(w) as rc2:
            model=rc2.compute(); cost=rc2.cost
        if model is None: break
        if opt_cost is None: opt_cost=cost
        if cost>opt_cost: break  # no more optima
        mset=set(v for v in model if v>0)
        used=set()
        for c in cells:
            for (p,r,ed) in cand[c]:
                if var[(c,p,r)] in mset: used.add(p)
        fs=frozenset(used)
        if fs in piece_sets:
            # block placement-level to force a new piece-set; approx: block one var
            pass
        piece_sets.append(fs)
        # block: forbid using EXACTLY this piece-set => add clause that at least one
        # piece NOT in used must be used, i.e. OR over all vars of pieces not in used.
        notused_vars=[var[(c,p,r)] for c in cells for (p,r,ed) in cand[c] if p not in used]
        if notused_vars: blocking.append(notused_vars)
        else: break
    return opt_cost, piece_sets, len(edges)

def run():
    # stratum 0: rows 0-1, full pool
    pool=set(range(NP))
    cells=[ (0+dy)*SIZE + x for dy in range(2) for x in range(SIZE)]
    print("solving stratum 0 (rows 0-1) optimum + enumerating optima...", flush=True)
    t0=time.time()
    res=solve_opt_enum(cells, pool, {}, K=15)
    if res is None: print("infeasible"); return
    opt_cost, piece_sets, nedge=res
    print(f"  edges={nedge}, optimum matched={nedge-opt_cost} (cost={opt_cost}), "
          f"{time.time()-t0:.1f}s", flush=True)
    print(f"  distinct optimal PIECE-SETS found (cap 15): {len(piece_sets)}")
    if len(piece_sets)>=2:
        # spread: union minus intersection
        u=set().union(*piece_sets); i=set(piece_sets[0])
        for s in piece_sets[1:]: i&=s
        print(f"  union of pieces across optima: {len(u)}; intersection: {len(i)}; "
              f"=> {len(u)-len(i)} pieces are SWAPPABLE while staying optimal")
        print(f"  => leftover-pool freedom EXISTS: {len(u)-len(i)} pieces can be "
              f"pushed to/from the bottom while keeping stratum 0 optimal")
    else:
        print("  optimum piece-set appears unique at this enumeration depth")

if __name__=="__main__":
    run()
