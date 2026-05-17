#!/usr/bin/env python3
"""Vol-122 A1 — enumerate borders specifically for the McGavin corner permutation (3,2,0,1).

The previous enumeration (SAMPLE_CAP=50) only got borders with corner TL=0.
McGavin's corner perm is (TL=3, TR=2, BR=0, BL=1) — uncovered.

Strategy:
1. Iterate (tl=3, tr=2, br=0, bl=1) configurations.
2. For each (tl_r, tr_r, br_r, bl_r), search 60-matched borders.
3. Save the first N as JSON partials.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

# Import functions from sister script
sys.path.insert(0, str(Path(__file__).parent))
from vol122_inv3_enumerate_unique_borders import (
    load_puzzle, classify, side_options, rotate, corner_rots, enumerate_chains
)


def main():
    out_dir = Path("output/vol-122/mcgavin_perm_borders")
    out_dir.mkdir(parents=True, exist_ok=True)

    pieces = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))
    corners, edges, _interiors = classify(pieces)
    sides_opt = {s: side_options(pieces, edges, s) for s in 'TRBL'}

    # McGavin corner perm: TL=3, TR=2, BR=0, BL=1
    tl, tr, br, bl = 3, 2, 0, 1
    print(f"Targeting corner perm: TL={tl}, TR={tr}, BR={br}, BL={bl}")

    tl_rs = corner_rots(pieces, tl, 'TL')
    tr_rs = corner_rots(pieces, tr, 'TR')
    bl_rs = corner_rots(pieces, bl, 'BL')
    br_rs = corner_rots(pieces, br, 'BR')
    print(f"  rotation options: TL={tl_rs}, TR={tr_rs}, BR={br_rs}, BL={bl_rs}")

    if not (tl_rs and tr_rs and bl_rs and br_rs):
        print("ERROR: not all corners admit this perm")
        return

    side = 16
    n_saved = 0
    for tl_r in tl_rs:
        te = rotate(pieces[tl], tl_r)
        for tr_r in tr_rs:
            tre = rotate(pieces[tr], tr_r)
            for br_r in br_rs:
                bre = rotate(pieces[br], br_r)
                for bl_r in bl_rs:
                    ble = rotate(pieces[bl], bl_r)
                    c1_list = enumerate_chains(te[1], tre[3], sides_opt['T'], set(), max_results=10)
                    for chain1 in c1_list:
                        used_1 = {pid for (pid, _, _) in chain1}
                        c2_list = enumerate_chains(tre[2], bre[0], sides_opt['R'], used_1, max_results=5)
                        for chain2 in c2_list:
                            used_2 = used_1 | {pid for (pid, _, _) in chain2}
                            # Chain3 matches original semantics (chain runs BR→BL in chain DP,
                            # we'll save it RIGHT-to-LEFT i.e. reverse it for placement).
                            c3_list = enumerate_chains(bre[3], ble[1], sides_opt['B'], used_2, max_results=5)
                            for chain3 in c3_list:
                                used_3 = used_2 | {pid for (pid, _, _) in chain3}
                                # Chain4 matches original semantics (chain runs BL→TL, save BOTTOM-to-TOP).
                                c4_list = enumerate_chains(ble[0], te[2], sides_opt['L'], used_3, max_results=5)
                                for chain4 in c4_list:
                                    # Save as partial
                                    placement = []
                                    # Corners
                                    placement.append({"pos": 0, "piece_id": tl, "rotation": tl_r})
                                    placement.append({"pos": side - 1, "piece_id": tr, "rotation": tr_r})
                                    placement.append({"pos": side * (side - 1), "piece_id": bl, "rotation": bl_r})
                                    placement.append({"pos": side * side - 1, "piece_id": br, "rotation": br_r})
                                    # Top edge (positions 1..14, left-to-right)
                                    for k, (pid, rot, _) in enumerate(chain1):
                                        placement.append({"pos": 1 + k, "piece_id": pid, "rotation": rot})
                                    # Right edge (positions 31, 47, ..., 239 = 16*1+15, 16*2+15, ...)
                                    for k, (pid, rot, _) in enumerate(chain2):
                                        placement.append({"pos": side * (1 + k) + (side - 1), "piece_id": pid, "rotation": rot})
                                    # Bottom edge: chain3 runs BR→BL in chain DP; we need positions
                                    # 241..254 (LEFT-to-RIGHT), so reverse chain3 for placement.
                                    chain3_rev = list(reversed(chain3))
                                    for k, (pid, rot, _) in enumerate(chain3_rev):
                                        placement.append({"pos": side * (side - 1) + 1 + k, "piece_id": pid, "rotation": rot})
                                    # Left edge: chain4 runs BL→TL in chain DP; we need positions
                                    # 16, 32, ..., 224 (TOP-to-BOTTOM), so reverse chain4 for placement.
                                    chain4_rev = list(reversed(chain4))
                                    for k, (pid, rot, _) in enumerate(chain4_rev):
                                        placement.append({"pos": side * (1 + k), "piece_id": pid, "rotation": rot})

                                    n_saved += 1
                                    out_path = out_dir / f"mcgavin_perm_b{n_saved:03d}.json"
                                    with open(out_path, "w") as f:
                                        json.dump({
                                            "source": "vol122_inv3_mcgavin_perm",
                                            "corner_perm": [tl, tr, br, bl],
                                            "corner_rots": [tl_r, tr_r, br_r, bl_r],
                                            "n_placement_cells": len(placement),
                                            "placement": placement,
                                        }, f)
                                    if n_saved <= 5 or n_saved % 50 == 0:
                                        print(f"[#{n_saved:3d}] tl_r={tl_r} tr_r={tr_r} br_r={br_r} bl_r={bl_r}: saved {out_path.name}")
                                    if n_saved >= 100:
                                        print(f"\nCapped at 100 borders. Saved to {out_dir}/")
                                        return

    print(f"\nTotal: {n_saved} borders saved to {out_dir}/")


if __name__ == "__main__":
    main()
