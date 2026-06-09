"""Measure pruning power of patch forward-checks vs edge-strict DFS.
Row-major MaxScore DFS with B&B (optimistic remaining-match upper bound),
counting NODES to reach (and prove) the optimum. Compare:
  mode 'edge'   : edge-strict only (baseline = what engine does)
  mode 'fc2x2'  : + when placing cell c, require the 2x2 with c as TL has
                  >=1 feasible completion among available pieces (look right+down)
  mode 'fcrow'  : + require the next cell in row (c+1) has >=1 candidate AND
                  the 2x2 with c as BL (c is bottom-left, need cell to right in
                  this row + the cell below-right) is completable.
We count search nodes (placements attempted) to find optimum with proof.
"""
import sys, time
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from collections import defaultdict

def prep(size,pieces):
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
    # bucket by (N,W) per cell for fast candidate lookup
    bucket=[]
    for c in range(ncell):
        d=defaultdict(list)
        for (p,r,ed) in cell_pr[c]:
            d[(ed[N],ed[W])].append((p,r,ed))
        bucket.append(d)
    return cell_pr,bucket

def search(size,pieces,mode='edge',time_limit=60):
    ncell=size*size
    cell_pr,bucket=prep(size,pieces)
    total=2*size*(size-1)
    best=[-1];place=[None]*ncell;used=[False]*len(pieces)
    nodes=[0];t0=time.time();to=[False]
    sys.setrecursionlimit(100000)
    def remaining(c):
        cnt=0
        for a in range(ncell):
            x=a%size;y=a//size
            if x+1<size and a+1>=c:cnt+=1
            if y+1<size and a+size>=c:cnt+=1
        return cnt
    def has_completion_2x2_as_TL(c):
        # cells c(TL placed), c+1(TR), c+size(BL), c+size+1(BR) all unplaced
        x=c%size;y=c//size
        if x+1>=size or y+1>=size: return True
        TL=place[c]  # just placed
        etl=TL[2]
        # TR needs W=etl[E]; BL needs N=etl[S]; BR needs (N=TR.S, W=BL.E)
        # search available TR,BL,BR. Bound effort: iterate candidate TR by W, BL by N.
        cTR=c+1;cBL=c+size;cBR=c+size+1
        # candidate TR: bucket[cTR] keyed (N,W) but we only constrain W -> scan
        trs=[t for t in cell_pr[cTR] if t[2][W]==etl[E] and not used[t[0]] and t[0]!=TL[0]]
        if not trs: return False
        bls=[t for t in cell_pr[cBL] if t[2][N]==etl[S] and not used[t[0]] and t[0]!=TL[0]]
        if not bls: return False
        # need some TR,BL,BR distinct with BR matching
        for (ptr,rtr,etr) in trs:
            for (pbl,rbl,ebl) in bls:
                if pbl==ptr: continue
                # BR needs N=etr[S], W=ebl[E]
                for (pbr,rbr,ebr) in bucket[cBR].get((etr[S],ebl[E]),()):
                    if used[pbr] or pbr in (TL[0],ptr,pbl): continue
                    return True
        return False
    def next_cands(c):
        x=c%size;y=c//size
        nkey=place[c-size][2][S] if y>0 else BORDER
        wkey=place[c-1][2][E] if x>0 else BORDER
        return bucket[c].get((nkey,wkey),())
    def dfs(c,matched):
        if to[0]:return
        if time.time()-t0>time_limit:to[0]=True;return
        if c==ncell:
            if matched>best[0]:best[0]=matched
            return
        if matched+remaining(c)<=best[0]:return
        for (p,r,ed) in next_cands(c):
            if used[p]:continue
            nodes[0]+=1
            add=0
            if c%size>0 and place[c-1][2][E]==ed[W]:add+=1
            if c//size>0 and place[c-size][2][S]==ed[N]:add+=1
            used[p]=True;place[c]=(p,r,ed)
            ok=True
            if mode=='fc2x2':
                if not has_completion_2x2_as_TL(c): ok=False
            if ok:
                dfs(c+1,matched+add)
            used[p]=False;place[c]=None
    dfs(0,0)
    return best[0],total,nodes[0],to[0],time.time()-t0

if __name__=="__main__":
    f=sys.argv[1];tl=float(sys.argv[2]) if len(sys.argv)>2 else 60
    size,pieces,hints=load_puzzle(f)
    for mode in ['edge','fc2x2']:
        b,t,n,to,dt=search(size,pieces,mode=mode,time_limit=tl)
        print(f"{f} [{mode:6s}]: max={b}/{t} nodes={n:,} {'TO' if to else 'exact'} {dt:.1f}s")
