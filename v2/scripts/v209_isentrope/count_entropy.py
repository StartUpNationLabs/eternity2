"""
ISENTROPE (vol-209) — tiling-count entropy W_Γ(n) for canonical E2's piece-alphabet,
adapting Canfora-Cedeño 2026 (arXiv:2601.18968) Wang-tiling stat-mech.

W_Γ(n) = number of valid (ALL internal edges matched) n×n blocks from E2's pieces.
S_Γ(n) = log10 W_Γ(n).  Two variants (E2 differs from Wang: rotation + finite distinct
supply):
  A) color-grammar entropy: pieces REUSABLE (infinite supply), rotation allowed.
     Counted via broken-profile DP (exact). Measures richness of the matching grammar.
  B) true-E2 entropy: pieces DISTINCT (no repeat). Exact small-n via the same DP +
     used-set (only tractable for very small n; we brute/DP-with-bitset).

Method (broken-profile / transfer DP), row-major fill of an n×n block:
  state after filling k cells = (profile, pend) where
     profile = tuple of length n: for each COLUMN, the S-color of the most-recently
       filled cell in that column (what the next cell below must match on its N).
       For columns not yet reached in the current row, profile holds the S-color from
       the row above (or a sentinel for row 0 = "no constraint", i.e. top border free).
     pend = the E-color the next cell must match on its W (from the just-placed left
       neighbor); sentinel at the start of each row (x=0 → W free, interior block).
  At each cell (x,y): sum over (piece,rot) with N==profile[x] (if constrained) and
     W==pend (if constrained); new profile[x]=S, new pend=E.
  Row ends (x=n-1): pend resets to sentinel (W free) for next row's x=0.
  Block done after n² cells. W_Γ(n) = total count (free top + free left/right borders:
  an interior free-floating block — matches PARQUET's interior patch-feasibility).

For variant B we carry the used-piece bitset in the state (exact, tiny n only).
"""
import sys, os, collections, math, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W

SIZE, PIECES, HINTS = load_puzzle()
NP = len(PIECES)
FREE = -1  # sentinel: no constraint (top border of block, or left border)

# interior pieces only (no border color), each with 4 rotations -> (N,E,S,W) tuples.
def build_placements(interior_only=True):
    pls = []  # list of (pid, N,E,S,W)
    for pid in range(NP):
        if interior_only and BORDER in PIECES[pid]:
            continue
        seen=set()
        for r in range(4):
            ed = rot_edges(PIECES[pid], r)
            key=(ed[N],ed[E],ed[S],ed[W])
            if key in seen: continue   # dedup identical rotations (none in E2, but safe)
            seen.add(key)
            pls.append((pid, ed[N], ed[E], ed[S], ed[W]))
    return pls

PLACE = build_placements(interior_only=True)
print(f"interior placements (piece×rot): {len(PLACE)}  (from {sum(1 for p in range(NP) if BORDER not in PIECES[p])} interior pieces)", flush=True)

# index placements by required (N, W) for fast lookup. N or W may be FREE -> any.
# We'll just filter per cell; PLACE is ~784 so linear scan per cell is fine for DP.
def count_reusable(n, cap_states=None):
    """Variant A: reusable pieces. Broken-profile DP. Returns W_Γ(n) (int)."""
    # state: (profile tuple length n, pend). profile[x]=FREE means top border (row0) free.
    # start: profile=(FREE,)*n, pend=FREE (row 0, col 0, no constraints).
    start = ((FREE,)*n, FREE)
    states = { start: 1 }
    for y in range(n):
        for x in range(n):
            new = collections.defaultdict(int)
            for (profile, pend), cnt in states.items():
                needN = profile[x]   # FREE or a color
                needW = pend         # FREE or a color
                for (pid, pn, pe, ps, pw) in PLACE:
                    if needN != FREE and pn != needN: continue
                    if needW != FREE and pw != needW: continue
                    np_profile = profile[:x] + (ps,) + profile[x+1:]
                    npend = pe if x < n-1 else FREE   # row ends -> W free next row
                    new[(np_profile, npend)] += cnt
            states = new
            if cap_states and len(states) > cap_states:
                # keep most-weighted states (approximation guard); flag it
                items = sorted(states.items(), key=lambda kv:-kv[1])[:cap_states]
                states = dict(items)
        # end of row y: pend already reset to FREE at x=n-1
    return sum(states.values())

def count_distinct(n, node_cap=50_000_000):
    """Variant B: distinct pieces. Exact DFS over n×n cells (row-major), used bitset.
       Only tractable for tiny n. Returns W_Γ(n)."""
    cnt=[0]; nodes=[0]; stop=[False]
    used=bytearray(NP)
    # frontier as a list profile[x] (S color of cell above) + pend
    profile=[FREE]*n
    # precompute placements grouped for speed: by (N,W) with FREE wildcards handled inline
    def dfs(idx, pend):
        if stop[0]: return
        nodes[0]+=1
        if nodes[0]>node_cap: stop[0]=True; return
        if idx==n*n:
            cnt[0]+=1; return
        x=idx%n
        needN=profile[x]; needW=pend
        for (pid,pn,pe,ps,pw) in PLACE:
            if used[pid]: continue
            if needN!=FREE and pn!=needN: continue
            if needW!=FREE and pw!=needW: continue
            used[pid]=1; old=profile[x]; profile[x]=ps
            dfs(idx+1, pe if x<n-1 else FREE)
            profile[x]=old; used[pid]=0
            if stop[0]: return
    dfs(0, FREE)
    return cnt[0], (not stop[0]), nodes[0]

if __name__=="__main__":
    print("\n=== Variant A: color-grammar entropy (reusable pieces) ===", flush=True)
    rowsA=[]
    for n in range(1, 6):
        try:
            w=count_reusable(n)
            s=math.log10(w) if w>0 else float('-inf')
            print(f"  n={n}: W_Γ={w}  S_Γ=log10={s:.4f}", flush=True)
            rowsA.append((n,w,s))
        except MemoryError:
            print(f"  n={n}: MemoryError (state blowup)"); break
    print("\n=== Variant B: true-E2 entropy (distinct pieces) ===", flush=True)
    rowsB=[]
    for n in range(1, 5):
        w,exact,nodes=count_distinct(n)
        tag="exact" if exact else f"PARTIAL(node_cap, nodes={nodes})"
        s=math.log10(w) if w>0 else float('-inf')
        print(f"  n={n}: W_Γ={w}  S_Γ={s:.4f}  [{tag}]", flush=True)
        rowsB.append((n,w,s,exact))
    # save
    import json
    json.dump({"variantA":rowsA,"variantB":[(n,w,s,e) for n,w,s,e in rowsB]},
              open("scripts/v209_isentrope/output/entropy_curve.json","w"))
    print("\nsaved scripts/v209_isentrope/output/entropy_curve.json")
