"""How much does PATCH-consistency shrink candidate domains vs edge-strict?
On canonical E2, simulate a row-major partial fill from a high board, and at
each newly-exposed cell measure:
  |edge-strict candidates| (pieces matching N,W of placed neighbors, available)
  |patch-consistent subset| (those that ALSO leave the 2x2-with-c-as-TL
     completable to all-matched among available pieces) -- the SOUND streamliner
We sample partial prefixes of McGavin's board (a near-solution) at various depths
to get realistic domain sizes.
"""
import sys, time
sys.path.insert(0,'.')
from e2lib import load_puzzle, load_board, rot_edges, BORDER, N,E,S,W
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

# load McGavin as the "ground truth" near-solution to define realistic prefixes
board,_=load_board('../../output/vol-65/mcgavin_469.json')

def measure_at_depth(D):
    """Place McGavin's pieces at cells 0..D-1, then measure domain at cell D."""
    used=[False]*len(pieces);place=[None]*ncell
    for c in range(D):
        pid,rot=board[c]
        place[c]=(pid,rot,rot_edges(pieces[pid],rot));used[pid]=True
    c=D
    x=c%size;y=c//size
    nkey=place[c-size][2][S] if y>0 else BORDER
    wkey=place[c-1][2][E] if x>0 else BORDER
    es=[t for t in bucket[c].get((nkey,wkey),()) if not used[t[0]]]
    # patch-consistent subset: placing t leaves 2x2(c as TL) completable all-matched
    def completable(t):
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
    pc=[t for t in es if completable(t)]
    return len(es),len(pc)

print("depth | edge-strict cands | patch-consistent | reduction")
import statistics
es_tot=pc_tot=0;n=0
for D in range(20, 240, 12):
    e,p=measure_at_depth(D)
    es_tot+=e;pc_tot+=p;n+=1
    print(f"{D:4d}  | {e:6d}            | {p:6d}          | {100*(e-p)/e if e else 0:.0f}%")
print(f"\nTOTALS over sampled depths: edge-strict={es_tot} patch-consistent={pc_tot} "
      f"avg reduction={100*(es_tot-pc_tot)/es_tot if es_tot else 0:.1f}%")
