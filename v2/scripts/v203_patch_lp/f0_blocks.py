"""F0: enumerate internally-matched 2x2 blocks per super-cell position
(border-aware) and count, for the aligned 8x8 super-grid (offset 0,0).

A block at super-cell (Sr,Sc) covers cells:
  TL=(2Sr,2Sc) TR=(2Sr,2Sc+1) BL=(2Sr+1,2Sc) BR=(2Sr+1,2Sc+1)
Outer sides facing the board border must be BORDER color.

Internal match constraints (edges [N,E,S,W], rot new[i]=base[(i-r)%4]):
  TL.E == TR.W ; BL.E == BR.W ; TL.S == BL.N ; TR.S == BR.N
Block identity for packing: the SET of 4 piece-ids (rotations are part of
the placement but uniqueness is per piece-id).
"""
import sys, time, itertools
from collections import defaultdict
sys.path.insert(0, '.')
from e2lib import load_puzzle, rot_edges, BORDER, N,E,S,W

SIZE = 16
SUP = SIZE // 2  # 8

def all_oriented(pieces):
    """For each piece id, the 4 (rotation, edges) orientations.
    Returns list indexed by pid of list[(r, (N,E,S,W))]."""
    out = []
    for pid, base in enumerate(pieces):
        outs = [(r, rot_edges(base, r)) for r in range(4)]
        out.append(outs)
    return out

def border_req(Sr, Sc):
    """Which outer sides of the 2x2 block must be BORDER.
    Returns dict cell-> set of sides that must == BORDER.
    cells: 'TL','TR','BL','BR'. sides on outer boundary."""
    req = {'TL':set(),'TR':set(),'BL':set(),'BR':set()}
    if Sr == 0:        # top row of super-grid -> TL.N, TR.N border
        req['TL'].add(N); req['TR'].add(N)
    if Sr == SUP-1:    # bottom -> BL.S, BR.S
        req['BL'].add(S); req['BR'].add(S)
    if Sc == 0:        # left -> TL.W, BL.W
        req['TL'].add(W); req['BL'].add(W)
    if Sc == SUP-1:    # right -> TR.E, BR.E
        req['TR'].add(E); req['BR'].add(E)
    return req

def oriented_ok(edges, sides_border):
    """Piece orientation ok if all required sides are BORDER and no OTHER
    side is BORDER spuriously? For interior pieces no side is BORDER; for
    edge/corner pieces the BORDER sides must EXACTLY land on required sides.
    A valid placement: every BORDER side of the piece must be on the board
    boundary, and every required-boundary side must be BORDER."""
    is_border_side = [edges[i] == BORDER for i in range(4)]
    nb = sum(is_border_side)
    # required sides must be border
    for sdir in sides_border:
        if not is_border_side[sdir]:
            return False
    # any border side not in required set => piece sticks border into interior => invalid
    for i in range(4):
        if is_border_side[i] and i not in sides_border:
            return False
    return True

def enumerate_supercell(oriented, Sr, Sc):
    req = border_req(Sr, Sc)
    # candidate orientations per cell respecting border
    cand = {}
    for cell, sides in req.items():
        lst = []
        for pid in range(len(oriented)):
            for (r, ed) in oriented[pid]:
                if oriented_ok(ed, sides):
                    lst.append((pid, r, ed))
        cand[cell] = lst
    # Build buckets for fast joins.
    # TR by W color ; BL by N color ; BR by (W,N)
    tr_by_w = defaultdict(list)
    for t in cand['TR']: tr_by_w[t[2][W]].append(t)
    bl_by_n = defaultdict(list)
    for t in cand['BL']: bl_by_n[t[2][N]].append(t)
    br_by_wn = defaultdict(list)
    for t in cand['BR']: br_by_wn[(t[2][W], t[2][N])].append(t)
    blocks = []
    for (pid_tl, r_tl, ed_tl) in cand['TL']:
        need_tr_w = ed_tl[E]
        need_bl_n = ed_tl[S]
        for (pid_tr, r_tr, ed_tr) in tr_by_w.get(need_tr_w, ()):
            if pid_tr == pid_tl: continue
            need_br_n = ed_tr[S]
            for (pid_bl, r_bl, ed_bl) in bl_by_n.get(need_bl_n, ()):
                if pid_bl in (pid_tl, pid_tr): continue
                need_br_w = ed_bl[E]
                for (pid_br, r_br, ed_br) in br_by_wn.get((need_br_w, need_br_n), ()):
                    if pid_br in (pid_tl, pid_tr, pid_bl): continue
                    blocks.append((pid_tl, pid_tr, pid_bl, pid_br,
                                   r_tl, r_tr, r_bl, r_br))
    return blocks

def main():
    t0 = time.time()
    size, pieces, hints = load_puzzle()
    oriented = all_oriented(pieces)
    total = 0
    per_cell = {}
    sizes = []
    for Sr in range(SUP):
        row = []
        for Sc in range(SUP):
            blocks = enumerate_supercell(oriented, Sr, Sc)
            per_cell[(Sr,Sc)] = len(blocks)
            sizes.append(len(blocks))
            total += len(blocks)
            row.append(len(blocks))
        print("Sr=%d " % Sr + " ".join("%8d"%v for v in row))
    print(f"\nTotal blocks (offset 0,0): {total:,}")
    print(f"min={min(sizes)} max={max(sizes):,} mean={total/64:,.0f}")
    print(f"corner cells: (0,0)={per_cell[(0,0)]}, (0,7)={per_cell[(0,7)]}, (7,0)={per_cell[(7,0)]}, (7,7)={per_cell[(7,7)]}")
    print(f"enum time: {time.time()-t0:.1f}s")

if __name__ == "__main__":
    main()
