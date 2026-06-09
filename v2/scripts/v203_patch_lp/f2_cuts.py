"""F2 with lazy forbidden-patch cuts. Validity-first design.

We build an EXACT MILP-style edge model (not the loose color-mass LP) where
the matched indicator of each internal 2x2 edge is tied to the actual
(piece,rotation) placements, then add forbidden-patch cover cuts.

To keep it tractable and PROVABLY VALID, we use this construction:

z[c,j] in {0,1} (or [0,1] for LP) for placement j=(p,r) at cell c.
Assignment: one per cell, one per piece. (border baked in.)

For each interior edge e between cell A (side sA) and cell B (side sB):
  matched indicator handled implicitly through patch cuts only; the
  OBJECTIVE counts matched edges via auxiliary m[e] in [0,1] with the
  LINKING that m[e] can be 1 only if a color-agreeing placement pair is
  chosen. We use the standard McCormick-free linearization valid for the
  assignment polytope:
     m[e] <= sum_{j in A: showsColor(j,sA)=k} z[A,j]   for the k that...
  -- but m[e] must pick ONE color. Cleanest exact linking:
     m[e] = sum_k y[e,k]      (y[e,k] = matched-in-color-k, <=1)
     y[e,k] <= sum_{j: A shows k on sA} z[A,j]
     y[e,k] <= sum_{j: B shows k on sB} z[B,j]
  At integrality this is EXACT (y[e,k]=1 iff both sides show k). LP relax
  = the loose color-mass LP from f2_patch_lp (gives #edges).

PARQUET cut (lazy, valid): For a 2x2 window q with cells TL,TR,BL,BR and a
specific placement tuple (jTL,jTR,jBL,jBR) that is realized with high mass
in the current solution, if that tuple is FORBIDDEN (the 4 pieces admit no
rotation making all 4 internal edges match -- here we test the SPECIFIC
rotations chosen too: count how many of the 4 internal edges match under
these exact placements = mu_match), then the 4 internal-edge m's summed
cannot all be 1 for this tuple. Valid cut:
    m[e1]+m[e2]+m[e3]+m[e4]
       <= mu_match + (4 - mu_match)*(4 - (zTL+zTR+zBL+zBR))
  i.e. if all 4 z's =1 (tuple fully chosen) RHS = mu_match, capping the
  4 edges at the realizable count. If any z<1, the cut relaxes. This is a
  valid logical cut (big-M with M=4-mu_match, indicator = all four placed).
"""
import sys, time
import highspy
import numpy as np
sys.path.insert(0,'.')
from e2lib import rot_edges, BORDER, N,E,S,W

def allowed_pr(size, pieces, cell):
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
            if bs==mb: out.append((p,r,ed))
    return out

