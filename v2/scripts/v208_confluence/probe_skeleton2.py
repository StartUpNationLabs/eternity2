"""
CONFLUENCE premise probe v2 (vol-208) — corrected border filter (border=65535)
+ co-activation conflict structure of unique-server demands.

Key reframe from v1: high boards realize ~30 of the 121 unique-server (N,W) pairs;
the placed piece is forced once a demand is activated. The combinatorial core is
WHICH unique-server demands can be co-activated. We measure:
  (a) true interior cell count (should be 196) with correct border filter,
  (b) per high board: how many of the 121 unique-server demands are activated,
  (c) PIECE CONTENTION among unique servers: do distinct unique-server demands
      share a server piece? (a piece can be the unique server of >1 demand ->
      activating both is IMPOSSIBLE, a hard conflict the constructor must respect).
"""
import sys, os, collections, itertools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
import e2lib as E

SIZE, PIECES, HINTS = E.load_puzzle()
NP = len(PIECES)
N, Eh, S, W = 0, 1, 2, 3
BORDER = 65535

servers = collections.defaultdict(set)
server_rot = collections.defaultdict(list)
for pid in range(NP):
    base = PIECES[pid]
    seen=set()
    for r in range(4):
        ed = E.rot_edges(base, r)
        key=(ed[N], ed[W])
        if key in seen: continue
        seen.add(key)
        servers[key].add(pid)
        server_rot[key].append((pid,r))

interior_pairs = {k:v for k,v in servers.items() if k[0]!=BORDER and k[1]!=BORDER}
uniq = {k:next(iter(v)) for k,v in interior_pairs.items() if len(v)==1}  # pair->the piece
print(f"interior (N,W) pairs: {len(interior_pairs)}; unique-server pairs: {len(uniq)}")

# (c) PIECE CONTENTION: which pieces are the unique server of MULTIPLE demands.
piece_to_uniqdemands = collections.defaultdict(list)
for pair,pid in uniq.items():
    piece_to_uniqdemands[pid].append(pair)
multi = {pid:ds for pid,ds in piece_to_uniqdemands.items() if len(ds)>1}
print(f"\npieces that are the UNIQUE server of >1 demand: {len(multi)}")
nconf = sum(len(ds) for ds in multi.values())
print(f"  total unique-demands tied up in such pieces: {nconf}")
print("  distribution (#demands per such piece):",
      dict(sorted(collections.Counter(len(ds) for ds in multi.values()).items())))
# These are HARD mutual-exclusions: a single piece cannot simultaneously sit at two
# different cells, so at most ONE of its unique-demands can be activated.
print("  => at most 1 of each such group's demands is realizable (hard conflict).")

# How many demands are 'free' (their unique server serves no other unique demand)?
free_uniq = [p for p,pid in uniq.items() if len(piece_to_uniqdemands[pid])==1]
print(f"  'free' unique demands (server dedicated): {len(free_uniq)}")

def analyze(path, label):
    board, d = E.load_board(path)
    m,t = E.score_board(SIZE, PIECES, board)
    interior=0; uniq_active=0; activated=[]
    for y in range(SIZE):
        for x in range(SIZE):
            pos=y*SIZE+x
            if pos not in board: continue
            pid,r=board[pos]
            ed=E.rot_edges(PIECES[pid],r)
            c1,c2=ed[N],ed[W]
            if c1==BORDER or c2==BORDER: continue
            interior+=1
            if (c1,c2) in uniq:
                uniq_active+=1
                activated.append((c1,c2))
    print(f"\n=== {label}: {m}/{t} ; interior cells {interior} ===")
    print(f"  unique-server demands ACTIVATED: {uniq_active} of {len(uniq)}")
    # are any activated demands mutually exclusive? (sanity: a valid board can't
    # activate two demands served by the same unique piece)
    used_pieces=collections.Counter(uniq[a] for a in activated)
    dup=[p for p,c in used_pieces.items() if c>1]
    print(f"  (sanity) same unique-piece used for 2 activated demands: {len(dup)} (must be 0)")
    return set(activated)

a1=analyze("output/vol-65/mcgavin_469.json","McGavin 469")
a2=analyze("output/vol-129/RECORD_463_corner2301_seed42.json","vol-129 463")
print(f"\nactivated-demand overlap McGavin vs 463: {len(a1&a2)} shared "
      f"(McG {len(a1)}, 463 {len(a2)}); jaccard={len(a1&a2)/len(a1|a2):.2f}")
