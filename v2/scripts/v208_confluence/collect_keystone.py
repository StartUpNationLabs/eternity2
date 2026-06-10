"""
KEYSTONE collector (vol-208). Rescore + verify every ALNS output, compute
corner-perm + Hamming-novelty vs known high basins, report best per cp, flag any
new-cp >=460 (the record target, open challenge #1).

Usage: uv run python scripts/v208_confluence/collect_keystone.py [alns_dir]
Default alns_dir = output/v17_alns_only
"""
import sys, os, glob, json, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W, load_board, score_board

SIZE, PIECES, HINTS = load_puzzle()
NP=len(PIECES)
ALNS_DIR = sys.argv[1] if len(sys.argv)>1 else "output/v17_alns_only"

# known high basins for novelty
KNOWN={
 'mcgavin469':'output/vol-65/mcgavin_469.json',
 'v129_463':'output/vol-129/RECORD_463_corner2301_seed42.json',
}
known_boards={}
for k,p in KNOWN.items():
    if os.path.exists(p):
        b,_=load_board(p); known_boards[k]=b

def corner_perm(board):
    """Canonical corner-perm: the 4 corner piece-ids at positions (0,0),(0,15),
    (15,0),(15,15), returned as a tuple of their RANKS among the 4 (0..3) so it's
    a permutation label independent of absolute ids."""
    corners=[0, SIZE-1, (SIZE-1)*SIZE, SIZE*SIZE-1]
    pids=[]
    for c in corners:
        if c in board: pids.append(board[c][0])
        else: pids.append(-1)
    order=sorted(range(4), key=lambda i: pids[i])
    rank=[0]*4
    for r,i in enumerate(order): rank[i]=r
    return tuple(rank)

def hamming(b1, b2):
    d=0
    for pos in range(SIZE*SIZE):
        p1=b1.get(pos); p2=b2.get(pos)
        if (p1[0] if p1 else None)!=(p2[0] if p2 else None): d+=1
    return d

def verify_unique(board):
    pids=[board[p][0] for p in board]
    return len(set(pids))==len(pids)==256

def run():
    files=glob.glob(os.path.join(ALNS_DIR,"*.json"))
    results=[]
    for f in files:
        try:
            board,d=load_board(f)
            m,t=score_board(SIZE,PIECES,board)
            if not verify_unique(board): continue
            cp=corner_perm(board)
            nov=min((hamming(board,kb) for kb in known_boards.values()), default=-1)
            results.append((m,cp,nov,f))
        except Exception:
            continue
    if not results:
        print("no valid boards yet in", ALNS_DIR); return
    results.sort(reverse=True)
    print(f"=== {len(results)} valid ALNS boards in {ALNS_DIR} ===")
    print(f"top score: {results[0][0]}; distribution:")
    dist=collections.Counter(r[0] for r in results)
    for sc in sorted(dist, reverse=True)[:12]:
        print(f"   {sc}: {dist[sc]}")
    # best per corner-perm
    best_by_cp={}
    for m,cp,nov,f in results:
        if cp not in best_by_cp or m>best_by_cp[cp][0]:
            best_by_cp[cp]=(m,nov,f)
    print(f"\n=== best per corner-perm ({len(best_by_cp)} distinct cps) ===")
    for cp in sorted(best_by_cp, key=lambda c:-best_by_cp[c][0]):
        m,nov,f=best_by_cp[cp]
        flag=" ★≥460" if m>=460 else ""
        print(f"   cp={cp}: {m}/480  (min-Hamming-to-known {nov}){flag}")
    # flag record candidates
    rec=[r for r in results if r[0]>=460]
    if rec:
        print(f"\n★★★ {len(rec)} boards ≥460 — VERIFY with verify_board + check cp novelty:")
        for m,cp,nov,f in rec[:20]:
            print(f"   {m}/480 cp={cp} nov={nov}  {f}")
    else:
        print(f"\n(no ≥460 yet; best {results[0][0]})")

if __name__=="__main__":
    run()
