"""F2: assignment LP/IP with forbidden-2x2-patch cover cuts.

Variables: z[c,p,r] in [0,1] (LP) or {0,1} (IP): piece p at cell c, rotation r.
Assignment constraints:
  sum_{p,r} z[c,p,r] = 1   for each cell c    (every cell filled)
  sum_{c,r} z[c,p,r] = 1   for each piece p    (every piece used once)
Border constraints baked into allowed (p,r) per cell: a cell on the board
  boundary requires BORDER on the outward sides; interior cells forbid BORDER.

Edge-match indicator (linearized upper bound):
  For a horizontal interior edge between cell c (left) and c+1 (right):
   matched_h[c] <= sum over (p,r),(p',r') with compatible colors of
                   (a var product) -- products aren't linear.
  Instead use the standard linearization: matched edge is matched iff the
  two adjacent cells carry a color-compatible pair. We UPPER BOUND total
  matched via: for each edge and each color k, the edge can be matched in
  color k only if BOTH sides can show color k. Define
   me[edge] = sum_k min( leftshows_k , rightshows_k )? still nonlinear-ish.

Cleanest valid UB used here (the "edge color agreement" LP):
  For each interior edge e=(cL side sL, cR side sR):
    introduce f[e] in [0,1] = matched indicator.
    For each color k:
      sum over (p,r): z[cL,p,r] with rotated(p,r)[sL]==k    =: L_{e,k}
      sum over (p,r): z[cR,p,r] with rotated(p,r)[sR]==k    =: R_{e,k}
    Constraint: f[e] <= sum_k t[e,k], with t[e,k] <= L_{e,k}, t[e,k] <= R_{e,k}.
    (t[e,k] = fractional matched mass in color k; bounded by both sides' mass.)
  Objective: max sum_e f[e].
  Without patch cuts this is the per-edge LP -> gives #edges (=480 at 16x16).

Patch cuts (the PARQUET contribution):
  For each 2x2 window q with cells (TL,TR,BL,BR) and each forbidden ordered
  4-tuple of DISTINCT pieces (a,b,c,d) [forbidden = no rotation makes all 4
  internal edges match], we add the cover inequality:
     z-mass that places a@TL,b@TR,c@BL,d@BR cannot be 1 simultaneously with
     all four internal edges matched... -> too many tuples.
  TRACTABLE patch cut: aggregate. For window q, AT MOST 3 of its 4 internal
  edges can be matched UNLESS the placed 4-tuple is feasible. Since feasible
  4-tuples are rare, but CAN occur, we cannot blanket-cut all to <=3.
  => the genuinely valid cut is per assignment, not aggregate. We add it
  LAZILY: only cut tuples actually realized fractionally above a threshold.

This file implements the per-edge LP base; patch cuts added in f2_cuts.py
via lazy separation. Here we expose build_base_lp returning the highspy model
plus index maps so cuts can be appended.
"""
import sys, itertools
import highspy
import numpy as np
sys.path.insert(0,'.')
from e2lib import rot_edges, BORDER, N,E,S,W, patch_feasible

def allowed_pr(size, pieces, cell):
    """Return list of (p,r) placements valid at cell given border rules."""
    x = cell % size; y = cell // size
    must_border = set()
    if y==0: must_border.add(N)
    if y==size-1: must_border.add(S)
    if x==0: must_border.add(W)
    if x==size-1: must_border.add(E)
    out=[]
    for p,base in enumerate(pieces):
        for r in range(4):
            ed = rot_edges(base, r)
            bsides = {i for i in range(4) if ed[i]==BORDER}
            if bsides == must_border:
                out.append((p,r,ed))
    return out

