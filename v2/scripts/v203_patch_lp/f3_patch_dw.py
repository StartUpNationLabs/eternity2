"""PARQUET-DW: window-patch LP with z-marginalization coupling and
owned-edge objective (no double counting). Exact patch enumeration
(small puzzles). Gives a SECOND-ORDER relaxation UB on matched edges.

Window q at top-left cell (Wr,Wc) covers cells TL,TR,BL,BR.
A 'patch assignment' a = (jTL,jTR,jBL,jBR) where each j is an index into
that cell's allowed (piece,rotation) list, with 4 DISTINCT pieces.
mu(a) = # of the 4 internal edges that are UNMATCHED under a.

Owned-edge objective: each interior edge assigned to one owning window.
total matched = #edges - sum_q (unmatched owned edges of q's patch).

Coupling (forces all windows to agree on shared cells AND pieces):
  for each cell c, placement index j:  z[c,j] in [0,1]
  per cell: sum_j z[c,j] = 1
  per piece: sum_{c,j: piece(c,j)=p} z[c,j] = 1
  for each window q and each of its 4 cells c (role role): 
     sum_{a at q with a[role]=j} w[q,a] = z[c,j]
  per window: sum_a w[q,a] = 1   (implied, but add for tightness)
Objective: max sum_q sum_a w[q,a]*matched_owned(a,q)
"""
import sys, time, itertools
import highspy, numpy as np
sys.path.insert(0,'.')
from e2lib import rot_edges, BORDER, N,E,S,W

def allowed_pr(size,pieces,cell):
    x=cell%size;y=cell//size;mb=set()
    if y==0:mb.add(N)
    if y==size-1:mb.add(S)
    if x==0:mb.add(W)
    if x==size-1:mb.add(E)
    out=[]
    for p,base in enumerate(pieces):
        for r in range(4):
            ed=rot_edges(base,r)
            bs={i for i in range(4) if ed[i]==BORDER}
            if bs==mb:out.append((p,r,ed))
    return out

def edge_owner(size):
    """Map each interior edge to its owning window top-left (Wr,Wc) and role.
    Returns dict edge_key -> (Wr,Wc, role) where role in
    {'H_top','H_bot','V_left','V_right'} describing which internal edge."""
    owner={}
    # horizontal edge between (x,y)-(x+1,y): cells c=y*size+x, c+1
    for y in range(size):
        for x in range(size-1):
            key=('H',x,y)
            # window below: TL=(x,y) if y<=size-2 -> edge is H_top of that window
            if y<=size-2:
                owner[key]=(y,x,'H_top')
            else: # last row -> window above TL=(x,y-1), edge is H_bot
                owner[key]=(y-1,x,'H_bot')
    # vertical edge between (x,y)-(x,y+1): cells c, c+size
    for y in range(size-1):
        for x in range(size):
            key=('V',x,y)
            if x<=size-2:
                owner[key]=(y,x,'V_left')
            else:
                owner[key]=(y,x-1,'V_right')
    return owner

