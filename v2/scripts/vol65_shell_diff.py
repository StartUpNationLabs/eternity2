#!/usr/bin/env python3
"""Vol-65 — Per-shell piece-placement diff between local-459 and McGavin-469.

For each shell-distance k:
- How many cells differ between our 459 and McGavin's 469?
- Of these diffs, how many are at the SAME piece-position
  (just rotation difference) vs DIFFERENT piece?

This identifies the "structural disagreement zone" by shell.
"""

import json


def load(p):
    with open(p) as f:
        d = json.load(f)
    arr = d.get("placement", [])
    pos_to = {}
    for idx, item in enumerate(arr):
        if item is None: continue
        pos = item.get("pos", idx)
        pid = item["piece_id"]
        rot = item["rotation"]
        pos_to[pos] = (pid, rot)
    return pos_to


def shell_distance(pos):
    r, c = divmod(pos, 16)
    return min(r, 15 - r, c, 15 - c)


def main():
    cur = load("output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json")
    orc = load("output/vol-65/mcgavin_469.json")

    by_shell = {k: {"total": 0, "match": 0, "rot_only": 0, "piece_diff": 0}
                for k in range(8)}

    for pos in range(256):
        k = shell_distance(pos)
        by_shell[k]["total"] += 1
        cur_pr = cur.get(pos)
        orc_pr = orc.get(pos)
        if cur_pr is None or orc_pr is None:
            continue
        if cur_pr == orc_pr:
            by_shell[k]["match"] += 1
        elif cur_pr[0] == orc_pr[0]:
            by_shell[k]["rot_only"] += 1
        else:
            by_shell[k]["piece_diff"] += 1

    print(f"{'shell':>5} | {'total':>5} | {'same':>5} | {'rot_only':>8} | {'piece_diff':>10}")
    for k in range(8):
        b = by_shell[k]
        if b["total"] == 0: continue
        print(f"{k:>5} | {b['total']:>5} | {b['match']:>5} | {b['rot_only']:>8} | {b['piece_diff']:>10}")
    total_match = sum(b["match"] for b in by_shell.values())
    total_rot = sum(b["rot_only"] for b in by_shell.values())
    total_piece = sum(b["piece_diff"] for b in by_shell.values())
    print(f"\nTOTAL: same={total_match} rot_only={total_rot} piece_diff={total_piece}")

    print()
    print("Cells where SAME piece is placed but different rotation:")
    rot_cells = [(pos, cur[pos], orc[pos]) for pos in cur
                 if pos in orc and cur[pos][0] == orc[pos][0]
                 and cur[pos][1] != orc[pos][1]]
    print(f"  count: {len(rot_cells)}")
    for pos, c, o in sorted(rot_cells, key=lambda t: shell_distance(t[0]))[:10]:
        x, y = pos % 16, pos // 16
        print(f"  pos={pos} ({x},{y}) shell={shell_distance(pos)}: piece {c[0]} cur_rot={c[1]} orc_rot={o[1]}")


if __name__ == "__main__":
    main()
