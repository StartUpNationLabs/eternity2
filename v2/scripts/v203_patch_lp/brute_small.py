"""Brute-force / DFS exact max-matched for small puzzles. Row-major DFS
with branch-and-bound on matched edges. Returns true optimum."""
import sys, time
sys.path.insert(0,'.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W

def solve(size, pieces, time_limit=60):
    ncell=size*size
    # precompute oriented placements valid per cell (border)
    def must_border(c):
        x=c%size;y=c//size;s=set()
        if y==0:s.add(N)
        if y==size-1:s.add(S)
        if x==0:s.add(W)
        if x==size-1:s.add(E)
        return s
    cell_pr=[]
    for c in range(ncell):
        mb=must_border(c); lst=[]
        for p,base in enumerate(pieces):
            for r in range(4):
                ed=rot_edges(base,r)
                bs={i for i in range(4) if ed[i]==BORDER}
                if bs==mb: lst.append((p,r,ed))
        cell_pr.append(lst)
    total=2*size*(size-1)
    best=[-1]
    used=[False]*len(pieces)
    place=[None]*ncell
    t0=time.time()
    timed_out=[False]
    # max additional matches possible from cell c onward (upper bound):
    # each remaining cell can add at most: right edge + down edge that are
    # "new" — bound loosely by remaining interior edges.
    def remaining_edges(c):
        # edges not yet decided: those with both endpoints >= ... approx
        cnt=0
        # An interior edge (a,b) with a<b is still UNDECIDED at the moment
        # we are about to place cell c iff its larger endpoint b >= c.
        # (b<c => both endpoints already placed => edge decided.)
        for a in range(ncell):
            x=a%size;y=a//size
            if x+1<size:           # horizontal edge a -- a+1
                b=a+1
                if b>=c: cnt+=1
            if y+1<size:           # vertical edge a -- a+size
                b=a+size
                if b>=c: cnt+=1
        return cnt
    import sys as _s
    _s.setrecursionlimit(10000)
    def dfs(c, matched):
        if timed_out[0]: return
        if time.time()-t0>time_limit:
            timed_out[0]=True; return
        if c==ncell:
            if matched>best[0]: best[0]=matched
            return
        # bound: matched + remaining_edges(c) <= best -> prune
        if matched+remaining_edges(c)<=best[0]:
            return
        x=c%size;y=c//size
        for (p,r,ed) in cell_pr[c]:
            if used[p]: continue
            add=0; ok=True
            # left neighbor
            if x>0:
                ln=place[c-1]
                if ln is not None:
                    if ln[2][E]==ed[W]: add+=1
            # up neighbor
            if y>0:
                un=place[c-size]
                if un is not None:
                    if un[2][S]==ed[N]: add+=1
            used[p]=True; place[c]=(p,r,ed)
            dfs(c+1, matched+add)
            used[p]=False; place[c]=None
    dfs(0,0)
    return best[0], total, timed_out[0], time.time()-t0

if __name__=="__main__":
    path=sys.argv[1]; tl=float(sys.argv[2]) if len(sys.argv)>2 else 60
    size,pieces,hints=load_puzzle(path)
    opt,total,to,dt=solve(size,pieces,tl)
    print(f"{path}: size={size} npieces={len(pieces)} TRUE_MAX={opt}/{total} "
          f"{'(TIMEOUT-lower-bound)' if to else '(exact)'} {dt:.1f}s")
