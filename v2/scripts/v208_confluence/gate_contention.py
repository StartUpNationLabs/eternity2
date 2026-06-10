"""
TRANSEPT gate part 2 (vol-208): piece->stratum contention.

Two questions:
(Q1) Does a GOOD stratification exist? Use McGavin 469 (an actual near-optimal
     board). Partition into strata of height H. Each stratum uses a fixed set of
     pieces (McGavin's). Measure each stratum's internal+seam matched (it's the
     realized board, so it's whatever McGavin achieved). Report per-stratum
     defect localization -> confirms the bottom-vs-top asymmetry or not.

(Q2) How CONTENDED is the assignment, independently of McGavin? For each stratum
     region (a height-H band at every vertical offset), compute the set of pieces
     that COULD give a perfect/near-perfect internal fill (too expensive to solve
     exactly per band) — instead approximate contention by: for each interior
     (N,W)-scarce demand, which strata could host it (its server piece is generic).
     Simpler robust proxy: measure, over the 256 pieces, how 'localized' each piece
     is to a band in the high-board corpus (does piece P appear in the same few
     rows across high boards? => low contention, assignment is easy; spread across
     all rows => high contention, assignment is the bottleneck).

We focus Q1 (exact, decisive) + a corpus row-localization measure for Q2.
"""
import sys, os, collections, glob, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W, load_board, score_board

SIZE, PIECES, HINTS = load_puzzle()
NP=len(PIECES)

def stratum_quality(board, H):
    """board: pos->(pid,rot). Return per-stratum (internal_matched, internal_total,
       seam_matched, seam_total) for height-H strata top to bottom."""
    out=[]
    rows=0
    while rows<SIZE:
        h=min(H,SIZE-rows)
        cells=[(rows+dy)*SIZE+x for dy in range(h) for x in range(SIZE)]
        cellset=set(cells)
        mi=ti=0
        for c in cells:
            x=c%SIZE;y=c//SIZE
            if x+1<SIZE and (c+1) in cellset:
                ti+=1
                if c in board and c+1 in board:
                    if rot_edges(PIECES[board[c][0]],board[c][1])[E]==rot_edges(PIECES[board[c+1][0]],board[c+1][1])[W]: mi+=1
            if y+1<SIZE and (c+SIZE) in cellset:
                ti+=1
                if c in board and c+SIZE in board:
                    if rot_edges(PIECES[board[c][0]],board[c][1])[S]==rot_edges(PIECES[board[c+SIZE][0]],board[c+SIZE][1])[N]: mi+=1
        # seam to stratum above
        sm=st=0
        if rows>0:
            for x in range(SIZE):
                st+=1
                up=(rows-1)*SIZE+x; cur=rows*SIZE+x
                if up in board and cur in board:
                    if rot_edges(PIECES[board[up][0]],board[up][1])[S]==rot_edges(PIECES[board[cur][0]],board[cur][1])[N]: sm+=1
        out.append((rows, mi, ti, sm, st))
        rows+=h
    return out

def q1():
    board,d=load_board("output/vol-65/mcgavin_469.json")
    m,t=score_board(SIZE,PIECES,board)
    print(f"McGavin {m}/{t}")
    for H in [1,2,4]:
        print(f"\n-- McGavin stratum quality H={H} (internal + seam) --")
        q=stratum_quality(board,H)
        for (rows,mi,ti,sm,st) in q:
            seam=f" seam {sm}/{st}" if st else ""
            print(f"  rows {rows:2d}..{rows+H-1:2d}: internal {mi}/{ti}{seam}")

def q2_row_localization():
    """For each piece, the distribution of ROW it occupies across high boards.
       Low spread => piece 'belongs' to a band => assignment easy.
       High spread => piece floats => contention high."""
    files=glob.glob("database-400-480/*.json")
    rows_of=collections.defaultdict(list)  # pid -> list of row indices across boards
    nb=0
    for f in files:
        sc=re.match(r'(\d+)_',os.path.basename(f))
        if not sc or int(sc.group(1))<458: continue
        try:
            board,d=load_board(f)
            m,t=score_board(SIZE,PIECES,board)
            if abs(m-int(sc.group(1)))>2: continue
            for pos,(pid,r) in board.items():
                rows_of[pid].append(pos//SIZE)
            nb+=1
        except Exception: continue
    print(f"\n-- piece row-localization across {nb} boards >=458 --")
    spreads=[]
    for pid in range(NP):
        rs=rows_of.get(pid,[])
        if len(rs)<5: continue
        import statistics
        spreads.append(statistics.pstdev(rs))
    spreads.sort()
    if spreads:
        import statistics
        print(f"  pieces with >=5 occurrences: {len(spreads)}")
        print(f"  row-stdev across boards: min {spreads[0]:.2f}, "
              f"median {statistics.median(spreads):.2f}, max {spreads[-1]:.2f}")
        # interpret: stdev ~0 => piece pinned to a row band; stdev ~4.6 (uniform over 16) => floats
        pinned=sum(1 for s in spreads if s<2.0)
        floating=sum(1 for s in spreads if s>3.5)
        print(f"  'pinned' pieces (row-stdev<2.0): {pinned}; 'floating' (>3.5): {floating}")
        print(f"  (uniform-over-16 stdev ~4.61; a strongly banded piece <1.5)")

if __name__=="__main__":
    q1()
    q2_row_localization()
