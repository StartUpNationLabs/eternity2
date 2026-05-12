#!/usr/bin/env python3
"""CVM / generalized BP with 2×2 plaquette regions on canonical E2.

Region = 2×2 block of 4 adjacent cells. Internal-to-region edges (3) are
all enforced as part of the region factor (sum over all valid joint
assignments). Adjacent plaquettes share a 1×2 strip of cells (2 of the
4); messages pass on this shared strip.

This captures short-range correlations BP misses (BP factors are per-
internal-edge; here a single factor reasons about all 4 internal edges
of a 2×2 block jointly).

Output: per-internal-edge marginal entropy after a fixed number of GBP
iterations. Compare to vol-11 cell-BP 8.4% and vol-12 edge-BP 18.8%.

This is the explicit follow-up to `reference_e2_bp_measurements.md`'s
suggestion: "CVM / generalized BP on 2×2 plaquettes ... captures short-
range correlations BP misses. ~225 plaquettes × ~10⁴ states each".
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Tuple, Dict

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v11_load_e2 as loader

W = H = 16
BORDER = 0
NSTATE = 23


def piece_class(piece_edges):
    n_border = int((piece_edges == BORDER).sum())
    if n_border == 2: return "corner"
    if n_border == 1: return "edge"
    return "interior"


def cell_class(pos):
    x, y = pos % W, pos // W
    n = int(x == 0) + int(x == W - 1) + int(y == 0) + int(y == H - 1)
    if n == 2: return "corner"
    if n == 1: return "edge"
    return "interior"


def cell_valid_pieces(pos, pieces, hint_pieces_at):
    """List of (pid, rot, rotated_edges as tuple) valid at cell pos."""
    if pos in hint_pieces_at:
        pid, rot = hint_pieces_at[pos]
        return [(pid, rot, tuple(int(c) for c in np.roll(pieces[pid], rot)))]
    cclass = cell_class(pos)
    x, y = pos % W, pos // W
    must_border = [y == 0, x == W - 1, y == H - 1, x == 0]
    out = []
    for pid in range(256):
        if piece_class(pieces[pid]) != cclass:
            continue
        for rot in range(4):
            rotated = tuple(int(c) for c in np.roll(pieces[pid], rot))
            ok = True
            for s in range(4):
                if must_border[s] and rotated[s] != BORDER: ok = False; break
                if (not must_border[s]) and rotated[s] == BORDER: ok = False; break
            if ok:
                out.append((pid, rot, rotated))
    return out


def enumerate_plaquettes(pieces, hints, limit_per=200_000):
    """For each 2x2 top-left corner (x in 0..W-1, y in 0..H-1), enumerate
    valid joint assignments. Returns dict (x,y) -> list of joint configs.

    Joint config: tuple of 4 (pid, rot) — TL, TR, BL, BR — plus the 4
    "outer" colors (the edge colors of the plaquette facing OUT of the
    2x2 block: top of TL, top of TR, right of TR, right of BR, bottom of
    BR, bottom of BL, left of BL, left of TL — that's 8 outer-color slots).
    """
    hint_pieces_at = {pos: (pid, rot) for pos, pid, rot in hints}

    # Per-cell config list.
    cell_cfgs = {}
    for pos in range(W * H):
        cell_cfgs[pos] = cell_valid_pieces(pos, pieces, hint_pieces_at)

    plaq = {}
    for y0 in range(H - 1):
        for x0 in range(W - 1):
            tl = y0 * W + x0
            tr = y0 * W + x0 + 1
            bl = (y0 + 1) * W + x0
            br = (y0 + 1) * W + x0 + 1
            tls = cell_cfgs[tl]; trs = cell_cfgs[tr]
            bls = cell_cfgs[bl]; brs = cell_cfgs[br]
            # Internal edges: TL.right == TR.left ; TL.bot == BL.top ;
            #                 TR.bot == BR.top ; BL.right == BR.left.
            # Index colors as rotated[s] where s = [N=0, E=1, S=2, W=3].
            joints = []
            count = 0
            # 4-loop with early pruning.
            for (pidA, rotA, edA) in tls:
                for (pidB, rotB, edB) in trs:
                    if edA[1] != edB[3]: continue
                    for (pidC, rotC, edC) in bls:
                        if edA[2] != edC[0]: continue
                        for (pidD, rotD, edD) in brs:
                            if edB[2] != edD[0]: continue
                            if edC[1] != edD[3]: continue
                            # Soft piece-uniqueness within plaquette: 4 pieces
                            # must be all distinct.
                            if len({pidA, pidB, pidC, pidD}) < 4: continue
                            outer = (edA[0], edB[0], edB[1], edD[1],
                                     edD[2], edC[2], edC[3], edA[3])
                            joints.append({
                                "p": (pidA, rotA, pidB, rotB, pidC, rotC, pidD, rotD),
                                "outer": outer,
                            })
                            count += 1
                            if count >= limit_per:
                                break
                        if count >= limit_per: break
                    if count >= limit_per: break
                if count >= limit_per: break
            plaq[(x0, y0)] = joints
    return plaq


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-per", type=int, default=200_000)
    ap.add_argument("--out", type=str, default="output/v12_cvm/plaquettes.json")
    ap.add_argument("--summary", action="store_true",
                    help="just print sizes, don't dump full data")
    args = ap.parse_args()

    p = loader.load()
    pieces = p["pieces"]
    hints = p["hints"]
    print(f"=== CVM 2×2 plaquette enumeration on canonical E2 ===")

    t0 = time.time()
    plaq = enumerate_plaquettes(pieces, hints, limit_per=args.limit_per)
    elapsed = time.time() - t0
    sizes = [len(v) for v in plaq.values()]
    print(f"enumerated {len(plaq)} plaquettes in {elapsed:.1f}s")
    print(f"plaquette joint-state counts: min={min(sizes)} max={max(sizes)} "
          f"median={int(np.median(sizes))} mean={np.mean(sizes):.0f} "
          f"sum={sum(sizes):,}")
    print(f"plaquettes with state count >= limit ({args.limit_per}): "
          f"{sum(1 for s in sizes if s >= args.limit_per)}")
    # Class breakdown.
    pos_classes = Counter()
    for (x0, y0), joints in plaq.items():
        block_classes = []
        for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
            pos = (y0 + dy) * W + (x0 + dx)
            block_classes.append(cell_class(pos))
        pos_classes[tuple(sorted(block_classes))] += 1
    print("plaquette spatial-class breakdown:")
    for k, v in pos_classes.most_common(20):
        print(f"  {k}: {v}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "n_plaquettes": len(plaq),
        "elapsed_s": elapsed,
        "state_counts": {f"{x},{y}": len(plaq[(x, y)]) for (x, y) in plaq},
        "sum_states": sum(sizes),
        "min": min(sizes), "max": max(sizes), "median": int(np.median(sizes)),
    }
    if not args.summary:
        # Don't dump 10^6+ joint configs — just summary + sample.
        summary["sample_plaquette"] = {"key": "1,1",
                                       "joints_first_5": plaq[(1, 1)][:5]}
    with out.open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
