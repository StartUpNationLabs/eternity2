"""MOSAIC window-MaxSAT primitive: given a rectangular window of cells, a pool of
available pieces, and FIXED boundary demands (colors that window-edge cells must
match on sides facing already-placed pieces outside the window), assign pieces to
window cells maximizing matched edges (internal window edges + boundary edges).

Weighted partial MaxSAT via pysat RC2.
Variables x[(cell,pid,rot)]. We restrict candidate (pid,rot) per cell by border
(window cells on the BOARD border need BORDER outward) — passed via board geometry.

Returns (assignment dict cell->(pid,rot), matched_count, solve_seconds).
"""
import sys, time, itertools
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from pysat.card import CardEnc, EncType

def solve_window(size, pieces, cells, pool, fixed_outer, placed_edges,
                 internal_only=False, timeout=None, verbose=False):
    """
    cells: list of board cell indices in the window.
    pool: set of available piece ids usable in this window.
    fixed_outer: dict cell-> {side: color} demands from pieces OUTSIDE window
                 already placed (boundary match targets).
    placed_edges: dict cell->(N,E,S,W) for ALL placed cells (for boundary scoring,
                  not strictly needed beyond fixed_outer).
    Returns assignment, matched, secs.
    """
    cellset=set(cells)
    # candidate (pid,rot) per cell respecting BOARD border
    def board_border_sides(c):
        x=c%size;y=c//size;s=set()
        if y==0:s.add(N)
        if y==size-1:s.add(S)
        if x==0:s.add(W)
        if x==size-1:s.add(E)
        return s
    cand={}
    var={}; nv=0
    for c in cells:
        bb=board_border_sides(c)
        lst=[]
        for p in pool:
            for r in range(4):
                ed=rot_edges(pieces[p],r)
                bs={i for i in range(4) if ed[i]==BORDER}
                if bs!=bb: continue
                # must also satisfy any fixed_outer demand on this cell
                ok=True
                for side,col in fixed_outer.get(c,{}).items():
                    if ed[side]!=col: ok=False;break
                if not ok: continue
                lst.append((p,r,ed))
        cand[c]=lst
        for (p,r,ed) in lst:
            nv+=1; var[(c,p,r)]=nv
    wcnf=WCNF()
    # each cell exactly one placement (hard). Use sequential card =1.
    for c in cells:
        lits=[var[(c,p,r)] for (p,r,ed) in cand[c]]
        if not lits:
            return None, -1, 0.0  # infeasible window
        # at least one
        wcnf.append(lits)
        # at most one (pairwise for small; cells small so ok)
        for a in range(len(lits)):
            for b in range(a+1,len(lits)):
                wcnf.append([-lits[a],-lits[b]])
    # each piece used at most once across window
    bypiece={}
    for c in cells:
        for (p,r,ed) in cand[c]:
            bypiece.setdefault(p,[]).append(var[(c,p,r)])
    for p,lits in bypiece.items():
        for a in range(len(lits)):
            for b in range(a+1,len(lits)):
                wcnf.append([-lits[a],-lits[b]])
    # soft: internal window edges match. For edge between c1(side s1) and c2(side s2)
    # both in window: matched iff colors equal. Encode soft via reified equality is
    # heavy; instead use: for each ordered pair of placements that DISAGREE on the
    # shared edge, add soft clause penalizing... Simpler: add a soft 'match' var.
    # match_var m=1 rewarded (weight1). Hard: m -> (placements agree). We encode
    # m <-> OR over agreeing placement-combos -- too many. Use the standard:
    #   for the edge, for every (placement of c1, placement of c2) that MISMATCH,
    #   add soft clause (-x_c1 OR -x_c2) weight 1  == pay 1 if both chosen & mismatch.
    # Then objective maximizes matches = (#edges) - (#mismatch penalties paid).
    # RC2 MINIMIZES weight of falsified soft clauses; a soft clause (-x1 OR -x2)
    # is falsified iff x1&x2 both true -> pays weight. So total paid = #mismatched
    # placed edges. Maximize matches <=> minimize this. 
    edges=[]
    for c in cells:
        x=c%size;y=c//size
        if x+1<size and (c+1) in cellset: edges.append((c,E,c+1,W))
        if y+1<size and (c+size) in cellset: edges.append((c,S,c+size,N))
    nedge_internal=len(edges)
    for (c1,s1,c2,s2) in edges:
        for (p1,r1,e1) in cand[c1]:
            for (p2,r2,e2) in cand[c2]:
                if p1==p2: continue
                if e1[s1]!=e2[s2]:
                    wcnf.append([-var[(c1,p1,r1)], -var[(c2,p2,r2)]], weight=1)
    # boundary edges: window cell side facing a placed-outside cell. fixed_outer
    # already FORCES those to match (hard) by candidate filtering -> they are
    # guaranteed matched, count them as matched_bonus.
    boundary_matched=sum(len(d) for d in fixed_outer.values())
    t0=time.time()
    with RC2(wcnf) as rc2:
        model=rc2.compute()
        cost=rc2.cost
    secs=time.time()-t0
    if model is None: return None, -1, secs
    mset=set(v for v in model if v>0)
    assign={}
    for c in cells:
        for (p,r,ed) in cand[c]:
            if var[(c,p,r)] in mset: assign[c]=(p,r)
    matched_internal = nedge_internal - cost
    return assign, matched_internal+boundary_matched, secs, nedge_internal, boundary_matched

if __name__=="__main__":
    size,pieces,hints=load_puzzle()
    # Test: a KxK window in the interior with NO boundary constraints, pool = all
    # interior pieces. Measure solve time + matched as window grows.
    import sys
    for (h,w) in [(2,2),(2,3),(3,3),(3,4),(4,4),(2,8),(3,5)]:
        # build window cells at top-left interior corner (1,1)
        cells=[ (1+dy)*size + (1+dx) for dy in range(h) for dx in range(w)]
        pool=set(p for p,b in enumerate(pieces) if sum(1 for c in b if c==BORDER)==0)  # interior pieces
        res=solve_window(size,pieces,cells,pool,{},{})
        if res[0] is None:
            print(f"{h}x{w}: INFEASIBLE")
        else:
            assign,matched,secs,nint,nb=res
            print(f"{h}x{w} ({h*w} cells): matched_internal={matched}/{nint}  solve={secs:.2f}s  pool={len(pool)}")
