"""
KEYSTONE gate (vol-208) — how fast can we EXACTLY MaxScore-complete the bottom
6 rows given a perfect top-10-row scaffold?

Rationale (from today's gates): the top 10 rows fill perfectly & freely; the
bottom 6 rows (96 cells, ~96-piece residual pool) carry ALL the difficulty. If
this subproblem solves fast (seconds), a massive structured search = "generate
diverse perfect top-10s, exact-complete each bottom" becomes practical (days of
compute -> huge coverage of NOVEL basins, frontier #1 + #4). This gates that.

We build a perfect top-10 via sequential strip-fill (rows 0-9, all perfect), then
MaxScore-complete the bottom 6 rows (rows 10-15) as ONE window with:
 - seam-above SOFT (reward matching row-9 south),
 - left/right/bottom borders hard,
 - internal edges soft,
 - the residual 96-piece pool.
Measure solve time + matched. Compare RC2 (optimal, may be slow) vs a fast
edge-strict DFS MaxScore with node budget (anytime).
"""
import sys, os, time, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v206_mosaic'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W
from gate_strip_fill import solve_stratum  # reuse perfect top builder

SIZE, PIECES, HINTS = load_puzzle()
NP=len(PIECES)

def build_perfect_top(top_rows=10, seed_skip=0):
    """Greedy sequential strip-fill rows 0..top_rows-1 (H=2). Returns board,pool."""
    pool=set(range(NP)); board={}; rows=0
    while rows<top_rows:
        h=2
        cells=[(rows+dy)*SIZE+x for dy in range(h) for x in range(SIZE)]
        seam={}
        if rows>0:
            for x in range(SIZE):
                pa,ra=board[(rows-1)*SIZE+x]
                seam[rows*SIZE+x]=rot_edges(PIECES[pa],ra)[S]
        res=solve_stratum(cells,pool,seam,seam_soft=True,card='seq')
        assign,mi,ms,secs,nint,nseam=res
        for c,(p,r) in assign.items(): board[c]=(p,r); pool.discard(p)
        rows+=h
    return board,pool

def maxscore_dfs_bottom(board, pool, top_rows, node_budget=5_000_000, time_budget=30.0):
    """Edge-strict-ish MaxScore DFS over bottom rows, row-major. Tracks best matched.
       'soft' = we DON'T require matches; we maximize them. To keep it tractable we
       do a best-first-ish greedy with branch & bound on an admissible upper bound."""
    free=[pos for pos in range(top_rows*SIZE, SIZE*SIZE)]
    nfree=len(free)
    placed=dict(board); used=set(p for p,_ in board.values())
    # candidate (pid,rot) per free cell respecting board border only (soft interior)
    def bbsides(c):
        x=c%SIZE;y=c//SIZE;s=set()
        if y==0:s.add(N)
        if y==SIZE-1:s.add(S)
        if x==0:s.add(W)
        if x==SIZE-1:s.add(E)
        return s
    cand={}
    for c in free:
        bb=bbsides(c); lst=[]
        for p in pool:
            for r in range(4):
                ed=rot_edges(PIECES[p],r)
                if {i for i in range(4) if ed[i]==BORDER}!=bb: continue
                lst.append((p,r,ed))
        cand[c]=lst
    # total bottom edges (internal among free + seam to row above)
    best=[-1]; best_board=[None]; nodes=[0]; t0=time.time(); stop=[False]
    # precompute, per free cell, its already-or-will-be neighbors for incremental scoring
    def gain(c, ed):
        g=0
        x=c%SIZE;y=c//SIZE
        # north neighbor (above, already placed if row above done)
        if y>0:
            up=placed.get(c-SIZE)
            if up and rot_edges(PIECES[up[0]],up[1])[S]==ed[N]: g+=1
        if x>0:
            lf=placed.get(c-1)
            if lf and rot_edges(PIECES[lf[0]],lf[1])[E]==ed[W]: g+=1
        return g
    # remaining-edges admissible bound: edges not yet decided
    def dfs(i, score):
        if stop[0]: return
        nodes[0]+=1
        if nodes[0]>node_budget or time.time()-t0>time_budget: stop[0]=True; return
        if i==nfree:
            if score>best[0]:
                best[0]=score; best_board[0]=dict(placed)
            return
        pos=free[i]
        # admissible UB: current score + (edges still placeable below/right) — loose:
        # remaining free cells each can add <=2 (N,W) gains
        ub=score + 2*(nfree-i)
        if ub<=best[0]: return
        # order candidates by immediate gain desc (greedy-best-first)
        opts=[]
        for (p,r,ed) in cand[pos]:
            if p in used: continue
            opts.append((gain(pos,ed),p,r,ed))
        opts.sort(reverse=True, key=lambda t:t[0])
        for (g,p,r,ed) in opts:
            placed[pos]=(p,r); used.add(p)
            dfs(i+1, score+g)
            del placed[pos]; used.discard(p)
            if stop[0]: return
    dfs(0,0)
    return best[0], best_board[0], nodes[0], time.time()-t0, stop[0]

def run():
    print("building perfect top-10 scaffold (rows 0-9)...", flush=True)
    t0=time.time()
    board,pool=build_perfect_top(10)
    print(f"  top-10 built, pool={len(pool)}, {time.time()-t0:.1f}s", flush=True)
    print("MaxScore DFS completing bottom 6 rows (rows 10-15, 96 cells)...", flush=True)
    best,bb,nodes,secs,timed=maxscore_dfs_bottom(board,pool,10,
                                                  node_budget=20_000_000, time_budget=60.0)
    # total bottom edges for reference: seam(16) + internal of 6x16 = 16 + (15*6+16*5)=16+170=186
    print(f"  best bottom matched (seam+internal) = {best} / 186  "
          f"(nodes {nodes}, {secs:.1f}s, {'TIMEOUT' if timed else 'COMPLETE'})", flush=True)
    # full board score if we take this completion
    if bb is not None:
        full=0
        for y in range(SIZE):
            for x in range(SIZE):
                pos=y*SIZE+x
                if x+1<SIZE and pos in bb and pos+1 in bb:
                    if rot_edges(PIECES[bb[pos][0]],bb[pos][1])[E]==rot_edges(PIECES[bb[pos+1][0]],bb[pos+1][1])[W]: full+=1
                if y+1<SIZE and pos in bb and pos+SIZE in bb:
                    if rot_edges(PIECES[bb[pos][0]],bb[pos][1])[S]==rot_edges(PIECES[bb[pos+SIZE][0]],bb[pos+SIZE][1])[N]: full+=1
        print(f"  => FULL BOARD matched = {full}/480 (top-10 perfect=270 + bottom {best})")

if __name__=="__main__":
    run()
