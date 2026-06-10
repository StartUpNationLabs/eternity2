"""
TRANSEPT gate (vol-208 binding item 1).
Measure the sequential strip-fill depletion mechanism at STRATUM granularity.

Build the board top-to-bottom in horizontal strata of height H. Each stratum is
solved to MaxScore OPTIMUM (RC2) against the REMAINING piece pool, with its top
edge matching the bottom of the stratum above (SOFT seam — we measure how many
seam edges match, we don't force them). Border cells require BORDER outward.

What we measure per stratum:
  - matched edges (internal to stratum + seam to stratum above),
  - pool size remaining,
  - whether the stratum could even be filled (feasibility).
This reproduces Anjou's "sequential => pool depletion" at strip scale and tells us
exactly where/why the greedy strip order dies — the defect TRANSEPT's global
pre-assignment must fix.

NOTE: uses pairwise-AMO RC2 (slow for full 16-wide x H>=2). We cap with a per-
stratum node/time budget by using internal_only on the last resort. For the gate
we use H=2 full-width and accept multi-minute solves; this is a one-shot diagnosis.
"""
import sys, os, time, collections, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v206_mosaic'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2

SIZE, PIECES, HINTS = load_puzzle()
NP = len(PIECES)

def board_border_sides(c):
    x=c%SIZE; y=c//SIZE; s=set()
    if y==0: s.add(N)
    if y==SIZE-1: s.add(S)
    if x==0: s.add(W)
    if x==SIZE-1: s.add(E)
    return s

def solve_stratum(cells, pool, seam_demand, seam_soft=True, card='seq'):
    """cells: list of board cells (a full-width band, row-major).
       pool: set of available piece ids.
       seam_demand: dict cell-> required NORTH color (bottom of stratum above).
         If seam_soft: matching it is rewarded (soft); else forced (hard filter).
       Returns assign, matched_internal, matched_seam, secs, nint, nseam_possible."""
    cellset=set(cells)
    cand={}; var={}; nv=0
    for c in cells:
        bb=board_border_sides(c)
        lst=[]
        for p in pool:
            for r in range(4):
                ed=rot_edges(PIECES[p],r)
                bs={i for i in range(4) if ed[i]==BORDER}
                if bs!=bb: continue
                if (not seam_soft) and c in seam_demand and ed[N]!=seam_demand[c]:
                    continue
                lst.append((p,r,ed))
        cand[c]=lst
        for (p,r,ed) in lst:
            nv+=1; var[(c,p,r)]=nv
    wcnf=WCNF()
    next_var=[nv]
    def newvar():
        next_var[0]+=1; return next_var[0]
    def amo_seq(lits):
        # Sinz sequential at-most-one
        if len(lits)<=1: return
        if len(lits)<=4:
            for a in range(len(lits)):
                for b in range(a+1,len(lits)):
                    wcnf.append([-lits[a],-lits[b]])
            return
        s=[newvar() for _ in range(len(lits)-1)]
        wcnf.append([-lits[0], s[0]])
        wcnf.append([-lits[-1], -s[-1]])
        for i in range(1,len(lits)-1):
            wcnf.append([-lits[i], s[i]])
            wcnf.append([-s[i-1], s[i]])
            wcnf.append([-lits[i], -s[i-1]])
    for c in cells:
        lits=[var[(c,p,r)] for (p,r,ed) in cand[c]]
        if not lits: return None,-1,-1,0.0,0,0
        wcnf.append(lits)             # at least one
        if card=='seq': amo_seq(lits)
        else:
            for a in range(len(lits)):
                for b in range(a+1,len(lits)):
                    wcnf.append([-lits[a],-lits[b]])
    bypiece={}
    for c in cells:
        for (p,r,ed) in cand[c]:
            bypiece.setdefault(p,[]).append(var[(c,p,r)])
    for p,lits in bypiece.items():
        if card=='seq': amo_seq(lits)
        else:
            for a in range(len(lits)):
                for b in range(a+1,len(lits)):
                    wcnf.append([-lits[a],-lits[b]])
    # internal horizontal + vertical edges within stratum
    edges=[]
    for c in cells:
        x=c%SIZE; y=c//SIZE
        if x+1<SIZE and (c+1) in cellset: edges.append((c,E,c+1,W))
        if y+1<SIZE and (c+SIZE) in cellset: edges.append((c,S,c+SIZE,N))
    nint=len(edges)
    for (c1,s1,c2,s2) in edges:
        for (p1,r1,e1) in cand[c1]:
            for (p2,r2,e2) in cand[c2]:
                if p1==p2: continue
                if e1[s1]!=e2[s2]:
                    wcnf.append([-var[(c1,p1,r1)], -var[(c2,p2,r2)]], weight=1)
    # seam: reward matching seam_demand on north of top-row stratum cells (soft).
    nseam=0
    if seam_soft:
        for c,dem in seam_demand.items():
            nseam+=1
            # pay 1 for each candidate that does NOT match the seam demand
            for (p,r,ed) in cand[c]:
                if ed[N]!=dem:
                    wcnf.append([-var[(c,p,r)]], weight=1)
    t0=time.time()
    with RC2(wcnf) as rc2:
        model=rc2.compute(); cost=rc2.cost
    secs=time.time()-t0
    if model is None: return None,-1,-1,secs,nint,nseam
    mset=set(v for v in model if v>0)
    assign={}
    for c in cells:
        for (p,r,ed) in cand[c]:
            if var[(c,p,r)] in mset: assign[c]=(p,r)
    # recompute matched directly from assignment (cost mixes internal+seam)
    mi=0
    for (c1,s1,c2,s2) in edges:
        p1,r1=assign[c1]; p2,r2=assign[c2]
        if rot_edges(PIECES[p1],r1)[s1]==rot_edges(PIECES[p2],r2)[s2]: mi+=1
    ms=0
    for c,dem in seam_demand.items():
        p,r=assign[c]
        if rot_edges(PIECES[p],r)[N]==dem: ms+=1
    return assign, mi, ms, secs, nint, nseam

