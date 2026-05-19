#!/usr/bin/env python3
"""V129-T8 — Interior-only trap analysis.

The trap-pieces analysis (V129-T5) showed traps are mostly on the BORDER.
Now: filter to INTERIOR positions only. Are there interior trap-pieces
strong enough to use as pinning targets?

Interior positions: 2 ≤ row ≤ 13 AND 2 ≤ col ≤ 13 (skip 2 layers).
"""

from __future__ import annotations
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
W = 16


def is_interior(pos):
    r, c = pos // W, pos % W
    return 2 <= r <= 13 and 2 <= c <= 13


def main():
    res = json.load(open(REPO / "output/vol-129/trap_pieces_per_position/result.json"))
    HINTS = {34, 45, 135, 210, 221}

    print(f"Interior positions: {sum(1 for p in range(256) if is_interior(p))} cells", flush=True)

    # Per interior position, top trap and escape pieces.
    interior_results = []
    for pos_str, traps in res["trap_pieces"].items():
        pos = int(pos_str)
        if not is_interior(pos): continue
        if pos in HINTS: continue
        escapes = res["escape_pieces"].get(pos_str, [])
        if not traps or not escapes: continue
        top_trap = traps[0]
        top_esc = escapes[0]
        if top_trap[:2] == top_esc[:2]: continue  # same → no escape signal
        interior_results.append((pos, top_trap, top_esc))

    interior_results.sort(key=lambda x: -x[1][2])  # by trap count
    print(f"Interior positions with TRAP ≠ ESCAPE: {len(interior_results)}", flush=True)

    print(f"\nTop 30 (sorted by trap count):", flush=True)
    print(f"{'pos':>4} {'r,c':>5}  TRAP            ESCAPE", flush=True)
    for pos, top_trap, top_esc in interior_results[:30]:
        r, c = pos // W, pos % W
        print(f"{pos:>4} ({r:>2d},{c:>2d})  p={top_trap[0]:>3d}r{top_trap[1]} cnt={top_trap[2]:>3d}    p={top_esc[0]:>3d}r{top_esc[1]} cnt={top_esc[2]:>3d}", flush=True)

    # Save the interior-only escape overlay for use in attack.
    out = {
        "interior_escape_targets": [
            {"pos": p, "trap_piece": list(t[:2]), "trap_count": t[2],
             "escape_piece": list(e[:2]), "escape_count": e[2]}
            for p, t, e in interior_results[:100]
        ]
    }
    out_path = REPO / "output/vol-129/trap_pieces_per_position/interior_only.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
