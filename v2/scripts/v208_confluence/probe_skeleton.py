"""
CONFLUENCE premise probe (vol-208).
Question: do high-score boards respect the (N,W)-pair scarcity skeleton?

A cell's (N,W) demand = (color it shows on North, color it shows on West).
A piece p SERVES (c1,c2) if some rotation r puts p.N=c1 and p.W=c2.
Scarcity finding (vol-204): 121/362 interior (N,W) pairs have exactly 1 server.

If high boards place the UNIQUE server of a pair at a cell whose (N,W) demand IS
that pair, then enforcing the skeleton from scratch biases toward high basins.
We measure: for each interior cell in a high board, what is its realized (N,W)
demand, how many pieces serve it, and is the placed piece a/the unique server?
"""
import sys, os, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'v203_patch_lp'))
import e2lib as E

SIZE, PIECES, HINTS = E.load_puzzle()
NP = len(PIECES)
N, Eh, S, W = 0, 1, 2, 3  # edge indices

def is_border_color(c): return c == 0  # border/grey color is 0 in this CSV? check
# In the official CSV the border color encodes as 0 (the frame). Verify:
border_vals = collections.Counter()
for p in PIECES:
    for c in p:
        border_vals[c]+=1
# color 0 should appear a lot (frame). Print top.
print("color multiplicities (top 6):", border_vals.most_common(6))
print("n distinct colors:", len(border_vals))

# Build server map over ALL (N,W) ordered pairs realizable by interior placement.
# A piece used in the interior can take any of 4 rotations. (N,W) it presents:
# for rotation r, edges = rot_edges(base,r); N=edges[0], W=edges[3].
# Restrict to interior-usable: a piece with a border(0) edge can still be interior-
# rotated so the 0 faces inward? In a real board interior cells never show color 0
# (0 only on frame outer rim). So interior (N,W) pairs have c1,c2 != 0.
servers = collections.defaultdict(set)   # (c1,c2) -> set of piece ids that can serve
server_rot = collections.defaultdict(list) # (c1,c2)->[(pid,rot)]
for pid in range(NP):
    base = PIECES[pid]
    if 0 in base:
        # piece touches frame; it *can* still present a non-zero N,W with the 0 elsewhere,
        # but border/corner pieces live on the rim. Include them anyway for completeness;
        # interior demands with c!=0 are what we filter on.
        pass
    seen=set()
    for r in range(4):
        ed = E.rot_edges(base, r)
        key=(ed[N], ed[W])
        if key in seen: continue
        seen.add(key)
        servers[key].add(pid)
        server_rot[key].append((pid,r))

# scarcity over interior pairs (both colors nonzero)
interior_pairs = [(k,v) for k,v in servers.items() if k[0]!=0 and k[1]!=0]
support = collections.Counter(len(v) for k,v in interior_pairs)
print(f"\n# interior (N,W) pairs (c1,c2 != 0): {len(interior_pairs)}")
print("support-size histogram (servers per pair): ",
      dict(sorted(support.items())))
uniq_pairs = {k for k,v in interior_pairs if len(v)==1}
print(f"unique-server interior pairs: {len(uniq_pairs)}")

def analyze(path, label):
    board, d = E.load_board(path)
    m,t = E.score_board(SIZE, PIECES, board)
    print(f"\n=== {label}: matched {m}/{t} (claimed {d.get('matched')}) ===")
    # For each interior cell (1..14 in both x,y) compute realized (N,W) demand
    # = (color on its North face, color on its West face) of the placed piece.
    # Then how many pieces serve that demand, and is placed piece the unique one.
    served_by_unique = 0; cells_on_uniq_pair = 0; interior_cells=0
    placed_is_a_server = 0
    histo_support = collections.Counter()
    for y in range(SIZE):
        for x in range(SIZE):
            pos = y*SIZE+x
            if pos not in board: continue
            pid,r = board[pos]
            ed = E.rot_edges(PIECES[pid], r)
            c1,c2 = ed[N], ed[W]
            if c1==0 or c2==0: continue  # skip rim-facing
            interior_cells+=1
            sup = len(servers[(c1,c2)])
            histo_support[sup]+=1
            if pid in servers[(c1,c2)]: placed_is_a_server+=1
            if (c1,c2) in uniq_pairs:
                cells_on_uniq_pair+=1
                # the unique server must be this very piece
                if servers[(c1,c2)] == {pid}:
                    served_by_unique+=1
    print(f"interior cells (nonzero N,W): {interior_cells}")
    print(f"  placed piece IS a server of its own realized demand: {placed_is_a_server}/{interior_cells}")
    print(f"  cells whose realized (N,W) is a UNIQUE-server pair: {cells_on_uniq_pair}")
    print(f"  ...and placed piece is that unique server: {served_by_unique}")
    print(f"  support histogram at realized demands: {dict(sorted(histo_support.items()))}")

analyze("output/vol-65/mcgavin_469.json", "McGavin 469")
analyze("output/vol-129/RECORD_463_corner2301_seed42.json", "vol-129 463")
