#!/usr/bin/env python3
"""Compute color budgets C(c) and per-row expected quotas q*_r(c).

Then measure: in a known 460 board, do per-row color quotas deviate
from q* significantly?

Hypothesis: yes — and the deviation pattern explains the row-12 wall.
"""
import sys
import json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "v184_lighthouse"))
from build_bidirectional2 import load_pieces, BORDER

REPO = Path(__file__).resolve().parents[2]


def main():
    pieces = load_pieces()
    # 'pieces' is {(pid, rot): (n, e, s, w)} with 256 * 4 = 1024 entries.
    # Total color count = sum over all (pid, rot=0) of 4 edges.
    # Each piece has 4 edges (rot=0 representative); each edge color is fixed.

    # Get the unique pieces (rot=0).
    color_count = Counter()
    border_count = Counter()
    interior_count = Counter()
    for (pid, rot), (n, e, s, w) in pieces.items():
        if rot != 0:
            continue
        for c in (n, e, s, w):
            color_count[c] += 1
            if c == BORDER:
                border_count[c] += 1
            else:
                interior_count[c] += 1

    print(f"Total pieces: 256")
    print(f"Total color slots: {sum(color_count.values())} (= 256 × 4 = 1024)")
    print()
    print(f"BORDER color count: {color_count[BORDER]}")
    print(f"Interior colors: {len(interior_count)} colors")
    print()
    print("Color distribution (interior colors only, top 10):")
    for c, n in sorted(interior_count.items(), key=lambda x: -x[1])[:10]:
        # c is the color (a 16-char string).
        print(f"  color {c}: {n} slots")

    # H-edges in the 16x16 board: 15 horizontal seams × 16 columns = 240 H-edges.
    # Each H-edge consumes 2 color-slots (one from each adjacent piece).
    # So total H-edge color-slot consumption = 480.
    # V-edges: 16 rows × 15 vertical seams = 240, also 480 slots.
    # Border edges: 4 × 15 + 4 corners ish... let's just compute it.
    # Each piece contributes 4 colors. 4 corners contribute 2 BORDER, 2 interior;
    # 56 edges contribute 1 BORDER + 3 interior; 196 interior contribute 4 interior.
    # Total interior color slots = 256 × 4 - 4 × 2 - 56 × 1 = 1024 - 8 - 56 = 960.

    interior_total = sum(interior_count.values())
    print(f"\nInterior color total slots: {interior_total}")
    print(f"Expected H-edge color demand: 240 H-edges × 2 = 480 slots")
    print(f"Expected V-edge color demand: 240 V-edges × 2 = 480 slots")
    print(f"Total H+V interior demand: 960 slots (= interior_total, conservation OK)")

    # Per-row H-edge quota: each interior color gets ~half the supply for H-edges.
    # 15 H-edge rows. Per row interior columns (col 0..15, but col 0 and 15 are border-touching)
    # interior horizontal edges per row interior = 16 (cols 0..15 each contribute one S-edge).

    # For each color c, the H-edge supply for that color = interior_count[c] / 2
    # (half goes to H-edges, half to V-edges, by symmetry... ACTUALLY this isn't right;
    # the piece doesn't choose which of its 4 edges is H vs V — the placement and rotation do.)

    # Simpler measure: in a 460 board, count color usage per row's S-edge sequence.
    # Compare to uniform: each row uses ~480/15 = 32 slots, distributed across colors.

    board_path = REPO / 'output' / 'vol-181' / 'RECORD_460_NEW_BASIN_row_s42_cp0312.json'
    if board_path.exists():
        board = json.load(open(board_path))
        placement = board['placement']
        print(f"\nLoaded {board_path.name}: score {board.get('matched', '?')}")

        # Reconstruct placement[pos] = (pid, rot).
        pl = [None] * 256
        for ent in placement:
            if ent is not None:
                pl[ent['pos']] = (ent['piece_id'], ent['rotation'])

        # For each row r in 0..15, compute the multi-set of S-edge colors.
        # S-edge of cell at (r, c) is edges[2] when rotation applied.
        row_color_counts = [Counter() for _ in range(16)]
        for pos in range(256):
            if pl[pos] is None: continue
            pid, rot = pl[pos]
            edges = pieces[(pid, rot)]
            r = pos // 16
            row_color_counts[r][edges[2]] += 1  # S-edge

        # Print per-row distribution: # of distinct colors, sum non-border, top 3 colors.
        print(f"\nPer-row S-edge color distribution:")
        all_colors = set()
        for r in range(16):
            all_colors.update(row_color_counts[r].keys())
        all_colors = sorted(all_colors)
        # Compute per-color row distribution: each color how many in each row.
        per_color_per_row = {c: [row_color_counts[r].get(c, 0) for r in range(16)] for c in all_colors}

        # Variance per color across rows (excluding BORDER which is anchored to last row).
        print("\nColor row-quota variance (interior colors only):")
        variances = []
        for c in all_colors:
            if c == BORDER: continue
            counts = per_color_per_row[c][:15]  # rows 0..14 (S-edges = H-edges)
            if not counts or sum(counts) == 0: continue
            mean = sum(counts) / 15
            var = sum((x - mean) ** 2 for x in counts) / 15
            variances.append((var, mean, sum(counts), c, counts))
        variances.sort(reverse=True)
        print("Top-5 highest-variance interior colors:")
        for var, mean, total, c, counts in variances[:5]:
            print(f"  color {c}: total={total} mean={mean:.2f} var={var:.2f}")
            print(f"    row distribution: {counts}")

        # Hypothesis test: is row 12+ deficient in any color?
        print("\nRows 12-14 cumulative color usage vs expected:")
        for c in all_colors[:8]:
            if c == BORDER: continue
            row_counts = per_color_per_row[c][:15]
            if sum(row_counts) == 0: continue
            total = sum(row_counts)
            expected_per_row = total / 15
            bottom_3 = sum(row_counts[12:15])
            expected_bottom_3 = expected_per_row * 3
            ratio = bottom_3 / expected_bottom_3 if expected_bottom_3 > 0 else 0
            print(f"  color {c}: rows 12-14 used {bottom_3:.1f}, expected {expected_bottom_3:.1f}, ratio={ratio:.2f}")


if __name__ == '__main__':
    main()
