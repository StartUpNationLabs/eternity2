"""Independent E2 loader + scorer + 2x2 patch feasibility. v203.
Edges convention: [N, E, S, W]. Rotation r rotates clockwise:
rotated(r)[i] = base[(i - r) mod 4]  (verified vs core/piece.rs:
 base (N,E,S,W)=(1,2,3,4); R90 -> (4,1,2,3) which is base shifted so
 new N = old W. i.e. new[i]=old[(i-1) mod4] for r=1.)
"""
import json, os, itertools
from functools import lru_cache

_HERE = os.path.dirname(os.path.abspath(__file__))
# script dir is v2/scripts/v203_patch_lp ; puzzle is eternity2/data/puzzles
_DEF_PUZZLE = os.path.abspath(os.path.join(
    _HERE, "..", "..", "..", "data", "puzzles", "size_16_official_eternity.csv"))
PUZZLE_CSV = os.environ.get("E2_PUZZLE", _DEF_PUZZLE)
BORDER = 65535
N, E, S, W = 0, 1, 2, 3

def load_puzzle(path=PUZZLE_CSV):
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]
    size = int(lines[0])
    pieces = []   # pieces[id] = (N,E,S,W) base colors
    hints = {}    # pos -> (piece_id, rotation)
    for idx, line in enumerate(lines[1:1+size*size]):
        cols = line.split(',')
        top   = int(cols[0], 2)
        right = int(cols[1], 2)
        bottom= int(cols[2], 2)
        left  = int(cols[3], 2)
        pieces.append((top, right, bottom, left))
        if len(cols) >= 7:
            x = int(cols[4]); y = int(cols[5]); rot = int(cols[6])
            if x != 0 or y != 0 or rot != 0:
                pos = y*size + x
                hints[pos] = (idx, rot)
    return size, pieces, hints

def rot_edges(base, r):
    # new[i] = base[(i - r) mod 4]
    return tuple(base[(i - r) % 4] for i in range(4))

def load_board(path):
    """Return dict pos->(piece_id, rotation). Accepts placement list."""
    d = json.load(open(path))
    pl = d['placement'] if isinstance(d, dict) else d
    board = {}
    if isinstance(pl, list) and pl and isinstance(pl[0], dict):
        for e in pl:
            board[e['pos']] = (e['piece_id'], e['rotation'])
    elif isinstance(pl, list):
        for pos, e in enumerate(pl):
            if e is None: continue
            board[pos] = (e[0], e[1])
    return board, d

def score_board(size, pieces, board):
    """Count matched interior edges. Unplaced cell -> its edges unmatched."""
    matched = 0
    total = 2*size*(size-1)
    def col_at(pos, side):
        if pos not in board: return None
        pid, r = board[pos]
        return rot_edges(pieces[pid], r)[side]
    for y in range(size):
        for x in range(size):
            pos = y*size + x
            # horizontal edge to the right neighbor
            if x+1 < size:
                a = col_at(pos, E); b = col_at(pos+1, W)
                if a is not None and b is not None and a == b:
                    matched += 1
            # vertical edge to the bottom neighbor
            if y+1 < size:
                a = col_at(pos, S); b = col_at(pos+size, N)
                if a is not None and b is not None and a == b:
                    matched += 1
    return matched, total

# ---- 2x2 patch feasibility on a 4-tuple of DISTINCT pieces ----
def patch_feasible(pieces, p_tl, p_tr, p_bl, p_br):
    """Does some rotation assignment make all 4 internal edges match?
    Internal edges: TL.E==TR.W, BL.E==BR.W, TL.S==BL.N, TR.S==BR.N."""
    rots = range(4)
    base = pieces
    for rtl in rots:
        etl = rot_edges(base[p_tl], rtl)
        for rtr in rots:
            etr = rot_edges(base[p_tr], rtr)
            if etl[E] != etr[W]: continue
            for rbl in rots:
                ebl = rot_edges(base[p_bl], rbl)
                if etl[S] != ebl[N]: continue
                for rbr in rots:
                    ebr = rot_edges(base[p_br], rbr)
                    if ebl[E] == ebr[W] and etr[S] == ebr[N]:
                        return True
    return False

if __name__ == "__main__":
    import sys, random
    size, pieces, hints = load_puzzle()
    print(f"size={size} npieces={len(pieces)} nhints={len(hints)}")
    print("hints:", hints)
    # verify McGavin
    board, d = load_board("output/vol-65/mcgavin_469.json")
    m, t = score_board(size, pieces, board)
    print(f"McGavin: claimed={d.get('matched')} independent={m}/{t}")
    # forbidden-2x2 rate on random distinct 4-tuples
    random.seed(12345)
    feas = 0; N_TRIAL = 200000
    ids = list(range(len(pieces)))
    for _ in range(N_TRIAL):
        a,b,c,e = random.sample(ids, 4)
        if patch_feasible(pieces, a,b,c,e):
            feas += 1
    print(f"feasible 2x2 on random distinct 4-tuples: {feas}/{N_TRIAL} = {100*feas/N_TRIAL:.3f}%")
