"""
LODESTONE prior (vol-208) — a scarce-demand-frequency prior matrix for the
KEYRING/V155 beam constructor.

Today's measurement ([[scarcity-skeleton-shared-core]]): high boards (>=458)
activate a SOFT, score-correlated set of scarce (N,W) demands. The count of
demands present in >=50% of boards rises monotonically with score (1->2->3->10).
This is a real signal NEVER wired into a constructor (MOSAIC used only a scalar
reservation; V155's prior is piece-at-position frequency, basin-specific).

LODESTONE converts the demand-frequency signal into KEYRING's per-(piece,position)
prior format:
  prior[piece p][pos] = sum over rotations r of [ freq_>=458( (p@r).N, (p@r).W ) ]
weighted so that placing p at pos in a rotation that REALIZES a high-board-frequent
scarce demand is preferred. We compute freq over the >=458 corpus (re-scored),
restricted to UNIQUE-SERVER demands (the scarce ones), and also include a milder
term for 2-server demands.

The prior is position-INDEPENDENT in its raw demand form (a demand can be realized
anywhere), so we broadcast the per-(piece,rotation) demand-frequency to all
positions, EXCEPT we zero it on border positions for interior pieces (and vice
versa) to respect class. KEYRING already enforces class via by_class; the prior
just biases ranking, so broadcasting is fine.

Output: JSON {"matrix": [[...256 pos...] x 256 pieces]} of integer counts (KEYRING
parses u64). We scale freqs to integers.
"""
import sys, os, json, collections, glob, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
from e2lib import load_puzzle, rot_edges, BORDER, N, E, S, W, load_board, score_board

SIZE, PIECES, HINTS = load_puzzle()
NP=len(PIECES); NPOS=SIZE*SIZE

# 1. server multiplicity per (N,W) demand
servers=collections.defaultdict(set)
for pid in range(NP):
    for r in range(4):
        ed=rot_edges(PIECES[pid],r); servers[(ed[N],ed[W])].add(pid)
mult={k:len(v) for k,v in servers.items()}

# 2. corpus demand frequency over >=458 boards (re-scored, fakes filtered)
freq=collections.Counter(); nb=0
for f in glob.glob("database-400-480/*.json"):
    m=re.match(r'(\d+)_', os.path.basename(f))
    if not m or int(m.group(1))<458: continue
    try:
        board,d=load_board(f); sc,t=score_board(SIZE,PIECES,board)
        if abs(sc-int(m.group(1)))>2: continue
        seen=set()
        for pos,(pid,r) in board.items():
            ed=rot_edges(PIECES[pid],r); key=(ed[N],ed[W])
            if key[0]==BORDER or key[1]==BORDER: continue
            if key in seen: continue
            seen.add(key); freq[key]+=1
        nb+=1
    except Exception: continue
print(f"corpus >=458 boards used: {nb}")
print(f"distinct demands seen: {len(freq)}; top: {freq.most_common(5)}")

# 3. weight per (piece, rotation): demand-frequency, boosted for scarcer demands.
#    w(p,r) = freq[(N,W)] * scarcity_boost(mult)  ; scarcity_boost: 1-server=3, 2=2, else=1
def boost(k):
    mk=mult.get(k,99)
    return 3.0 if mk==1 else (2.0 if mk==2 else 1.0)
piece_weight=[0.0]*NP
for pid in range(NP):
    best=0.0
    seen=set()
    for r in range(4):
        ed=rot_edges(PIECES[pid],r); key=(ed[N],ed[W])
        if key[0]==BORDER or key[1]==BORDER: continue
        if key in seen: continue
        seen.add(key)
        w=freq.get(key,0)*boost(key)
        best=max(best,w)   # piece's affinity = its best demand-realizing rotation
    piece_weight[pid]=best

# 4. broadcast to all positions as the prior matrix (KEYRING: score + alpha*prior_sum).
#    Integer scale (KEYRING parses u64). Scale so max ~ 1000.
mx=max(piece_weight) or 1.0
SCALE=1000.0/mx
matrix=[]
for pid in range(NP):
    val=int(round(piece_weight[pid]*SCALE))
    matrix.append([val]*NPOS)   # position-independent demand prior

out={"matrix": matrix, "_meta": {
    "name":"LODESTONE", "vol":208, "boards_used":nb,
    "desc":"scarce-demand-frequency prior; prior[p][pos]=best demand-realizing-rotation freq*scarcity_boost, broadcast over positions"}}
outpath="scripts/v208_confluence/output/lodestone_prior.json"
os.makedirs(os.path.dirname(outpath), exist_ok=True)
json.dump(out, open(outpath,'w'))
print(f"wrote {outpath}")
# sanity: distribution of piece weights
nz=sum(1 for v in piece_weight if v>0)
print(f"pieces with nonzero demand affinity: {nz}/{NP}; max raw {mx:.0f}, scaled max {int(mx*SCALE)}")
print(f"top-10 pieces by affinity: {sorted(range(NP), key=lambda p:-piece_weight[p])[:10]}")