class Model:
    def __init__(self, size, pieces, hints=None, integer=False, verbose=False):
        self.size=size; self.pieces=pieces; self.integer=integer
        self.h=highspy.Highs()
        if not verbose: self.h.setOptionValue("output_flag", False)
        self.h.setOptionValue("threads", 8)
        self.inf=highspy.kHighsInf
        self.ncell=size*size
        self.cell_pr=[allowed_pr(size,pieces,c) for c in range(self.ncell)]
        self.nvar=0
        self.zidx={}
        # add z vars
        for c in range(self.ncell):
            for j in range(len(self.cell_pr[c])):
                self.zidx[(c,j)]=self.nvar; self.nvar+=1
        self.nz=self.nvar
        self.h.addVars(self.nz, np.zeros(self.nz), np.ones(self.nz))
        # edges list and m/y vars
        self.medge={}     # edge_id -> m var
        self.edges=[]     # (cL,sL,cR,sR)
        self._build_assignment(hints)
        self._build_edges()
        self.h.changeObjectiveSense(highspy.ObjSense.kMaximize)
        for e in self.medge.values():
            self.h.changeColCost(e,1.0)
        if integer:
            for v in range(self.nz):
                self.h.changeColIntegrality(v, highspy.HighsVarType.kInteger)

    def _add_var(self,lb,ub):
        self.h.addVars(1,np.array([lb]),np.array([ub]))
        self.nvar+=1; return self.nvar-1
    def _row(self,lo,hi,idxs,coef):
        self.h.addRow(lo,hi,len(idxs),np.array(idxs,dtype=np.int32),np.array(coef,dtype=float))

    def _build_assignment(self,hints):
        for c in range(self.ncell):
            idxs=[self.zidx[(c,j)] for j in range(len(self.cell_pr[c]))]
            self._row(1.0,1.0,idxs,[1.0]*len(idxs))
        occ={p:[] for p in range(len(self.pieces))}
        for c in range(self.ncell):
            for j,(p,r,ed) in enumerate(self.cell_pr[c]):
                occ[p].append(self.zidx[(c,j)])
        for p in range(len(self.pieces)):
            idxs=occ[p]; self._row(1.0,1.0,idxs,[1.0]*len(idxs))
        if hints:
            for pos,(pid,rot) in hints.items():
                found=[j for j,(p,r,ed) in enumerate(self.cell_pr[pos]) if p==pid and r==rot]
                if found: self._row(1.0,1.0,[self.zidx[(pos,found[0])]],[1.0])

    def _color_mass(self,cell,side):
        m={}
        for j,(p,r,ed) in enumerate(self.cell_pr[cell]):
            col=ed[side]
            if col==BORDER: continue
            m.setdefault(col,[]).append(self.zidx[(cell,j)])
        return m

    def _build_edges(self):
        eid=0
        for c in range(self.ncell):
            x=c%self.size;y=c//self.size
            nb=[]
            if x+1<self.size: nb.append((c,E,c+1,W))
            if y+1<self.size: nb.append((c,S,c+self.size,N))
            for (cL,sL,cR,sR) in nb:
                m=self._add_var(0.0,1.0)
                self.medge[(cL,sL,cR,sR)]=m
                self.edges.append((cL,sL,cR,sR))
                Lm=self._color_mass(cL,sL);Rm=self._color_mass(cR,sR)
                colors=set(Lm)&set(Rm)
                tvs=[]
                for k in colors:
                    t=self._add_var(0.0,1.0);tvs.append(t)
                    self._row(0.0,self.inf,Lm[k]+[t],[1.0]*len(Lm[k])+[-1.0])
                    self._row(0.0,self.inf,Rm[k]+[t],[1.0]*len(Rm[k])+[-1.0])
                if tvs:
                    self._row(0.0,self.inf,tvs+[m],[1.0]*len(tvs)+[-1.0])
                else:
                    self._row(0.0,0.0,[m],[1.0])
                eid+=1

    def solve(self):
        self.h.run()
        return self.h.getObjectiveValue()

    def get_sol(self):
        sol=self.h.getSolution()
        return np.array(sol.col_value)

    def window_cells(self, Wr, Wc):
        # 2x2 window at top-left cell (Wr,Wc): cells in row-major
        s=self.size
        TL=Wr*s+Wc; TR=Wr*s+Wc+1; BL=(Wr+1)*s+Wc; BR=(Wr+1)*s+Wc+1
        return TL,TR,BL,BR

    def internal_edges_of_window(self, TL,TR,BL,BR):
        # returns the 4 internal edge keys
        return [(TL,E,TR,W),(BL,E,BR,W),(TL,S,BL,N),(TR,S,BR,N)]

    def separate_and_add(self, val, thresh=0.5):
        """Find violated forbidden-patch cuts in fractional solution `val`.
        Returns number of cuts added."""
        s=self.size; added=0
        for Wr in range(s-1):
            for Wc in range(s-1):
                TL,TR,BL,BR=self.window_cells(Wr,Wc)
                cells=[TL,TR,BL,BR]
                # pick the dominant placement at each cell
                chosen=[]
                ok=True
                for c in cells:
                    best_j=-1;best_v=0.0
                    for j in range(len(self.cell_pr[c])):
                        v=val[self.zidx[(c,j)]]
                        if v>best_v: best_v=v;best_j=j
                    if best_j<0 or best_v<thresh: ok=False;break
                    chosen.append(best_j)
                if not ok: continue
                # the four placements (with rotation)
                pls=[self.cell_pr[cells[i]][chosen[i]] for i in range(4)]
                # count how many internal edges match under THESE placements
                eTL,eTR,eBL,eBR=[pl[2] for pl in pls]
                mu=0
                if eTL[E]==eTR[W]: mu+=1
                if eBL[E]==eBR[W]: mu+=1
                if eTL[S]==eBL[N]: mu+=1
                if eTR[S]==eBR[N]: mu+=1
                if mu==4: continue  # this tuple is fully matchable as placed
                # current m-sum on the 4 edges
                iek=self.internal_edges_of_window(TL,TR,BL,BR)
                msum=sum(val[self.medge[k]] for k in iek)
                if msum <= mu + 1e-6: continue  # not violated
                # add valid cut:
                # sum m[e] <= mu + (4-mu)*(4 - (z1+z2+z3+z4))
                # => sum m[e] + (4-mu)*(z1+z2+z3+z4) <= mu + 4*(4-mu)
                zvars=[self.zidx[(cells[i],chosen[i])] for i in range(4)]
                idxs=[self.medge[k] for k in iek]+zvars
                coef=[1.0]*4+[float(4-mu)]*4
                rhs=mu + 4.0*(4-mu)
                self._row(-self.inf, rhs, idxs, coef)
                added+=1
        return added

def run_with_cuts(size,pieces,hints=None,max_rounds=40,verbose=True):
    m=Model(size,pieces,hints=hints,integer=False)
    obj=m.solve()
    hist=[obj]
    for rnd in range(max_rounds):
        val=m.get_sol()
        added=m.separate_and_add(val)
        if added==0:
            break
        obj=m.solve()
        hist.append(obj)
        if verbose: print(f"  round {rnd+1}: +{added} cuts -> LP-UB={obj:.3f}")
    return obj, hist

if __name__=="__main__":
    from e2lib import load_puzzle
    f=sys.argv[1] if len(sys.argv)>1 else 'small/g4_c5_s1.csv'
    size,pieces,hints=load_puzzle(f)
    print(f"{f}: size={size}")
    obj,hist=run_with_cuts(size,pieces,hints=None,max_rounds=60)
    print(f"FINAL LP-UB with patch cuts = {obj:.3f}  (base was {hist[0]:.3f})")
