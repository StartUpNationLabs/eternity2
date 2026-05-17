#!/usr/bin/env python3
"""Vol-122 K2 — Soft-Lock then Recompute (SLR) PoC.

NEW INVENTION: take a best-so-far board (e.g., m=447 from ALNS). For each
cell, compute LOCAL MATCH SCORE = # of its 4 adjacent edges that match
neighbors (ignoring border-side which is always matched for border cells).

Identify HIGH-QUALITY cells (local-match = 4/4, fully matched). LOCK
those. UNLOCK the rest. Run CSP-fill from the locked-pinned state with
the unused pieces. The hope: locked cells anchor good structure; CSP
exhaustively searches the unlocked space.

This differs from standard ALNS destroy because:
- Destroy is random; SLR is quality-filtered.
- Destroy + repair operates within ALNS's local search; SLR uses full
  CSP search on the unlocked cells.
- Could find globally better arrangements within the unlocked region.

We compute the lock set, save as a partial, then can feed to
border_to_csp_fill --random-fill-remaining for CSP exploration.

Outputs a partial JSON that represents the LOCKED CELLS only.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v


def load_pieces():
    pieces = {}
    with open("../data/puzzles/size_16_official_eternity.csv") as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces[pid] = tuple(parse_color(cols[i]) for i in range(4))
                pid += 1
            except ValueError: pass
    return pieces


def rotate(edges, rot):
    return tuple(edges[(i - rot) % 4] for i in range(4))


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} BOARD.json OUT_LOCKED.json [MIN_MATCH=4]")
        sys.exit(1)

    board_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    min_match = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    pieces = load_pieces()
    side = 16

    with open(board_path) as f:
        d = json.load(f)
    # Extract placements (handle both list-of-dict and indexed forms)
    placed = {}
    placements = d.get('placement', [])
    for entry in placements:
        if entry is None: continue
        pos = entry.get('pos')
        if pos is not None:
            placed[pos] = (entry['piece_id'], entry['rotation'])
    print(f"loaded board: {len(placed)} placed cells")

    # Compute per-cell local match score
    cell_scores = {}
    for pos, (pid, rot) in placed.items():
        r, c = pos // side, pos % side
        my_edges = rotate(pieces[pid], rot)
        T, R, B, L = my_edges
        score = 0
        # 4 sides: count matches with neighbors
        for (dr, dc, my_side, their_side) in [
            (-1, 0, 0, 2), (0, 1, 1, 3), (1, 0, 2, 0), (0, -1, 3, 1)
        ]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < side and 0 <= nc < side:
                npos = nr * side + nc
                if npos in placed:
                    npid, nrot = placed[npos]
                    nedges = rotate(pieces[npid], nrot)
                    my_color = my_edges[my_side]
                    their_color = nedges[their_side]
                    if my_color == their_color and my_color != 0:
                        score += 1
            else:
                # Boundary — if border color, count as match
                if my_edges[my_side] == 0:
                    score += 1
        cell_scores[pos] = score

    # Print distribution
    from collections import Counter
    dist = Counter(cell_scores.values())
    print("Score distribution (cells with N matched sides):")
    for k in sorted(dist):
        print(f"  {k}/4 matched: {dist[k]:3d} cells ({100*dist[k]/len(placed):.1f}%)")

    # Compute how many edges this scoring matches
    # Each edge is counted twice (once per cell), so total matched edges = sum(score) / 2 + border
    sum_scores = sum(cell_scores.values())
    print(f"\nSum of cell scores: {sum_scores}")
    print(f"Implied matched edges: {sum_scores // 2}")

    # Lock cells with score >= min_match
    locked = {pos: v for pos, v in placed.items() if cell_scores[pos] >= min_match}
    print(f"\nLOCKED cells (score >= {min_match}/4): {len(locked)}/{len(placed)}")

    # Save as partial JSON (only locked cells placed)
    out_placement = []
    for pos, (pid, rot) in locked.items():
        out_placement.append({"pos": pos, "piece_id": pid, "rotation": rot})
    out_doc = {
        "source": f"vol122_slr from {board_path.name} (min_match={min_match})",
        "n_locked": len(locked),
        "n_total_input": len(placed),
        "placement": out_placement,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(out_doc, f, indent=2)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
