#!/usr/bin/env python3
"""vol-211 Phase 0b: linear-placement adjacency (LPA) diagnostic.

Convention (derived 2026-06-10, parity argument): the veteran's "231/258
linear placement adjacencies" lives on the BORDER-FIRST scan ladder:
  scan = border ring (60 cells, ring order) then interior row-major (196).
  prefix adjacency totals: 60 after ring; each interior cell adds +2
  (left+up, with border supplying the missing side at row edges) except
  +3 at interior row-last (right-border edge), +3.. at bottom row.
  The ladder passes through 231 at depth 143 and 258 at depth 156.
  Row-major prefixes on 16-wide and 14-wide rectangles SKIP both values
  (231 and 258 unreachable - parity).

For each board: LPA_bf(d) for d=1..256, report:
  - matched at d=156 (the /258 point)  -> the veteran metric
  - max d with perfect prefix (all adjacencies of prefix matched)
  - matched at d=143 (the /231 point)
"""
import json, sys, glob

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"
BORDER_RAW = 65535
W = 16


def load_pieces():
    pieces = []
    with open(PUZZLE_CSV) as f:
        f.readline()
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            pieces.append(tuple(col(p) for p in parts[:4]))
    return pieces


def rot(q, r):
    return tuple(q[(s - r) % 4] for s in range(4))


def board_edges(path, pieces):
    d = json.load(open(path))
    place = {}
    if "placement" in d:
        arr = d["placement"]
        for i, e in enumerate(arr):
            pos = e.get("pos", i)
            place[pos] = (e["piece_id"], e["rotation"])
    else:
        return None
    if len(place) != 256:
        return None
    return {pos: rot(pieces[p], r) for pos, (p, r) in place.items()}


def border_first_order():
    order = []
    # ring order: top row L->R, right col T->B, bottom row R->L, left col B->T
    for x in range(W):
        order.append(x)
    for y in range(1, W):
        order.append(y * W + (W - 1))
    for x in range(W - 2, -1, -1):
        order.append((W - 1) * W + x)
    for y in range(W - 2, 0, -1):
        order.append(y * W)
    for y in range(1, W - 1):
        for x in range(1, W - 1):
            order.append(y * W + x)
    assert len(order) == 256 and len(set(order)) == 256
    return order


def lpa_curve(edges, order):
    """Returns list (d, total_adj, matched_adj) cumulative along scan."""
    placed = set()
    total = matched = 0
    out = []
    for pos in order:
        y, x = divmod(pos, W)
        e = edges[pos]
        for (nx, ny, s_self, s_other) in ((x - 1, y, 3, 1), (x + 1, y, 1, 3),
                                          (x, y - 1, 0, 2), (x, y + 1, 2, 0)):
            if 0 <= nx < W and 0 <= ny < W:
                npos = ny * W + nx
                if npos in placed:
                    total += 1
                    ne = edges[npos]
                    if e[s_self] == ne[s_other] and e[s_self] != 0:
                        matched += 1
        placed.add(pos)
        out.append((len(placed), total, matched))
    return out


def main():
    pieces = load_pieces()
    order = border_first_order()
    print("board\tmatched@156(/258)\tmatched@143(/231)\tmax_perfect_d\tfinal")
    for path in sys.argv[1:]:
        files = sorted(glob.glob(path))
        if not files:
            print(f"MISSING: {path}", file=sys.stderr)
            continue
        for f in files:
            edges = board_edges(f, pieces)
            if edges is None:
                continue
            curve = lpa_curve(edges, order)
            at156 = curve[155]
            at143 = curve[142]
            assert at156[1] == 258, f"ladder broken: {at156}"
            assert at143[1] == 231, f"ladder broken: {at143}"
            maxperf = 0
            for d, t, m in curve:
                if m == t:
                    maxperf = d
            name = f.split("/")[-1]
            print(f"{name}\t{at156[2]}/258\t{at143[2]}/231\t{maxperf}\t{curve[-1][2]}/480")


if __name__ == "__main__":
    main()
