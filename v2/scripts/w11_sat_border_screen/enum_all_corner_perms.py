#!/usr/bin/env python3
"""Vol-124 W11: enumerate border-DP partials for ALL 24 corner permutations.

Builds on scripts/vol122_inv3_border_to_partial.py — that script dumps only
the first --max-borders=5 globally. Here we enumerate all 24 corner-perms,
and for EACH dump up to --max-per-perm chain solutions.

Output: output/vol-124/border_partials/perm{i}_b{j}.json (60-cell placement
files compatible with W11 screen_bulk.py).

Then run screen_bulk.py to SAT-filter each.
"""

from __future__ import annotations
import json
import sys
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vol122_inv3_border_to_partial import (
    load_puzzle, classify, corner_rots, side_options, enumerate_chains, rotate
)

W = 16


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle",
                    default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--out-dir",
                    default="output/vol-124/border_partials")
    ap.add_argument("--max-per-perm", type=int, default=5,
                    help="up to N borders per corner permutation")
    ap.add_argument("--max-chains-per-side", type=int, default=3,
                    help="diversify by exploring multiple chain solutions per side")
    args = ap.parse_args()

    pieces = load_puzzle(Path(args.puzzle))
    corners, edges, interiors = classify(pieces)
    sides_opt = {s: side_options(pieces, edges, s) for s in 'TRBL'}

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    perm_stats = []

    for perm_i, (tl, tr, br, bl) in enumerate(permutations(corners)):
        n_for_perm = 0
        tl_rs = corner_rots(pieces, tl, 'TL')
        tr_rs = corner_rots(pieces, tr, 'TR')
        bl_rs = corner_rots(pieces, bl, 'BL')
        br_rs = corner_rots(pieces, br, 'BR')
        if not (tl_rs and tr_rs and bl_rs and br_rs):
            perm_stats.append((perm_i, 0, "no_corner_rots"))
            continue

        for tl_r in tl_rs:
            if n_for_perm >= args.max_per_perm: break
            te = rotate(pieces[tl], tl_r)
            for tr_r in tr_rs:
                if n_for_perm >= args.max_per_perm: break
                tre = rotate(pieces[tr], tr_r)
                for br_r in br_rs:
                    if n_for_perm >= args.max_per_perm: break
                    bre = rotate(pieces[br], br_r)
                    for bl_r in bl_rs:
                        if n_for_perm >= args.max_per_perm: break
                        ble = rotate(pieces[bl], bl_r)

                        # For each corner-rotation 4-tuple, find up to K diverse chain solutions
                        c1s = enumerate_chains(te[1], tre[3], sides_opt['T'], set(),
                                                max_results=args.max_chains_per_side)
                        if not c1s: continue
                        for chain1 in c1s:
                            if n_for_perm >= args.max_per_perm: break
                            used1 = {pid for (pid,_,_) in chain1}
                            c2s = enumerate_chains(tre[2], bre[0], sides_opt['R'], used1,
                                                    max_results=1)
                            if not c2s: continue
                            chain2 = c2s[0]
                            used2 = used1 | {pid for (pid,_,_) in chain2}
                            c3s = enumerate_chains(bre[3], ble[1], sides_opt['B'], used2,
                                                    max_results=1)
                            if not c3s: continue
                            chain3 = c3s[0]
                            used3 = used2 | {pid for (pid,_,_) in chain3}
                            c4s = enumerate_chains(ble[0], te[2], sides_opt['L'], used3,
                                                    max_results=1)
                            if not c4s: continue
                            chain4 = c4s[0]

                            placement = []
                            placement.append({"pos": 0,   "piece_id": tl, "rotation": tl_r})
                            placement.append({"pos": 15,  "piece_id": tr, "rotation": tr_r})
                            placement.append({"pos": 255, "piece_id": br, "rotation": br_r})
                            placement.append({"pos": 240, "piece_id": bl, "rotation": bl_r})
                            for i, (pid, r, _) in enumerate(chain1):
                                placement.append({"pos": 1 + i, "piece_id": pid, "rotation": r})
                            for i, (pid, r, _) in enumerate(chain2):
                                placement.append({"pos": 15 + W*(i+1), "piece_id": pid, "rotation": r})
                            for i, (pid, r, _) in enumerate(chain3):
                                placement.append({"pos": 254 - i, "piece_id": pid, "rotation": r})
                            for i, (pid, r, _) in enumerate(chain4):
                                placement.append({"pos": 224 - W*i, "piece_id": pid, "rotation": r})
                            placement.sort(key=lambda p: p["pos"])
                            assert len(set(p["pos"] for p in placement)) == 60

                            out_path = out_dir / f"perm{perm_i:02d}_b{n_for_perm}.json"
                            doc = {
                                "placement": placement,
                                "metadata": {
                                    "source": "vol124_w11_enum_all_corner_perms",
                                    "corner_perm_idx": perm_i,
                                    "corners": [tl, tr, br, bl],
                                    "corner_rots": [tl_r, tr_r, br_r, bl_r],
                                    "border_matched": 60,
                                }
                            }
                            out_path.write_text(json.dumps(doc, indent=2))
                            n_for_perm += 1
                            total += 1

        perm_stats.append((perm_i, n_for_perm,
                           "ok" if n_for_perm > 0 else "no_chain_solution"))
        print(f"perm{perm_i:02d}: {n_for_perm} borders", file=sys.stderr)

    summary = {
        "total_borders": total,
        "perm_stats": [{"perm": p, "n_borders": n, "note": s}
                        for (p, n, s) in perm_stats],
    }
    (out_dir / "_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n# total: {total} border partials across "
          f"{sum(1 for _,n,_ in perm_stats if n>0)} valid corner perms")


if __name__ == "__main__":
    main()
