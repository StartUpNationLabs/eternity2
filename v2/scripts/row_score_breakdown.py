"""Use the rescore_board tool's logic — but we just need to compute
matched edges per row-window from a board JSON. Cleaner: use the 
Rust tool but we can also count via Python since we have piece data
embedded with rotations. To avoid CSV parsing complications, decode
via the bucas_url field if present (which encodes color edges).

Actually, simpler: scan the board, compute edge colors using the 
rust score (we can call repair_region with cluster=[single_cell] 
to get the precomputed boundary colors? No, too convoluted).

Let's read pieces.txt-style — actually I just realized the puzzle CSV
gives EDGES as bitmasks (colors as one-hot). Just parse it as integer 
position.
"""
import json
import sys
from pathlib import Path

# pieces.txt format from v2/../data: "16\n<16 color bits N>,<16 color E>,..."
# But the format we saw has 4-fields per piece with bitmasks. Each
# bitmask has a single bit set indicating color 1..16 (or 0 for border).
def bitmask_to_color(bs):
    bs = bs.strip()
    if all(c == '0' for c in bs):
        return 0
    # Position of '1' from right gives color (1-indexed)
    idx = bs[::-1].index('1') + 1
    return idx

def parse_puzzle(path):
    """Parse v2-style csv. First line = size. Each subsequent line:
       n_mask,e_mask,s_mask,w_mask,x,y,rot (or with hint suffix)
    """
    with open(path) as f:
        lines = f.read().splitlines()
    size = int(lines[0])
    pieces = []  # piece index = 0-based
    for line in lines[1:]:
        if not line.strip(): continue
        parts = line.split(',')
        if len(parts) < 4: continue
        n, e, s, w = parts[0], parts[1], parts[2], parts[3]
        pieces.append((bitmask_to_color(n), bitmask_to_color(e), bitmask_to_color(s), bitmask_to_color(w)))
    return size, pieces

def rotate(edges, r):
    n,e,s,w = edges
    if r==0: return (n,e,s,w)
    if r==1: return (w,n,e,s)
    if r==2: return (s,w,n,e)
    if r==3: return (e,s,w,n)

def load_board(path):
    with open(path) as f:
        d = json.load(f)
    arr = d['placement']
    pos2 = {}
    for it in arr:
        if it is None: continue
        pos2[int(it['pos'])] = (int(it['piece_id']), int(it['rotation']))
    return pos2

def score_by_row_window(pos2, pieces, W=16, H=16):
    # Internal-and-boundary edge categorization by row window pair.
    # Returns: matched_in_row[y] = matched edges where BOTH cells in row y or below row y boundary.
    # Simpler: edges = list of (matched: bool, type: 'h' or 'v', y1, y2).
    matched_h = [0]*H  # row y: horizontal edges in row y
    matched_v = [0]*(H-1)  # vertical between row y and y+1
    for pos, (pid, rot) in pos2.items():
        x, y = pos % W, pos // W
        edges = rotate(pieces[pid-1], rot)  # pid 1-indexed
        n, e, s, w = edges
        # Right edge
        if x+1 < W:
            r_pos = pos + 1
            if r_pos in pos2:
                rpid, rrot = pos2[r_pos]
                rn, re, rs, rw = rotate(pieces[rpid-1], rrot)
                if e == rw and e != 0:
                    matched_h[y] += 1
        # Bottom edge
        if y+1 < H:
            b_pos = pos + W
            if b_pos in pos2:
                bpid, brot = pos2[b_pos]
                bn, be, bs, bw = rotate(pieces[bpid-1], brot)
                if s == bn and s != 0:
                    matched_v[y] += 1
    return matched_h, matched_v

if __name__ == '__main__':
    size, pieces = parse_puzzle(sys.argv[1])
    board_path = sys.argv[2]
    pos2 = load_board(board_path)
    matched_h, matched_v = score_by_row_window(pos2, pieces, W=size, H=size)
    total = sum(matched_h) + sum(matched_v)
    print(f"Board: {board_path}")
    print(f"  Total matched: {total}")
    print(f"  Per-row horizontal matched (rows 0-15):")
    for y, h in enumerate(matched_h):
        print(f"    row {y:>2}: h={h:>2}")
    print(f"  Per-row pair vertical matched (between row y and y+1):")
    for y, v in enumerate(matched_v):
        print(f"    rows {y:>2}-{y+1:>2}: v={v:>2}")
    # 4-row windows.
    print(f"  4-row windows internal+touching edges:")
    for w in [(0,3),(4,7),(8,11),(12,15)]:
        y_lo, y_hi = w
        in_h = sum(matched_h[y_lo:y_hi+1])
        in_v = sum(matched_v[y_lo:y_hi]) if y_hi > y_lo else 0
        bdy_v = (matched_v[y_lo-1] if y_lo > 0 else 0) + (matched_v[y_hi] if y_hi < size-1 else 0)
        print(f"    rows {y_lo}-{y_hi}: int_h={in_h}, int_v={in_v}, bdy_v={bdy_v}, total_window={in_h+in_v}, with_bdy={in_h+in_v+bdy_v}")
