#!/usr/bin/env python3
"""vol-211: tail supply-vs-demand diagnosis. Take a complete interior board,
strip the last K cells (row-major over the 14x14), and ask: over the K
removed pieces and K cells, what is the max bipartite matching where
piece->cell is allowed iff some rotation matches the cell's UP color
(up edges are fixed by row above)? K-matching = supply OK (loss is in the
horizontal chaining); < K = up-supply starvation (reservation could help).
Also reports the same for up AND left-from-final-board (arrangement-bound).
Usage: tail_supply.py <board.json> [K]"""
import json, sys

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"
N = 14


def load_pieces():
    pieces = []
    with open(PUZZLE_CSV) as f:
        f.readline()
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == 65535 else v
            pieces.append(tuple(col(x) for x in p[:4]))
    return pieces


def rot(q, r):
    return tuple(q[(s - r) % 4] for s in range(4))


def hopcroft(adj, nl, nr):
    # simple augmenting-path matching (K<=30, fine)
    match_l = [-1] * nl
    match_r = [-1] * nr

    def aug(u, seen):
        for v in adj[u]:
            if not seen[v]:
                seen[v] = True
                if match_r[v] == -1 or aug(match_r[v], seen):
                    match_l[u] = v
                    match_r[v] = u
                    return True
        return False

    m = 0
    for u in range(nl):
        if aug(u, [False] * nr):
            m += 1
    return m


def main():
    pieces = load_pieces()
    path = sys.argv[1]
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 22
    d = json.load(open(path))
    cellmap = {}
    for e in d["placement"]:
        pos = e["pos"]
        y, x = pos // 16, pos % 16
        cell = (y - 1) * N + (x - 1)
        cellmap[cell] = (e["piece_id"], e["rotation"])
    start = N * N - k
    tail_cells = list(range(start, N * N))
    tail_pieces = [cellmap[c][0] for c in tail_cells]
    up_color = {}
    for c in tail_cells:
        upid, uprot = cellmap[c - N]
        if c - N >= start:
            # up inside tail: use its placed value (board is complete)
            pass
        up_color[c] = rot(pieces[upid], uprot)[2]
    # bipartite: piece i -> cell j if some rotation matches up color
    adj_up = []
    for pid in tail_pieces:
        row = []
        for j, c in enumerate(tail_cells):
            if any(rot(pieces[pid], r)[0] == up_color[c] for r in range(4)):
                row.append(j)
        adj_up.append(row)
    m_up = hopcroft(adj_up, k, k)
    # up AND left (left from the final board's own arrangement)
    adj_ul = []
    for pid in tail_pieces:
        row = []
        for j, c in enumerate(tail_cells):
            ok = False
            for r in range(4):
                e = rot(pieces[pid], r)
                if e[0] != up_color[c]:
                    continue
                if c % N == 0:
                    ok = True
                    break
                lpid, lrot = cellmap[c - 1]
                if rot(pieces[lpid], lrot)[1] == e[3]:
                    ok = True
                    break
            if ok:
                row.append(j)
        adj_ul.append(row)
    m_ul = hopcroft(adj_ul, k, k)
    print(f"{path}")
    print(f"  tail K={k}: up-only max matching = {m_up}/{k}")
    print(f"  up+left(final-board) matching   = {m_ul}/{k}")
    print("  -> up-deficit", k - m_up, "(supply starvation); chaining costs the rest")


if __name__ == "__main__":
    main()