def run(H=2, card='seq', max_strata=None):
    pool=set(range(NP))
    board={}   # pos->(pid,rot)
    rows_done=0
    total_internal=0; total_seam=0
    print(f"=== sequential strip-fill H={H} card={card} ===", flush=True)
    strat=0
    while rows_done < SIZE:
        h=min(H, SIZE-rows_done)
        cells=[ (rows_done+dy)*SIZE + x for dy in range(h) for x in range(SIZE)]
        # seam demand: for top row of this stratum, north must match south of cell above
        seam={}
        if rows_done>0:
            for x in range(SIZE):
                above=(rows_done-1)*SIZE+x
                pa,ra=board[above]
                seam[(rows_done)*SIZE+x]=rot_edges(PIECES[pa],ra)[S]
        res=solve_stratum(cells, pool, seam, seam_soft=True, card=card)
        if res[0] is None:
            print(f"stratum {strat} rows {rows_done}..{rows_done+h-1}: INFEASIBLE pool={len(pool)}", flush=True)
            break
        assign,mi,ms,secs,nint,nseam=res
        for c,(p,r) in assign.items():
            board[c]=(p,r); pool.discard(p)
        total_internal+=mi; total_seam+=ms
        print(f"stratum {strat} rows {rows_done}..{rows_done+h-1}: "
              f"internal {mi}/{nint}, seam {ms}/{nseam}, pool->{len(pool)}, {secs:.1f}s", flush=True)
        rows_done+=h; strat+=1
        if max_strata and strat>=max_strata: break
    print(f"\nTOTAL matched (internal+seam) = {total_internal+total_seam}", flush=True)
    return board, total_internal+total_seam

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--H', type=int, default=2)
    ap.add_argument('--card', default='seq')
    ap.add_argument('--max-strata', type=int, default=None)
    a=ap.parse_args()
    run(H=a.H, card=a.card, max_strata=a.max_strata)
