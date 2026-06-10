"""
TRANSEPT gate part 4b (vol-208) — FAST leftover-pool freedom.
(Replaces the slow 15x-RC2 enumeration with a millisecond local measure.)

Solve stratum 0 (rows 0-1) to optimum once. Then measure placement freedom:
for each placed piece, how many UNUSED pieces could substitute at that cell+some
rotation while keeping ALL of that cell's currently-matched edges still matched?
A high swap-count => the optimal fill is far from unique => a non-greedy filler
could choose a fill leaving a DIFFERENT (better-for-bottom) leftover pool.

Also: pairwise-swap freedom within the stratum (swap two placed pieces) is the
other freedom axis; we report single-substitution which lower-bounds it.
"""
import sys, os, time, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v206_mosaic'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W
from window_maxsat import solve_window

SIZE, PIECES, HINTS = load_puzzle()
NP=len(PIECES)

def matched_sides_at(board, c):
    """set of sides of cell c that are currently matched to a placed neighbor."""
    out=set()
    if c not in board: return out
    pid,r=board[c]; ed=rot_edges(PIECES[pid],r)
    x=c%SIZE;y=c//SIZE
    nb={N:(c-SIZE if y>0 else None, S), E:(c+1 if x<SIZE-1 else None, W),
        S:(c+SIZE if y<SIZE-1 else None, N), W:(c-1 if x>0 else None, E)}
    for side,(nc,oside) in nb.items():
        if nc is None or nc not in board: continue
        npid,nr=board[nc]; ned=rot_edges(PIECES[npid],nr)
        if ed[side]==ned[oside]: out.add(side)
    return out

def board_border_sides(c):
    x=c%SIZE;y=c//SIZE;s=set()
    if y==0:s.add(N)
    if y==SIZE-1:s.add(S)
    if x==0:s.add(W)
    if x==SIZE-1:s.add(E)
    return s

def run():
    pool=set(range(NP))
    cells=[ (0+dy)*SIZE + x for dy in range(2) for x in range(SIZE)]
    print("solving stratum 0 (rows 0-1) to optimum...", flush=True)
    t0=time.time()
    res=solve_window(SIZE, PIECES, cells, pool, {}, {})
    assign,matched,secs,nint,nb=res
    print(f"  matched_internal={matched}/{nint}, {secs:.1f}s", flush=True)
    board=dict(assign)
    used=set(p for p,_ in board.values())
    unused=pool-used
    print(f"  used {len(used)} pieces, unused pool {len(unused)}", flush=True)
    # single-substitution freedom
    swap_counts=[]
    for c in cells:
        ms=matched_sides_at(board,c)
        bb=board_border_sides(c)
        nsub=0
        for q in unused:
            for r in range(4):
                ed=rot_edges(PIECES[q],r)
                # must respect board border
                if {i for i in range(4) if ed[i]==BORDER}!=bb: continue
                # must keep every currently-matched side still matched
                ok=True
                pid,pr=board[c]; ped=rot_edges(PIECES[pid],pr)
                for side in ms:
                    # neighbor color on that side stays same; q must present same color
                    if ed[side]!=ped[side]: ok=False;break
                if ok: nsub+=1; break  # count distinct unused pieces that fit
        swap_counts.append(nsub)
    import statistics
    print(f"  single-substitution freedom per cell (unused pieces that fit keeping "
          f"matches): min {min(swap_counts)}, median {statistics.median(swap_counts)}, "
          f"max {max(swap_counts)}, total swappable cells {sum(1 for x in swap_counts if x>0)}/{len(cells)}")
    print(f"  sum substitution options = {sum(swap_counts)}")
    if sum(swap_counts)>50:
        print("  => SUBSTANTIAL leftover-pool freedom: many unused pieces can replace "
              "placed ones keeping stratum-0 optimal. A non-greedy filler CAN steer "
              "the leftover pool. (Necessary condition for residual-lookahead met.)")
    else:
        print("  => LOW freedom: optimal fill is nearly rigid; residual-lookahead has "
              "little room.")

if __name__=="__main__":
    run()
