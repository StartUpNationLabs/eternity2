#!/usr/bin/env python3
"""Enumerate top-side paths in pure Python with start=1, end=2 to see how many exist."""
import sys, time
sys.path.insert(0, 'scripts')
from verify_rust_border_encoding import load_pieces, rotated

size, pieces = load_pieces('../data/puzzles/size_16_official_eternity.csv')

# Build edge placements for TOP side: each edge piece, rotation forced by border-on-top.
def edge_pl_top():
    out = []
    for pid, q in enumerate(pieces):
        if sum(1 for c in q if c == 0) != 1: continue
        for r in range(4):
            e = rotated(q, r)
            t,ri,b,le = e
            if t == 0:
                out.append((pid, r, le, ri, b))  # prev=le, next=ri, inward=b
    return out

eps = edge_pl_top()
print(f'top edge placements: {len(eps)}')

from collections import defaultdict
by_prev = defaultdict(list)
for ep in eps:
    by_prev[ep[2]].append(ep)

print(f'by_prev keys: {sorted(by_prev.keys())}')
print(f'by_prev counts: {[(k, len(v)) for k,v in sorted(by_prev.items())]}')

start, end = 1, 2
length = 14
results = []
nodes = [0]
t0 = time.time()
TIME_BUDGET = 30.0

def rec(idx, required_prev, used, current):
    if time.time() - t0 > TIME_BUDGET: return
    nodes[0] += 1
    if idx == length:
        if current[-1][3] == end:
            results.append(list(current))
            if len(results) % 1000 == 0:
                print(f'  found={len(results)} nodes={nodes[0]} elapsed={time.time()-t0:.1f}s')
        return
    last = idx == length - 1
    for opt in by_prev.get(required_prev, []):
        pid = opt[0]
        if pid in used: continue
        if last and opt[3] != end: continue
        used.add(pid)
        current.append(opt)
        rec(idx+1, opt[3], used, current)
        current.pop()
        used.remove(pid)
        if time.time() - t0 > TIME_BUDGET: return

rec(0, start, set(), [])
print(f'\ntop paths start=1 end=2: {len(results)} (nodes={nodes[0]} time={time.time()-t0:.1f}s)')
EOF
