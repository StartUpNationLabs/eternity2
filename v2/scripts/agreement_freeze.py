#!/usr/bin/env python3
"""AGREEMENT-FREEZING — find consensus (piece, rotation) across high-score boards.

Per memory, multiple basins agree on certain cells. The "backbone" of cells
where N>=K boards agree is the voted-correct skeleton. Freeze it, see how
many cells get fixed, and check if the remaining sub-problem is tractable.

Specifically:
1. Take all 1278 DB boards (or top-K by score).
2. For each cell, count the most-common (piece, rotation) and its frequency.
3. Report agreement distribution.
4. Cells with very high agreement (>= 80% of boards) are "consensus backbone".
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
DB = REPO / "database-400-480"

def load_board(path):
    with open(path) as f: d = json.load(f)
    pl = d.get("placement", [])
    if not pl: return None, 0
    out = {}
    for i, p in enumerate(pl):
        if not isinstance(p, dict): continue
        pos = p.get("pos", i)
        if "piece_id" not in p or "rotation" not in p: return None, 0
        out[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
    return out, d.get("matched", 0)


def main():
    # Load all boards by score band.
    boards_by_band = defaultdict(list)
    for f in sorted(DB.glob("*.json")):
        if f.name == "README.md": continue
        b, s = load_board(f)
        if b is None or len(b) != 256: continue
        boards_by_band[s].append((f.name, b))

    print(f"Loaded boards by score band:")
    for sc in sorted(boards_by_band.keys(), reverse=True)[:15]:
        print(f"  {sc}: {len(boards_by_band[sc])}")
    total = sum(len(v) for v in boards_by_band.values())
    print(f"Total complete boards: {total}", flush=True)

    # Look at TOP score bands only — the most constrained boards.
    targets = [469, 466, 465, 462, 461]
    selected = []
    for sc in targets:
        selected.extend(boards_by_band.get(sc, []))
    print(f"\nSelected high-score boards: {len(selected)}", flush=True)

    # Per-cell vote.
    cell_votes = defaultdict(Counter)
    for name, board in selected:
        for pos, (pid, rot) in board.items():
            cell_votes[pos][(pid, rot)] += 1

    # Per-cell agreement: top vote count / total voters.
    print(f"\n=== Cell agreement levels ===", flush=True)
    agreement_levels = []
    for pos in range(256):
        if pos not in cell_votes: continue
        votes = cell_votes[pos]
        total_votes = sum(votes.values())
        top_choice, top_count = votes.most_common(1)[0]
        agree_pct = top_count / total_votes * 100
        agreement_levels.append((agree_pct, pos, top_choice, top_count, total_votes))

    agreement_levels.sort(reverse=True)
    print(f"Cells with most agreement:", flush=True)
    for ag, pos, choice, cnt, total in agreement_levels[:20]:
        row, col = pos // 16, pos % 16
        print(f"  pos={pos:3d} ({row:2d},{col:2d}): agreement={ag:.1f}% ({cnt}/{total} boards agree on {choice})", flush=True)

    # Histogram of agreement levels.
    buckets = [0, 50, 60, 70, 80, 90, 95, 100, 101]
    hist = [0] * (len(buckets) - 1)
    for ag, *_ in agreement_levels:
        for i in range(len(buckets) - 1):
            if buckets[i] <= ag < buckets[i+1]:
                hist[i] += 1; break
    print(f"\nAgreement histogram:")
    for i in range(len(buckets) - 1):
        print(f"  [{buckets[i]:>3}-{buckets[i+1]:>3}%): {hist[i]} cells")

    # Backbone at different thresholds.
    print(f"\n=== Consensus backbone by threshold ===")
    for thresh in [50, 60, 70, 80, 90, 95]:
        bb = [(pos, choice, cnt) for ag, pos, choice, cnt, total in agreement_levels if ag >= thresh]
        print(f"  threshold {thresh}%: {len(bb)}/256 cells")

    # Save the 80% consensus backbone.
    consensus_path = REPO / "output" / "vol-125" / "agreement_backbone.json"
    backbone = {pos: choice for ag, pos, choice, cnt, total in agreement_levels if ag >= 80}
    out_data = {
        "threshold_pct": 80,
        "n_voters": len(selected),
        "score_bands_used": targets,
        "backbone_cells": [
            {"pos": pos, "piece_id": pid, "rotation": rot}
            for pos, (pid, rot) in sorted(backbone.items())
        ],
    }
    consensus_path.write_text(json.dumps(out_data, indent=2))
    print(f"\nSaved 80%-consensus backbone ({len(backbone)} cells) to {consensus_path}", flush=True)


if __name__ == "__main__":
    main()
