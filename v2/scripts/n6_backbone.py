#!/usr/bin/env python3
"""
N6: Cross-family backbone extraction.

Walk all saved JSON boards across output/*. For each one, extract the
placement (256 cells × (piece_id, rotation)) and matched_best/score.
Tally per-cell agreement across boards.

Cells where >=fraction of boards agree on identical (piece_id, rotation)
are the "backbone" — high-confidence cells we should pin as hints.

Outputs:
- Histogram of consensus fractions.
- List of consensus cells (per threshold).
- Backbone JSON file suitable as hint input.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path


def find_placement(d: dict) -> list[dict] | None:
    """Find a 256-cell placement in a JSON document. Handles multiple schemas."""
    if isinstance(d, dict):
        if "placement" in d and isinstance(d["placement"], list) and len(d["placement"]) > 0:
            first = d["placement"][0]
            if isinstance(first, dict) and ("piece_id" in first or "pid" in first) and "pos" in first:
                return d["placement"]
        if "best_placement" in d and isinstance(d["best_placement"], list):
            return d["best_placement"]
        if "board" in d and isinstance(d["board"], dict):
            inner = find_placement(d["board"])
            if inner:
                return inner
        if "best_board" in d:
            bb = d["best_board"]
            if isinstance(bb, dict):
                inner = find_placement(bb)
                if inner:
                    return inner
    return None


def find_score(d: dict) -> int | None:
    for k in ("matched_best", "best_score", "best_matched", "score", "matched"):
        v = d.get(k)
        if isinstance(v, int):
            return v
    return None


def normalize_cell(cell: dict) -> tuple[int, int, int] | None:
    """Return (pos, piece_id, rotation) or None."""
    pos = cell.get("pos")
    pid = cell.get("piece_id", cell.get("pid"))
    rot = cell.get("rotation", cell.get("rot"))
    if pos is None or pid is None or rot is None:
        return None
    return int(pos), int(pid), int(rot)


def load_boards(paths: list[Path], min_score: int):
    boards = []
    for p in paths:
        try:
            d = json.load(open(p))
        except Exception:
            continue
        placement = find_placement(d)
        if not placement:
            continue
        score = find_score(d)
        if score is None or score < min_score:
            continue
        cells = []
        for c in placement:
            n = normalize_cell(c)
            if n:
                cells.append(n)
        if len(cells) < 200:
            continue
        boards.append({"path": str(p), "score": score, "cells": cells})
    return boards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="output", help="Root dir to scan")
    parser.add_argument("--min-score", type=int, default=440, help="Minimum board score to include")
    parser.add_argument("--threshold", type=float, default=0.9, help="Consensus fraction for backbone")
    parser.add_argument("--out", default="output/n6_backbone/backbone.json", help="Output backbone file")
    parser.add_argument("--cells", type=int, default=256, help="Number of cells in the puzzle")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"ERROR: {root} not found", file=sys.stderr)
        return 2
    json_paths = sorted(root.rglob("*.json"))
    print(f"Scanning {len(json_paths)} JSON files under {root}/ for score >= {args.min_score} ...")

    boards = load_boards(json_paths, args.min_score)
    print(f"Loaded {len(boards)} boards with score >= {args.min_score}.")
    if not boards:
        print("No boards passed the filter. Aborting.")
        return 1

    # Stratify by score buckets.
    by_score: dict[int, int] = Counter(b["score"] for b in boards)
    print("Score histogram (board count):")
    for s in sorted(by_score, reverse=True):
        print(f"  {s}: {by_score[s]}")

    # Tally per-cell (piece_id, rotation).
    tally: dict[int, Counter] = defaultdict(Counter)
    for b in boards:
        for pos, pid, rot in b["cells"]:
            tally[pos][(pid, rot)] += 1

    total = len(boards)
    consensus = []  # list of (pos, frac, (pid, rot), n)
    for pos in range(args.cells):
        c = tally.get(pos)
        if not c:
            consensus.append((pos, 0.0, None, 0))
            continue
        (pid_rot, n) = c.most_common(1)[0]
        consensus.append((pos, n / total, pid_rot, n))

    fracs = [c[1] for c in consensus]
    # Histogram by 0.1 bucket.
    hist = Counter(min(int(f * 10), 9) for f in fracs)
    print(f"\nConsensus histogram across {total} boards (cells per 10% bucket):")
    for k in range(10):
        lo = k * 10
        hi = lo + 10
        bar = "#" * (hist.get(k, 0))
        print(f"  [{lo:3d}–{hi:3d}%): {hist.get(k, 0):3d}  {bar}")

    # Backbone at threshold.
    backbone = [(pos, pid_rot, n) for (pos, frac, pid_rot, n) in consensus if frac >= args.threshold and pid_rot is not None]
    print(f"\nBackbone at frac >= {args.threshold}: {len(backbone)} / {args.cells} cells")

    # Cross-family: split boards by source dir.
    by_family: dict[str, list] = defaultdict(list)
    for b in boards:
        parts = Path(b["path"]).parts
        if "v17_alns_pt" in parts:
            fam = "alns_pt"
        elif "v17_alns_portfolio" in parts:
            fam = "alns_portfolio"
        elif "v17_alns_only" in parts:
            fam = "alns_only"
        elif "border_diversity_v7" in parts:
            fam = "border_diversity"
        elif any("chunk_" in p for p in parts):
            fam = next(p for p in parts if "chunk_" in p)
        else:
            fam = "other"
        by_family[fam].append(b)
    print("\nBoards by family:")
    for f, blist in sorted(by_family.items()):
        ss = Counter(b["score"] for b in blist)
        top = sorted(ss.items(), reverse=True)[:3]
        print(f"  {f}: {len(blist)} boards, top scores: {top}")

    # Cross-family backbone: cell must have same (pid, rot) majority in EACH family.
    cross_consensus = []
    families = [f for f, blist in by_family.items() if len(blist) >= 3]
    print(f"\nFamilies with >=3 boards used for cross-family backbone: {families}")
    if len(families) >= 2:
        per_fam_top: dict[str, dict[int, tuple]] = {}
        for f in families:
            tally_f: dict[int, Counter] = defaultdict(Counter)
            for b in by_family[f]:
                for pos, pid, rot in b["cells"]:
                    tally_f[pos][(pid, rot)] += 1
            top_f = {}
            for pos in range(args.cells):
                c = tally_f.get(pos)
                if c:
                    top_f[pos] = c.most_common(1)[0]
            per_fam_top[f] = top_f
        for pos in range(args.cells):
            tops = [per_fam_top[f].get(pos) for f in families]
            if any(t is None for t in tops):
                continue
            # Check all families agree on top (pid, rot).
            pid_rots = {t[0] for t in tops}
            if len(pid_rots) == 1:
                pid_rot = next(iter(pid_rots))
                min_count = min(t[1] for t in tops)
                cross_consensus.append((pos, pid_rot, min_count))
        print(f"Cross-family backbone (all families' top agree): {len(cross_consensus)} cells")

    # Per-cell entropy + second-mode analysis.
    print("\nPer-cell mode analysis (top + second-top assignments, top entropy):")
    entropies = []
    for pos in range(args.cells):
        c = tally.get(pos)
        if not c:
            continue
        items = c.most_common()
        top_n = items[0][1]
        second_n = items[1][1] if len(items) > 1 else 0
        # Effective entropy (Shannon over assignments).
        import math
        h = 0.0
        for _, n in items:
            p = n / total
            if p > 0:
                h -= p * math.log2(p)
        entropies.append((pos, h, top_n, second_n, len(items)))

    # Cells with EXACTLY two strong modes (top ~60%, second ~30-40%): bimodal lock.
    bimodal = [t for t in entropies if t[2] / total >= 0.5 and t[3] / total >= 0.2 and t[4] <= 4]
    print(f"\nBimodal cells (top >= 50%, second >= 20%, <= 4 distinct values): {len(bimodal)}")
    for pos, h, n1, n2, k in sorted(bimodal, key=lambda x: -x[2])[:20]:
        row, col = pos // 16, pos % 16
        items = tally[pos].most_common(2)
        print(f"  ({row:2d},{col:2d}) pos={pos:3d}  top={items[0][0]} n={n1}  2nd={items[1][0]} n={n2}  H={h:.2f} k={k}")

    # High-entropy cells: many assignments seen, no clear winner.
    high_h = sorted(entropies, key=lambda x: -x[1])[:20]
    print(f"\nTop-20 highest-entropy cells:")
    for pos, h, n1, n2, k in high_h:
        row, col = pos // 16, pos % 16
        print(f"  ({row:2d},{col:2d}) pos={pos:3d}  H={h:.2f}  top={n1}/{total}  2nd={n2}/{total}  k={k}")

    # Save backbone JSON.
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_data = {
        "n_boards": total,
        "min_score": args.min_score,
        "threshold": args.threshold,
        "score_histogram": dict(by_score),
        "backbone": [
            {"pos": pos, "piece_id": pid_rot[0], "rotation": pid_rot[1], "n_agree": n}
            for (pos, pid_rot, n) in backbone
        ],
        "cross_family_backbone": [
            {"pos": pos, "piece_id": pid_rot[0], "rotation": pid_rot[1], "n_agree_min": n}
            for (pos, pid_rot, n) in cross_consensus
        ],
        "families": {f: [b["path"] for b in blist] for f, blist in by_family.items()},
    }
    with open(out_path, "w") as f:
        json.dump(out_data, f, indent=2)
    print(f"\nWrote backbone to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
