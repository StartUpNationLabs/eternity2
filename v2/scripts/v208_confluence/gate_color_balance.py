"""
TRANSEPT gate part 3 (vol-208) — is per-stratum color-supply balance a BINDING,
SELECTIVE constraint over piece->stratum partitions? (the make-or-break for the
assignment pre-pass).

If a stratum is fillable to near-perfect ONLY when its assigned pool has balanced
edge-color supply, and McGavin's actual partition is markedly more balanced than a
random partition, then the assignment objective is real & selective => TRANSEPT
has a meaningful global step. If random partitions balance just as well (like the
PARQUET 2x2-LP that capped at 480 for everyone), the assignment is unconstrained
and TRANSEPT collapses to refuted J1.

Color-balance metric for a stratum pool P (a set of pieces) and the stratum's
geometry (H rows x 16, with top+bottom seams):
  The stratum has, per color c, a SUPPLY = total count of color c across all
  piece-sides in P. To tile the stratum's internal vertical edges (16*(H-1)) and
  present matchable colors to its seams, it needs each *used* adjacency color to
  appear an EVEN number of times among internal-facing sides (each internal edge
  consumes 2 same-color half-edges). A simple proxy for 'fillability stress':
  sum over colors of (supply_c mod 2) on the interior-facing sides — but exact
  interior-facing assignment is the solve itself. Instead we use a robust,
  assignment-free proxy validated against McGavin:

  PROXY = per-stratum 'self-matchability' = max matching achievable on the pool's
  color multiset for the stratum's internal edge count, computed as:
     for each color c, it can cover floor(count_c / 2) internal edges;
     usable_internal = min(needed_internal, sum_c floor(count_c/2)).
  This is the vol-65 PSM-style per-color matching cap, restricted to a stratum's
  pool. McGavin's per-stratum pools should hit ~needed; random pools should fall
  short if the constraint is selective.
"""
import sys, os, collections, random, statistics
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W, load_board, score_board

SIZE, PIECES, HINTS = load_puzzle()
NP=len(PIECES)

def piece_colors(pid):
    """multiset of the 4 edge colors (ignoring border)."""
    return [c for c in PIECES[pid] if c!=BORDER]

def stratum_internal_edges(H):
    # within a height-H x 16 stratum: horizontal (15*H) + vertical (16*(H-1))
    return 15*H + 16*(H-1)

def matching_cap(pool):
    """vol-65-style per-color matching cap over a pool's color multiset (all 4
    sides counted). max internal edges this pool could match = sum_c floor(cnt/2)."""
    cnt=collections.Counter()
    for p in pool:
        for c in piece_colors(p): cnt[c]+=1
    return sum(v//2 for v in cnt.values()), cnt

def mcgavin_partition(H):
    board,_=load_board("output/vol-65/mcgavin_469.json")
    strata=[]
    rows=0
    while rows<SIZE:
        h=min(H,SIZE-rows)
        pool=set()
        for dy in range(h):
            for x in range(SIZE):
                pos=(rows+dy)*SIZE+x
                pool.add(board[pos][0])
        strata.append(pool); rows+=h
    return strata

def analyze(H, ntrials=200):
    needed=stratum_internal_edges(H)
    print(f"\n=== H={H}: internal edges/stratum needed={needed} ===")
    mg=mcgavin_partition(H)
    mg_caps=[]
    for i,pool in enumerate(mg):
        cap,_=matching_cap(pool)
        mg_caps.append(cap)
    print(f"McGavin per-stratum matching-cap: {mg_caps}")
    print(f"  (cap>=needed means pool CAN cover all internal edges by color count)")
    print(f"  McGavin min cap {min(mg_caps)}, all>=needed: {all(c>=needed for c in mg_caps)}")
    # random partitions: shuffle pieces into strata of the SAME sizes as McGavin
    sizes=[len(p) for p in mg]
    allp=list(range(NP))
    rng=random.Random(12345)
    rand_mincaps=[]; rand_below=[]
    for t in range(ntrials):
        rng.shuffle(allp)
        idx=0; caps=[]
        for s in sizes:
            pool=set(allp[idx:idx+s]); idx+=s
            cap,_=matching_cap(pool); caps.append(cap)
        rand_mincaps.append(min(caps))
        rand_below.append(sum(1 for c in caps if c<needed))
    print(f"  random partitions (same sizes, {ntrials} trials):")
    print(f"    min-cap across strata: mean {statistics.mean(rand_mincaps):.1f}, "
          f"min {min(rand_mincaps)}, max {max(rand_mincaps)}")
    print(f"    # strata below needed: mean {statistics.mean(rand_below):.2f}, "
          f"max {max(rand_below)}")
    frac_allok=sum(1 for b in rand_below if b==0)/ntrials
    print(f"    fraction of random partitions with ALL strata cap>=needed: {frac_allok:.2%}")

for H in [2,4]:
    analyze(H)
