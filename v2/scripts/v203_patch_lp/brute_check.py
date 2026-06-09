import sys, time, itertools
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W
# Exhaustive DFS, NO bound pruning, find true max for tiny puzzle.
def solve_nobound(size,pieces,time_limit=120):
    ncell=size*size
    def must_border(c):
        x=c%size;y=c//size;s=set()
        if y==0:s.add(N)
        if y==size-1:s.add(S)
        if x==0:s.add(W)
        if x==size-1:s.add(E)
        return s
    cell_pr=[]
    for c in range(ncell):
        mb=must_border(c);lst=[]
        for p,base in enumerate(pieces):
            for r in range(4):
                ed=rot_edges(base,r)
                bs={i for i in range(4) if ed[i]==BORDER}
                if bs==mb:lst.append((p,r,ed))
        cell_pr.append(lst)
    total=2*size*(size-1)
    best=[-1];used=[False]*len(pieces);place=[None]*ncell
    t0=time.time();to=[False]
    sys.setrecursionlimit(100000)
    def dfs(c,matched):
        if to[0]:return
        if time.time()-t0>time_limit:to[0]=True;return
        if best[0]==total:return  # found perfect, stop
        if c==ncell:
            if matched>best[0]:best[0]=matched
            return
        x=c%size;y=c//size
        for (p,r,ed) in cell_pr[c]:
            if used[p]:continue
            add=0
            if x>0:
                ln=place[c-1]
                if ln is not None and ln[2][E]==ed[W]:add+=1
            if y>0:
                un=place[c-size]
                if un is not None and un[2][S]==ed[N]:add+=1
            used[p]=True;place[c]=(p,r,ed)
            dfs(c+1,matched+add)
            used[p]=False;place[c]=None
    dfs(0,0)
    return best[0],total,to[0]
size,pieces,hints=load_puzzle(sys.argv[1])
print(f"per-cell placement counts: corner~{len([1 for p,b in enumerate(pieces) for r in range(4)])}")
b,t,to=solve_nobound(size,pieces,float(sys.argv[2]) if len(sys.argv)>2 else 60)
print(f"{sys.argv[1]}: NO-BOUND DFS max={b}/{t} {'TIMEOUT' if to else 'EXACT'}")