def build_and_solve_base(size, pieces, hints=None, integer=False, verbose=False):
    """Build the per-edge agreement LP (no patch cuts). Returns (obj, model, idx)."""
    h = highspy.Highs()
    if not verbose:
        h.setOptionValue("output_flag", False)
    ncell = size*size
    # placements per cell
    cell_pr = [allowed_pr(size, pieces, c) for c in range(ncell)]
    # variable index for z[c, j] where j enumerates cell_pr[c]
    zidx = {}
    nvars = 0
    for c in range(ncell):
        for j in range(len(cell_pr[c])):
            zidx[(c,j)] = nvars; nvars += 1
    # We'll add t[e,k] and f[e] vars too. First add z vars.
    inf = highspy.kHighsInf
    # add all z as [0,1]
    h.addVars(nvars, np.zeros(nvars), np.ones(nvars))
    # objective accumulates on f[e]; set later. Track var count.
    var_count = nvars
    def add_var(lb,ub):
        nonlocal var_count
        h.addVars(1, np.array([lb]), np.array([ub]))
        var_count += 1
        return var_count-1
    # assignment: each cell sum_j z=1
    for c in range(ncell):
        idxs = [zidx[(c,j)] for j in range(len(cell_pr[c]))]
        if not idxs:
            return None  # infeasible: cell has no placement
        h.addRow(1.0,1.0,len(idxs), np.array(idxs,dtype=np.int32), np.ones(len(idxs)))
    # each piece used exactly once: sum over cells/placements with piece p =1
    occ = {p:[] for p in range(len(pieces))}
    for c in range(ncell):
        for j,(p,r,ed) in enumerate(cell_pr[c]):
            occ[p].append(zidx[(c,j)])
    for p in range(len(pieces)):
        idxs = occ[p]
        if not idxs:
            return None
        h.addRow(1.0,1.0,len(idxs), np.array(idxs,dtype=np.int32), np.ones(len(idxs)))
    # hints
    if hints:
        for pos,(pid,rot) in hints.items():
            # force z[pos, j*]=1 for the matching placement
            found=None
            for j,(p,r,ed) in enumerate(cell_pr[pos]):
                if p==pid and r==rot: found=j
            if found is None:
                return None
            v=zidx[(pos,found)]
            h.addRow(1.0,1.0,1,np.array([v],dtype=np.int32),np.array([1.0]))
    # edges
    fvars=[]
    # iterate interior edges
    def color_mass_rows(cell, side):
        """map color->list of zidx whose placement shows that color on side."""
        m={}
        for j,(p,r,ed) in enumerate(cell_pr[cell]):
            col=ed[side]
            if col==BORDER: continue
            m.setdefault(col,[]).append(zidx[(cell,j)])
        return m
    for c in range(ncell):
        x=c%size; y=c//size
        nbrs=[]
        if x+1<size: nbrs.append((c, E, c+1, W))
        if y+1<size: nbrs.append((c, S, c+size, N))
        for (cL,sL,cR,sR) in nbrs:
            f=add_var(0.0,1.0); fvars.append(f)
            Lm=color_mass_rows(cL,sL); Rm=color_mass_rows(cR,sR)
            colors=set(Lm)&set(Rm)
            tvars=[]
            for k in colors:
                t=add_var(0.0,1.0); tvars.append(t)
                # t <= sum L_{e,k}
                idxs=Lm[k]+[t]; coef=[1.0]*len(Lm[k])+[-1.0]
                h.addRow(0.0,inf,len(idxs),np.array(idxs,dtype=np.int32),np.array(coef))
                idxs=Rm[k]+[t]; coef=[1.0]*len(Rm[k])+[-1.0]
                h.addRow(0.0,inf,len(idxs),np.array(idxs,dtype=np.int32),np.array(coef))
            # f <= sum t
            if tvars:
                idxs=tvars+[f]; coef=[1.0]*len(tvars)+[-1.0]
                h.addRow(0.0,inf,len(idxs),np.array(idxs,dtype=np.int32),np.array(coef))
            else:
                h.addRow(0.0,0.0,1,np.array([f],dtype=np.int32),np.array([1.0]))
    # objective: maximize sum f
    h.changeObjectiveSense(highspy.ObjSense.kMaximize)
    for f in fvars:
        h.changeColCost(f,1.0)
    if integer:
        # set z vars integer
        for v in range(nvars):
            h.changeColIntegrality(v, highspy.HighsVarType.kInteger)
    h.run()
    obj=h.getObjectiveValue()
    return obj, h, (cell_pr, zidx, fvars)

if __name__=="__main__":
    sys.path.insert(0,'.')
    from e2lib import load_puzzle
    size,pieces,hints=load_puzzle()
    print("Building base per-edge LP on canonical 16x16 (no patch cuts)...")
    import time; t0=time.time()
    res=build_and_solve_base(size,pieces,hints=None,integer=False)
    if res:
        print(f"base LP-UB (no cuts, no hints) = {res[0]:.2f}  in {time.time()-t0:.1f}s")
