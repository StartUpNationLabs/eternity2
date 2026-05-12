#!/usr/bin/env python3
"""Verify the NS-1 multiset-equality invariant on real boards.

Statement (Hopfer 2022): "the multiset of inward-facing colors across
the 56 border-edge pieces must equal the multiset of inward-facing
colors on the 56 14×14-perimeter interior pieces."

We compute both multisets on:
1. Both 470 boards (Blackwood 2021, Bucas variant) from the community
   corpus — should be EQUAL on a verified full solution.
2. Lower-score boards (some 469s, 465, 421, etc.) — also should
   match for the 14×14 substructure if borders are correctly closed.
3. Vol-6 record 454 board — should match for placed cells.

If the equality holds on all verified high-score boards, NS-1 is a
valid invariant. If not, the propagator statement is wrong.
"""
from __future__ import annotations

import sys
import json
import re
from pathlib import Path
from collections import Counter
from typing import List, Tuple

ROOT = Path(__file__).resolve().parents[1]

# Bucas decoding: each cell is 4 chars (N, E, S, W); ord('a')-ord('a')=0=BORDER.
W = H = 16
BORDER = 0


def decode_url(url: str) -> List[Tuple[int, int, int, int]]:
    """Return list of 256 (N, E, S, W) tuples."""
    m = re.search(r"board_edges=([a-z]+)", url)
    if not m:
        return []
    blob = m.group(1)
    if len(blob) < 16 * 16 * 4:
        return []
    quads = []
    for pos in range(16 * 16):
        chunk = blob[pos * 4:pos * 4 + 4]
        quads.append(tuple(ord(c) - ord('a') for c in chunk))
    return quads


def cell_class(pos):
    x, y = pos % W, pos // W
    on_t = (y == 0); on_b = (y == H - 1)
    on_l = (x == 0); on_r = (x == W - 1)
    nb = int(on_t) + int(on_b) + int(on_l) + int(on_r)
    return ("corner", "edge", "interior")[(0 if nb == 2 else (1 if nb == 1 else 2))]


def border_facing_colors(quads):
    """For each 14×14-perimeter interior cell, return the color on its
    side that faces the outer border ring.

    Returns dict pos -> color.
    """
    out = {}
    for pos in range(W * H):
        x, y = pos % W, pos // W
        # 14×14 perimeter: x ∈ {1, 14} or y ∈ {1, 14}, and NOT a border cell
        if cell_class(pos) != "interior":
            continue
        on_outer_ring = (x == 1) or (x == W - 2) or (y == 1) or (y == H - 2)
        if not on_outer_ring:
            continue
        n, e, s, w = quads[pos]
        # which side faces the border ring?
        # If y==1, north faces border (pos with y=0)
        # If y==H-2, south
        # If x==1, west
        # If x==W-2, east
        outer = []
        if y == 1: outer.append(("N", n))
        if y == H - 2: outer.append(("S", s))
        if x == 1: outer.append(("W", w))
        if x == W - 2: outer.append(("E", e))
        # Corner-of-14×14 cells (x,y both at extreme) face TWO border sides
        for tag, c in outer:
            out[(pos, tag)] = c
    return out


def edge_piece_inward_colors(quads):
    """For each edge-class border-ring cell, return the color on the
    side that faces the interior (the inward side).

    Returns dict pos -> color.
    """
    out = {}
    for pos in range(W * H):
        if cell_class(pos) != "edge":
            continue
        x, y = pos % W, pos // W
        n, e, s, w = quads[pos]
        # which side faces interior?
        # top row (y==0): south side faces interior
        # bottom row (y==H-1): north faces interior
        # left col (x==0): east faces interior
        # right col (x==W-1): west faces interior
        if y == 0: out[pos] = s
        elif y == H - 1: out[pos] = n
        elif x == 0: out[pos] = e
        elif x == W - 1: out[pos] = w
    return out


def corner_facing(quads):
    """For each corner cell, the two interior-facing colors.

    A corner has 2 ring-internal sides (one north/south + one east/west);
    they face an adjacent border-edge cell, not the interior. So corners
    contribute zero to "border ring's inward-facing toward interior" tally.
    """
    return {}


def check_board(quads):
    """Compute the two multisets and report match."""
    # Multiset A: inward-facing colors of the 56 edge-class border pieces.
    # (corners contribute zero — they face adjacent border pieces only)
    edge_inward = edge_piece_inward_colors(quads)
    A = Counter(edge_inward.values())

    # Multiset B: border-facing colors of 14×14-perimeter interior pieces.
    bf = border_facing_colors(quads)
    B = Counter(bf.values())

    return A, B, edge_inward, bf


def main():
    corpus_dir = ROOT / "output" / "community_corpus"
    boards = sorted(corpus_dir.glob("*.json"))
    boards = [b for b in boards if b.name != "_index.tsv"]

    print(f"Verifying NS-1 multiset equality on {len(boards)} corpus boards")
    print()
    results = []
    for bf in boards:
        try:
            data = json.loads(bf.read_text())
        except Exception:
            continue
        url = data.get("url", "")
        score = data.get("interior_matched", 0)
        quads = decode_url(url)
        if len(quads) != 256:
            continue
        A, B, _, _ = check_board(quads)
        equal = (A == B)
        results.append((score, equal, A, B, bf.name))

    # Sort by score descending
    results.sort(key=lambda r: -r[0])

    # Print top scores first
    n_eq = sum(1 for _, eq, *_ in results if eq)
    n_neq = sum(1 for _, eq, *_ in results if not eq)
    print(f"Match counts: equal={n_eq} not_equal={n_neq}")
    print()
    print("Top boards (by interior_matched):")
    print(f"{'score':>5} {'match?':>6} {'name'}")
    for score, eq, A, B, name in results[:20]:
        print(f"  {score:>3}  {'✓' if eq else '✗':>4}  {name}")

    # Detail for top 470s
    print()
    print("Multisets for the 470 board:")
    for score, eq, A, B, name in results:
        if score == 470:
            print(f"  {name}:")
            print(f"    A (edge-piece inward) = {dict(sorted(A.items()))}")
            print(f"    B (14×14 outer ring)  = {dict(sorted(B.items()))}")
            # Sizes
            print(f"    sizes: |A|={sum(A.values())} |B|={sum(B.values())}")
            print(f"    A-B diff: {dict({k: A.get(k,0) - B.get(k,0) for k in set(A)|set(B) if A.get(k,0)!=B.get(k,0)})}")
            break

    # Save
    OUT = ROOT / "output" / "v11_sp" / "ns1_verification.json"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "schema_version": 1,
        "total_boards_checked": len(results),
        "n_equal": n_eq,
        "n_not_equal": n_neq,
        "per_board": [
            {"name": name, "score": score, "match": eq,
             "A": dict(A), "B": dict(B)}
            for score, eq, A, B, name in results
        ],
    }
    with OUT.open("w") as f:
        json.dump(out, f, indent=2)
    print()
    print(f"Saved {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
