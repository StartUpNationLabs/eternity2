"""Domain reduction on GREEDY (not ground-truth) prefixes — where patch FC
should prune dead branches edge-strict would keep. Build a row-major greedy
edge-strict partial (pick first matching available piece) to depth D, then at
the NEXT cell compare edge-strict vs 2x2 and 2x3 patch-consistent candidate sets.
Also report how often edge-strict has candidates but patch-consistent is EMPTY
(= a wipeout patches detect early but edge-strict misses)."""
import sys, random
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
from collections import defaultdict

size,pieces,hints=load_puzzle()
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
bucket=[defaultdict(list) for _ in range(ncell)]
for c in range(ncell):
    for (p,r,ed) in cell_pr[c]:
        bucket[c][(ed[N],ed[W])].append((p,r,ed))

def es_cands(c,used,place):
    x=c%size;y=c//size
    nkey=place[c-size][2][S] if y>0 else BORDER
    wkey=place[c-1][2][E] if x>0 else BORDER
    return [t for t in bucket[c].get((nkey,wkey),()) if not used[t[0]]]

def completable_2x2(c,t,used):
    x=c%size;y=c//size
    if x+1>=size or y+1>=size:return True
    etl=t[2];cTR=c+1;cBL=c+size;cBR=c+size+1
    trs=[u for u in cell_pr[cTR] if u[2][W]==etl[E] and not used[u[0]] and u[0]!=t[0]]
    if not trs:return False
    bls=[u for u in cell_pr[cBL] if u[2][N]==etl[S] and not used[u[0]] and u[0]!=t[0]]
    if not bls:return False
    for (ptr,rtr,etr) in trs:
        for (pbl,rbl,ebl) in bls:
            if pbl==ptr:continue
            for (pbr,rbr,ebr) in bucket[cBR].get((etr[S],ebl[E]),()):
                if used[pbr] or pbr in (t[0],ptr,pbl):continue
                return True
    return False

def run(seed,maxD=180):
    rng=random.Random(seed)
    used=[False]*len(pieces);place=[None]*ncell
    stats=[]  # (D, es, pc2)
    wipeouts=0
    for c in range(ncell):
        cands=es_cands(c,used,place)
        if not cands: break
        if c>=10 and c<maxD:
            pc2=[t for t in cands if completable_2x2(c,t,used)]
            stats.append((c,len(cands),len(pc2)))
            if cands and not pc2: wipeouts+=1
        # greedy random pick to continue
        t=rng.choice(cands)
        used[t[0]]=True;place[c]=t
    es=sum(s[1] for s in stats);pc=sum(s[2] for s in stats)
    return es,pc,wipeouts,len(stats),c

ES=PC=WO=NS=0
for seed in range(40):
    es,pc,wo,ns,depth=run(seed)
    ES+=es;PC+=pc;WO+=wo;NS+=ns
print(f"40 greedy-random prefixes:")
print(f"  edge-strict candidate-sum = {ES}")
print(f"  2x2-patch-consistent sum  = {PC}  (reduction {100*(ES-PC)/ES if ES else 0:.1f}%)")
print(f"  cells where edge-strict>0 but 2x2-consistent==0 (early wipeouts): {WO} / {NS}")
