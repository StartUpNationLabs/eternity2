#!/usr/bin/env python3
"""Fast plaquette state-count using indexed-by-color tables.

Strategy:
- For each cell pos, precompute valid_configs[pos] = list of (pid, rot, edges-N,E,S,W).
- Index per-cell by (east_color, south_color) so 2×2 plaquette enumeration
  becomes: pick TL config; for each TR config matching TL.east → look up BL
  configs matching TL.south → look up BR configs matching (BL.east, TR.south).
- Soft uniqueness: just count plaquette-internal piece collisions (4 distinct).

Output: per-plaquette state count + cumulative timing. Doesn't compute GBP
marginals yet — that's the v2 if state counts are tractable.
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path
from collections import defaultdict
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v11_load_e2 as loader

W = H = 16
BORDER = 0


def piece_class(p):
    n = int((p == BORDER).sum())
    if n == 2: return 0  # corner
    if n == 1: return 1  # edge
    return 2  # interior


def cell_class(pos):
    x, y = pos % W, pos // W
    n = int(x == 0) + int(x == W - 1) + int(y == 0) + int(y == H - 1)
    if n == 2: return 0
    if n == 1: return 1
    return 2


def precompute_cells(pieces, hints):
    """For each cell pos, build a numpy array of shape (n_configs, 6):
    columns = [pid, rot, N, E, S, W]. Plus indexed-by-(E,S), (N,W), etc.
    """
    hint_pieces_at = {pos: (pid, rot) for pos, pid, rot in hints}
    cells = {}
    for pos in range(W * H):
        if pos in hint_pieces_at:
            pid, rot = hint_pieces_at[pos]
            rotated = np.roll(pieces[pid], rot)
            cells[pos] = np.array([[pid, rot, *rotated]], dtype=np.int32)
            continue
        cc = cell_class(pos)
        x, y = pos % W, pos // W
        must_border = [y == 0, x == W - 1, y == H - 1, x == 0]
        rows = []
        for pid in range(256):
            if piece_class(pieces[pid]) != cc: continue
            for rot in range(4):
                rotated = tuple(int(c) for c in np.roll(pieces[pid], rot))
                ok = True
                for s in range(4):
                    if must_border[s] and rotated[s] != BORDER: ok = False; break
                    if (not must_border[s]) and rotated[s] == BORDER: ok = False; break
                if ok:
                    rows.append([pid, rot, *rotated])
        cells[pos] = np.array(rows, dtype=np.int32) if rows else np.zeros((0, 6), dtype=np.int32)
    return cells


def count_plaquettes(cells, limit_per=None):
    """For each (x0, y0) in [0..W-2] × [0..H-2], count valid 2×2 joint
    configs using indexed enumeration."""
    state_counts = {}
    sample = {}
    t0 = time.time()
    for y0 in range(H - 1):
        for x0 in range(W - 1):
            tl = y0 * W + x0
            tr = y0 * W + x0 + 1
            bl = (y0 + 1) * W + x0
            br = (y0 + 1) * W + x0 + 1
            A = cells[tl]; B = cells[tr]; C = cells[bl]; D = cells[br]
            if len(A) == 0 or len(B) == 0 or len(C) == 0 or len(D) == 0:
                state_counts[(x0, y0)] = 0; continue
            # Index B by W (B[:, 5]) ; C by N (C[:, 2]) ; D by (N, W).
            B_by_w = defaultdict(list)
            for i, row in enumerate(B): B_by_w[row[5]].append(i)
            C_by_n = defaultdict(list)
            for i, row in enumerate(C): C_by_n[row[2]].append(i)
            D_by_nw = defaultdict(list)
            for i, row in enumerate(D): D_by_nw[(row[2], row[5])].append(i)

            cnt = 0
            for i, a in enumerate(A):
                pa, ra, an, ae, as_, aw = a
                # B match: a.E == b.W
                for j in B_by_w.get(ae, ()):
                    b = B[j]
                    if b[0] == pa: continue  # piece uniqueness
                    # C match: a.S == c.N
                    for k in C_by_n.get(as_, ()):
                        c = C[k]
                        if c[0] in (pa, b[0]): continue
                        # D match: b.S == d.N AND c.E == d.W
                        for l in D_by_nw.get((b[4], c[3]), ()):
                            d = D[l]
                            if d[0] in (pa, b[0], c[0]): continue
                            cnt += 1
                            if limit_per is not None and cnt >= limit_per:
                                break
                        if limit_per is not None and cnt >= limit_per: break
                    if limit_per is not None and cnt >= limit_per: break
                if limit_per is not None and cnt >= limit_per: break

            state_counts[(x0, y0)] = cnt
    return state_counts, time.time() - t0


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-per", type=int, default=None,
                    help="cap state count per plaquette (None=exact)")
    ap.add_argument("--out", type=str, default="output/v12_cvm/plaquette_counts.json")
    args = ap.parse_args()

    p = loader.load()
    pieces = p["pieces"]
    hints = p["hints"]
    print(f"=== fast 2×2 plaquette state counts (canonical E2) ===")
    t0 = time.time()
    cells = precompute_cells(pieces, hints)
    sizes = [len(c) for c in cells.values()]
    print(f"per-cell config sizes: min={min(sizes)} max={max(sizes)} "
          f"sum={sum(sizes):,}  (precompute: {time.time()-t0:.1f}s)")

    counts, elapsed = count_plaquettes(cells, limit_per=args.limit_per)
    vals = np.array(list(counts.values()))
    print(f"enumerated {len(counts)} plaquettes in {elapsed:.1f}s")
    print(f"plaquette state counts: min={vals.min()} max={vals.max()} "
          f"median={int(np.median(vals))} mean={vals.mean():.0f} "
          f"sum={vals.sum():,}")
    # Class breakdown.
    print()
    print("top-10 largest plaquettes (by state count):")
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:10]
    for (x0, y0), n in top:
        # Classify by cells in the 2x2.
        classes = []
        for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            cc = cell_class((y0 + dy) * W + (x0 + dx))
            classes.append("CEI"[cc])
        print(f"  ({x0},{y0}) {''.join(classes)}: {n:,}")
    print()
    print("top-10 smallest:")
    bot = sorted(counts.items(), key=lambda kv: kv[1])[:10]
    for (x0, y0), n in bot:
        classes = []
        for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            cc = cell_class((y0 + dy) * W + (x0 + dx))
            classes.append("CEI"[cc])
        print(f"  ({x0},{y0}) {''.join(classes)}: {n:,}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        json.dump({"schema_version": 1, "elapsed_s": elapsed,
                   "limit_per": args.limit_per,
                   "counts": {f"{x},{y}": int(v) for (x, y), v in counts.items()}}, f)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
