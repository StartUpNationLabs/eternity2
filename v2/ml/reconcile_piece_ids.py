"""Vol-34 T2 — build piece_id ↔ card_id + rotation map between our v2 engine
and capiman/e2.

Prereq: ml/data/color_map.json (built by reconcile_unsat_encoding_v2.py).

For each our piece, find the capiman card and the capiman rotation it
matches in canonical orientation. The cap_rot value tells the unsat
propagator which (field, card, cap_rot) literal to look up.

Output: ml/data/piece_card_map.json
  {
    "our_pid_to_cap_card": {pid: card, ...}
    "cap_rot_for_our_rot": {pid: [r0, r1, r2, r3]}
       # cap_rot value (1..4) to use when our_rot=k
  }
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path


def parse_our_csv(path: str):
    with open(path) as f:
        lines = [l.rstrip() for l in f if l.strip()]
    n = int(lines[0]) ** 2
    pieces = []
    for line in lines[1 : n + 1]:
        cols = line.split(",")
        edges = []
        for col in cols[:4]:
            v = int(col, 2)
            edges.append(0 if v == 65535 else v)
        pieces.append(tuple(edges))
    return pieces


def parse_capiman_all_rotations(path: str):
    pat = re.compile(
        r"^\s*\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}"
    )
    by_card = defaultdict(dict)
    with open(path) as f:
        for line in f:
            m = pat.match(line)
            if not m:
                continue
            _, _, card, rot, pn, pe, ps, pw = [int(x) for x in m.groups()]
            by_card[card][rot] = (pn, pe, ps, pw)
    return dict(by_card)


def rotate_tuple(t, k):
    """Apply our rotation convention: R<k> sends (t,r,b,l) -> shifted by k.

    Our `rotated(R<k>)` in piece.rs:
      k=0: (t, r, b, l)
      k=1: (l, t, r, b)     # last → first
      k=2: (b, l, t, r)
      k=3: (r, b, l, t)     # first → last
    """
    if k == 0:
        return t
    if k == 1:
        return (t[3], t[0], t[1], t[2])
    if k == 2:
        return (t[2], t[3], t[0], t[1])
    if k == 3:
        return (t[1], t[2], t[3], t[0])
    raise ValueError(k)


def main():
    color_map = {
        int(k): v for k, v in json.load(open("ml/data/color_map.json"))["our_to_capiman"].items()
    }
    our = parse_our_csv("../data/puzzles/size_16_official_eternity.csv")
    cap_by_card = parse_capiman_all_rotations("output/capiman_e2/e2_info.c")
    print(f"[ours] {len(our)} pieces; [capiman] {len(cap_by_card)} cards")

    # Index: (canonical color tuple) -> (card, capiman_rot_value)
    edge_tuple_to_card_rot = {}
    for card, rots in cap_by_card.items():
        for rot_val, tpl in rots.items():
            if tpl in edge_tuple_to_card_rot:
                pass  # acceptable if rotational symmetry → multiple roles
            edge_tuple_to_card_rot[tpl] = (card, rot_val)

    our_pid_to_card = {}
    cap_rot_for_our_rot = {}
    unmatched = []

    for pid, edges in enumerate(our):
        relabeled = tuple(color_map[c] for c in edges)  # our edges in CAPIMAN colors
        # For each of our 4 rotations, compute the rotated tuple and find
        # the corresponding capiman (card, cap_rot).
        cap_rots = [None, None, None, None]
        card_found = None
        for our_rot in range(4):
            rotated = rotate_tuple(relabeled, our_rot)
            hit = edge_tuple_to_card_rot.get(rotated)
            if hit is None:
                continue
            card, cap_rot = hit
            if card_found is None:
                card_found = card
            elif card_found != card:
                print(f"[warn] pid {pid} maps to multiple cards: {card_found}, {card}")
            cap_rots[our_rot] = cap_rot
        if card_found is None:
            unmatched.append((pid, edges, relabeled))
            continue
        our_pid_to_card[pid] = card_found
        cap_rot_for_our_rot[pid] = cap_rots

    print(f"[match] {len(our_pid_to_card)}/{len(our)} pieces matched")
    if unmatched:
        print(f"[unmatched] {len(unmatched)}: {unmatched[:2]}")

    # Verify bijection.
    cards_used = set(our_pid_to_card.values())
    print(f"[bijection] {len(cards_used)} distinct cards used (expect {len(our)})")

    # Quick sanity on pid 0 → card 1 mapping:
    if 0 in our_pid_to_card:
        print(f"[sanity] pid 0 → card {our_pid_to_card[0]}, cap_rot per our_rot: {cap_rot_for_our_rot[0]}")

    Path("ml/data").mkdir(exist_ok=True)
    with open("ml/data/piece_card_map.json", "w") as f:
        json.dump(
            {
                "our_pid_to_cap_card": {
                    str(p): c for p, c in sorted(our_pid_to_card.items())
                },
                "cap_rot_for_our_rot": {
                    str(p): rs for p, rs in sorted(cap_rot_for_our_rot.items())
                },
            },
            f,
            indent=2,
        )
    print("[out] ml/data/piece_card_map.json")


if __name__ == "__main__":
    main()
