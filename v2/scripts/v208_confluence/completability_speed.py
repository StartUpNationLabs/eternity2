"""
"How many placed pieces let us DECIDE completability in milliseconds?" (vol-208,
user question 2026-06-10).

We separate three notions and MEASURE each on the real canonical puzzle:

(A) PERFECT-completability decision: given the top T rows pinned (16*T pieces),
    can the remaining (16-T)*16 cells be filled so EVERY remaining edge matches
    (=> a 480 board)? This is the strict question. We decide it by exact DFS over
    the free region (edge-strict: only place a piece if it matches all already-
    placed neighbors), returning SAT/UNSAT, and TIME it. We sweep T to find the
    smallest placed count whose decision is < a few ms.
    Boundary: we pin McGavin's top T rows. McGavin is a 469 board, so its top
    rows do NOT perfectly complete (11 defects) -> the decision is UNSAT and the
    DFS must exhaust the free region to prove it. Exhaustion time vs free size is
    exactly "how fast can we decide".

(B) NECESSARY-condition checks (always O(cells), microseconds): edge-strict
    frontier consistency + per-color residual budget (Hall-lite). These can only
    say "definitely NOT completable" or "maybe". We measure how often they alone
    decide (i.e. fire UNSAT) as a function of T.

(C) For calibration: a GENERATED perfectly-solvable 16x16 puzzle, pin top T rows
    of its TRUE solution, and time the perfect-completion DFS (this has SAT
    answers -> measures positive-decision speed).

Report: the free-region size (and placed-piece count) at which (A) decides in
~1ms, ~10ms, ~100ms, and where it explodes.
"""
import sys, os, time, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W, load_board

SIZE, PIECES, HINTS = load_puzzle()
NP=len(PIECES)

# Precompute, for fast edge-strict DFS: index pieces by the (rot) that yields a
# given (N, W) when north & west neighbors are fixed. We'll do a simple but fast
# DFS that, at each free cell in row-major order, knows required N (south of cell
# above) and required W (east of cell to the left), and tries matching pieces.
# Build map (Ncolor, Wcolor) -> list of (pid, rot). Border handled per-cell.
nw_index=collections.defaultdict(list)
for pid in range(NP):
    for r in range(4):
        ed=rot_edges(PIECES[pid],r)
        nw_index[(ed[N],ed[W])].append((pid,r,ed))

def decide_perfect_completion(pinned, free_cells, time_budget_s=2.0):
    """pinned: dict pos->(pid,rot) for placed cells. free_cells: row-major list of
       empty cells to fill. Edge-strict perfect completion: every internal edge
       among free+pinned must match. Returns (sat, nodes, secs)."""
    placed=dict(pinned)
    used=set(p for p,_ in pinned.values())
    t0=time.time(); nodes=[0]; timeout=[False]
    free=free_cells
    nfree=len(free)
    def need_NW(pos):
        x=pos%SIZE;y=pos//SIZE
        reqN=reqW=None
        if y>0:
            up=placed.get(pos-SIZE)
            if up: reqN=rot_edges(PIECES[up[0]],up[1])[S]
            else: reqN='?'  # above is free & unfilled (shouldn't happen in row-major)
        else: reqN=BORDER
        if x>0:
            lf=placed.get(pos-1)
            if lf: reqW=rot_edges(PIECES[lf[0]],lf[1])[E]
            else: reqW='?'
        else: reqW=BORDER
        return reqN,reqW,x,y
    def dfs(i):
        if timeout[0]: return False
        if time.time()-t0>time_budget_s: timeout[0]=True; return False
        if i==nfree: return True
        pos=free[i]
        reqN,reqW,x,y=need_NW(pos)
        # also need to respect E/S borders and (for perfect) match right/bottom if
        # those neighbors already placed (they aren't in row-major free order, but
        # pinned cells to the right/below could be). Check after placing.
        reqE = BORDER if x==SIZE-1 else None
        reqS = BORDER if y==SIZE-1 else None
        cands = nw_index.get((reqN,reqW), [])
        for (pid,rot,ed) in cands:
            if pid in used: continue
            if reqE is not None and ed[E]!=reqE: continue
            if reqS is not None and ed[S]!=reqS: continue
            # match any already-placed right/bottom pinned neighbor (perfect)
            rp=placed.get(pos+1)
            if rp and ed[E]!=rot_edges(PIECES[rp[0]],rp[1])[W]: continue
            bp=placed.get(pos+SIZE)
            if bp and ed[S]!=rot_edges(PIECES[bp[0]],bp[1])[N]: continue
            nodes[0]+=1
            placed[pos]=(pid,rot); used.add(pid)
            if dfs(i+1): return True
            del placed[pos]; used.discard(pid)
        return False
    sat=dfs(0)
    return (None if timeout[0] else sat), nodes[0], time.time()-t0

def run_mcgavin():
    board,_=load_board("output/vol-65/mcgavin_469.json")
    print("=== (A) PERFECT-completion decision, pinning McGavin top T rows ===")
    print("(McGavin is 469 => UNSAT; time = exhaustion proof time)")
    print(f"{'T rows':>6} {'placed':>6} {'free cells':>10} {'decision':>9} {'nodes':>12} {'secs':>9}")
    for T in range(15, 7, -1):  # 15 down to 8: free region grows
        pinned={pos:board[pos] for pos in range(T*SIZE)}
        free=[pos for pos in range(T*SIZE, SIZE*SIZE)]
        sat,nodes,secs=decide_perfect_completion(pinned, free, time_budget_s=3.0)
        dec = 'TIMEOUT' if sat is None else ('SAT' if sat else 'UNSAT')
        print(f"{T:>6} {T*SIZE:>6} {len(free):>10} {dec:>9} {nodes:>12} {secs:>9.4f}", flush=True)
        if sat is None:
            print(f"   -> exploded at T={T} ({len(free)} free cells); stop deepening")
            break

if __name__=="__main__":
    run_mcgavin()
