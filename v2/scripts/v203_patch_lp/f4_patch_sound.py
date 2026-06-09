"""PARQUET sound tightening of the per-edge LP.

Base = per-edge color-mass LP (SOUND: objective = matched, LP >= true max).
Add per-window patch constraint:
   sum_{e in window q internal} m[e]  <=  3 + sum_{a feasible@q} w[q,a]
with  w[q,a] in [0,1],  w[q,a] <= z[c,j] for each of a's 4 (cell,placement),
and   sum_a w[q,a] <= 1.
This caps "all 4 internal edges matched" to require a feasible patch active.
SOUND: any integral board satisfies it; LP value can only drop toward truth.

Feasible patches per window can be many (interior up to ~4M at 16x16); at
small scale we enumerate all. For canonical we'll do column generation /
restrict later. Here: validate soundness + tightening on small puzzles.
"""
import sys, time
import highspy, numpy as np
from collections import defaultdict
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

def build(size,pieces,hints=None,integer=False,with_patches=True,verbose=False):
    h=highspy.Highs()
    if not verbose:h.setOptionValue("output_flag",False)
    h.setOptionValue("threads",8)
    inf=highspy.kHighsInf
    ncell=size*size
    cell_pr=[allowed_pr(size,pieces,c) for c in range(ncell)]
    nvar=0; zidx={}
    for c in range(ncell):
        for j in range(len(cell_pr[c])):zidx[(c,j)]=nvar;nvar+=1
    nz=nvar
    h.addVars(nz,np.zeros(nz),np.ones(nz))
    def addv(lb,ub):
        nonlocal nvar;h.addVars(1,np.array([lb]),np.array([ub]));nvar+=1;return nvar-1
    def row(lo,hi,idx,co):h.addRow(lo,hi,len(idx),np.array(idx,dtype=np.int32),np.array(co,dtype=float))
    for c in range(ncell):
        idx=[zidx[(c,j)] for j in range(len(cell_pr[c]))];row(1,1,idx,[1.0]*len(idx))
    occ={p:[] for p in range(len(pieces))}
    for c in range(ncell):
        for j,(p,r,ed) in enumerate(cell_pr[c]):occ[p].append(zidx[(c,j)])
    for p in range(len(pieces)):row(1,1,occ[p],[1.0]*len(occ[p]))
    if hints:
        for pos,(pid,rot) in hints.items():
            f=[j for j,(p,r,ed) in enumerate(cell_pr[pos]) if p==pid and r==rot]
            if f:row(1,1,[zidx[(pos,f[0])]],[1.0])
    # per-edge m + color t
    medge={}
    def cmass(cell,side):
        m=defaultdict(list)
        for j,(p,r,ed) in enumerate(cell_pr[cell]):
            if ed[side]!=BORDER:m[ed[side]].append(zidx[(cell,j)])
        return m
    for c in range(ncell):
        x=c%size;y=c//size;nb=[]
        if x+1<size:nb.append((c,E,c+1,W))
        if y+1<size:nb.append((c,S,c+size,N))
        for (cL,sL,cR,sR) in nb:
            mv=addv(0,1);medge[(cL,sL,cR,sR)]=mv
            Lm=cmass(cL,sL);Rm=cmass(cR,sR);cols=set(Lm)&set(Rm);tvs=[]
            for k in cols:
                t=addv(0,1);tvs.append(t)
                row(0,inf,Lm[k]+[t],[1.0]*len(Lm[k])+[-1.0])
                row(0,inf,Rm[k]+[t],[1.0]*len(Rm[k])+[-1.0])
            if tvs:row(0,inf,tvs+[mv],[1.0]*len(tvs)+[-1.0])
            else:row(0,0,[mv],[1.0])
    npat=0
    if with_patches:
        for Wr in range(size-1):
            for Wc in range(size-1):
                TL=Wr*size+Wc;TR=TL+1;BL=TL+size;BR=BL+1
                prTL=cell_pr[TL];prTR=cell_pr[TR];prBL=cell_pr[BL];prBR=cell_pr[BR]
                trW=defaultdict(list)
                for j,(p,r,ed) in enumerate(prTR):trW[ed[W]].append((j,p,r,ed))
                blN=defaultdict(list)
                for j,(p,r,ed) in enumerate(prBL):blN[ed[N]].append((j,p,r,ed))
                brWN=defaultdict(list)
                for j,(p,r,ed) in enumerate(prBR):brWN[(ed[W],ed[N])].append((j,p,r,ed))
                wvars=[]
                for jtl,(ptl,rtl,etl) in enumerate(prTL):
                    for (jtr,ptr,rtr,etr) in trW.get(etl[E],()):
                        if ptr==ptl:continue
                        for (jbl,pbl,rbl,ebl) in blN.get(etl[S],()):
                            if pbl in (ptl,ptr):continue
                            for (jbr,pbr,rbr,ebr) in brWN.get((ebl[E],etr[S]),()):
                                if pbr in (ptl,ptr,pbl):continue
                                wv=addv(0,1);wvars.append(wv)
                                # w <= each z
                                row(-inf,0,[wv,zidx[(TL,jtl)]],[1.0,-1.0])
                                row(-inf,0,[wv,zidx[(TR,jtr)]],[1.0,-1.0])
                                row(-inf,0,[wv,zidx[(BL,jbl)]],[1.0,-1.0])
                                row(-inf,0,[wv,zidx[(BR,jbr)]],[1.0,-1.0])
                                npat+=1
                if wvars:row(0,1,wvars,[1.0]*len(wvars))
                # sum_e m[e] - sum_a w[q,a] <= 3
                ie=[(TL,E,TR,W),(BL,E,BR,W),(TL,S,BL,N),(TR,S,BR,N)]
                idx=[medge[k] for k in ie]+wvars
                co=[1.0]*4+[-1.0]*len(wvars)
                row(-inf,3.0,idx,co)
    h.changeObjectiveSense(highspy.ObjSense.kMaximize)
    for mv in medge.values():h.changeColCost(mv,1.0)
    if integer:
        for v in range(nz):h.changeColIntegrality(v,highspy.HighsVarType.kInteger)
    t0=time.time();h.run()
    return h.getObjectiveValue(),npat,time.time()-t0

if __name__=="__main__":
    from e2lib import load_puzzle
    f=sys.argv[1]
    size,pieces,hints=load_puzzle(f)
    b0,_,_=build(size,pieces,with_patches=False)
    b1,npat,dt=build(size,pieces,with_patches=True)
    print(f"{f}: base={b0:.3f}  PARQUET={b1:.3f}  (#patches={npat}, {dt:.1f}s)")
