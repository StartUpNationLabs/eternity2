#!/usr/bin/env python3
"""LADDER rank v2: score = depth − λ·deficit, dedup by content, diversity cap.

deficit = Σ_c max(0, F_c − S_c) over the prefix state (LEDGER measure):
F_c = frame rim targets on empty interior cells + placed interior sides
facing empty interior cells; S_c = sides of unused interior pieces.

Usage: ladder_rank2.py <puzzle_csv> <frame_json> <probe_dir...> --k K --lam L --maxov OV
Prints: <path> <pin_depth> <depth> <deficit> per selected prefix.
"""
import json
import sys
from glob import glob

args = sys.argv[1:]
def opt(name, default):
    if name in args:
        return float(args[args.index(name) + 1])
    return default
K = int(opt('--k', 12)); LAM = opt('--lam', 2.0); MAXOV = opt('--maxov', 0.8)
puzzle_csv, frame_json = args[0], args[1]
dirs = [a for a in args[2:] if not a.startswith('--') and not a.replace('.', '').isdigit()]

lines = [l.strip() for l in open(puzzle_csv) if l.strip()]
pieces = [[int(x, 2) for x in l.split(',')[:4]] for l in lines[1:]]
def edges_of(pid, rot):
    e = pieces[pid]
    return [e[(s - rot) % 4] for s in range(4)]

ring = {e['pos']: (e['piece_id'], e['rotation'])
        for e in json.load(open(frame_json))['placement'] }
interior_pids = {pid for pid in range(256) if 0 not in pieces[pid]}

def rim_target(pos, side):
    d = {0: -16, 1: 1, 2: 16, 3: -1}[side]
    npos = pos + d
    if npos in ring:
        return edges_of(*ring[npos])[(side + 2) % 4]
    return None

def deficit_of(cells):
    used = {v[0] for v in cells.values()}
    S = {}
    for pid in interior_pids - used:
        for c in pieces[pid]:
            S[c] = S.get(c, 0) + 1
    F = {}
    for y in range(1, 15):
        for x in range(1, 15):
            pos = y * 16 + x
            if pos in cells:
                continue
            for s in range(4):
                t = rim_target(pos, s)
                if t is not None:
                    F[t] = F.get(t, 0) + 1
    for pos, (pid, rot) in cells.items():
        e = edges_of(pid, rot)
        for s, d in ((0, -16), (1, 1), (2, 16), (3, -1)):
            npos = pos + d
            ny, nx = npos // 16, npos % 16
            if 1 <= ny <= 14 and 1 <= nx <= 14 and npos not in cells:
                F[e[s]] = F.get(e[s], 0) + 1
    return sum(max(0, F.get(c, 0) - S.get(c, 0)) for c in F)

cands, seen = [], set()
for d in dirs:
    for f in glob(f"{d}/prefix_d*.json"):
        pl = json.load(open(f))['placement']
        cells = {e['pos']: (e['piece_id'], e['rotation']) for e in pl}
        h = hash(frozenset((p, v) for p, v in cells.items()))
        if h in seen:
            continue
        seen.add(h)
        df = deficit_of(cells)
        cands.append((len(cells) - LAM * df, len(cells), df, f, cells))
cands.sort(key=lambda t: -t[0])

kept = []
for score, depth, df, f, cells in cands:
    if len(kept) >= K:
        break
    if all(sum(1 for p, v in cells.items() if kc.get(p) == v)
           / min(len(cells), len(kc)) <= MAXOV for *_, kc in kept):
        kept.append((score, depth, df, f, cells))

for score, depth, df, f, _ in kept:
    print(f, max(20, depth - 15), depth, df)