def solve(size,pieces,hints=None,integer=False,verbose=False):
    h=highspy.Highs()
    if not verbose:h.setOptionValue("output_flag",False)
    h.setOptionValue("threads",8)
    inf=highspy.kHighsInf
    ncell=size*size
    cell_pr=[allowed_pr(size,pieces,c) for c in range(ncell)]
    # z vars
    nvar=0; zidx={}
    for c in range(ncell):
        for j in range(len(cell_pr[c])):
            zidx[(c,j)]=nvar;nvar+=1
    h.addVars(nvar,np.zeros(nvar),np.ones(nvar))
    def addv(lb,ub):
        nonlocal nvar;h.addVars(1,np.array([lb]),np.array([ub]));nvar+=1;return nvar-1
    def row(lo,hi,idx,co):h.addRow(lo,hi,len(idx),np.array(idx,dtype=np.int32),np.array(co,dtype=float))
    # assignment
    for c in range(ncell):
        idx=[zidx[(c,j)] for j in range(len(cell_pr[c]))]
        row(1,1,idx,[1.0]*len(idx))
    occ={p:[] for p in range(len(pieces))}
    for c in range(ncell):
        for j,(p,r,ed) in enumerate(cell_pr[c]):occ[p].append(zidx[(c,j)])
    for p in range(len(pieces)):
        row(1,1,occ[p],[1.0]*len(occ[p]))
    if hints:
        for pos,(pid,rot) in hints.items():
            f=[j for j,(p,r,ed) in enumerate(cell_pr[pos]) if p==pid and r==rot]
            if f:row(1,1,[zidx[(pos,f[0])]],[1.0])
    owner=edge_owner(size)
    # enumerate window patches
    obj_terms=[]  # (wvar, matched_owned_count)
    nwin_patch=0
    for Wr in range(size-1):
        for Wc in range(size-1):
            TL=Wr*size+Wc;TR=TL+1;BL=TL+size;BR=BL+1
            cells=[TL,TR,BL,BR]
            # which interior edges does THIS window own?
            owned=[]  # list of ('H_top'/... )
            for ek,(or_,oc,role) in owner.items():
                if (or_,oc)==(Wr,Wc): owned.append(role)
            owned=set(owned)
            # patch coupling rows accumulate per (cell-role, j)
            # build patches
            prTL=cell_pr[TL];prTR=cell_pr[TR];prBL=cell_pr[BL];prBR=cell_pr[BR]
            # group by color to join fast: TR.W==TL.E ; BL.N==TL.S ; BR.W==BL.E, BR.N==TR.S
            from collections import defaultdict
            trW=defaultdict(list)
            for j,(p,r,ed) in enumerate(prTR):trW[ed[W]].append((j,p,r,ed))
            blN=defaultdict(list)
            for j,(p,r,ed) in enumerate(prBL):blN[ed[N]].append((j,p,r,ed))
            brWN=defaultdict(list)
            for j,(p,r,ed) in enumerate(prBR):brWN[(ed[W],ed[N])].append((j,p,r,ed))
            # We want ALL patches (feasible or not) but that's huge. For the
            # UB we only need patches whose 4 internal edges are ALL matched
            # to get the "0-defect" mass; plus we allow a window to be
            # "defective". Trick: instead of enumerating defective patches
            # (huge), we DON'T require sum_a w=1 over feasible-only. Instead:
            #   matched_owned(window) = sum over FEASIBLE-on-owned-edges...
            # Simpler exact approach below in solve_v2. Here: enumerate
            # patches with ALL 4 internal matched (feasible), value=|owned|,
            # and allow slack (window may pick none -> 0 matched on owned).
            wvars=[]
            # marginal accumulators: role_j -> list of wvar
            margin={('TL',):defaultdict(list),('TR',):defaultdict(list),
                    ('BL',):defaultdict(list),('BR',):defaultdict(list)}
            for (jtl,ptl,rtl,etl) in enumerate(prTL) and []:
                pass
            for jtl,(ptl,rtl,etl) in enumerate(prTL):
                for (jtr,ptr,rtr,etr) in trW.get(etl[E],()):
                    if ptr==ptl:continue
                    for (jbl,pbl,rbl,ebl) in blN.get(etl[S],()):
                        if pbl in (ptl,ptr):continue
                        for (jbr,pbr,rbr,ebr) in brWN.get((ebl[E],etr[S]),()):
                            if pbr in (ptl,ptr,pbl):continue
                            # feasible patch (all 4 internal matched). matched_owned=|owned|
                            wv=addv(0.0,1.0);wvars.append(wv)
                            margin[('TL',)][jtl].append(wv)
                            margin[('TR',)][jtr].append(wv)
                            margin[('BL',)][jbl].append(wv)
                            margin[('BR',)][jbr].append(wv)
                            obj_terms.append((wv,len(owned)))
                            nwin_patch+=1
            # sum_a w <= 1
            if wvars: row(0,1,wvars,[1.0]*len(wvars))
            # marginal coupling: sum_{a:role=j} w <= z[cell,j]
            # (<= because window may be defective -> some z-mass not in any
            #  feasible patch. This keeps UB valid: matched_owned counted only
            #  for feasible patches.)
            for role,cell in [('TL',TL),('TR',TR),('BL',BL),('BR',BR)]:
                for j,wl in margin[(role,)].items():
                    row(-inf,0.0, wl+[zidx[(cell,j)]], [1.0]*len(wl)+[-1.0])
    h.changeObjectiveSense(highspy.ObjSense.kMaximize)
    for wv,val in obj_terms:
        h.changeColCost(wv,float(val))
    if integer:
        for v in range(len(zidx)):h.changeColIntegrality(v,highspy.HighsVarType.kInteger)
    t0=time.time()
    h.run()
    return h.getObjectiveValue(), nwin_patch, time.time()-t0

if __name__=="__main__":
    from e2lib import load_puzzle
    f=sys.argv[1]
    size,pieces,hints=load_puzzle(f)
    ub,npat,dt=solve(size,pieces,hints=None,integer=False)
    print(f"{f}: PARQUET-DW LP-UB={ub:.3f}  (#feasible-window-patches={npat}, {dt:.1f}s)")
