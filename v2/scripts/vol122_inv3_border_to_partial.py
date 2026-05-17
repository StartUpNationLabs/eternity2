#!/usr/bin/env python3
"""Vol-122 INVENTION 3 step 3 — convert a 60-matched border into a partial
board file (60 cells placed, 196 interior empty), to feed to the solver
engine or ALNS as a STARTING POINT for the interior-only problem.

Re-runs the border enumerator to get a single border, then writes the
60-cell placement to a JSON board file.
"""

from __future__ import annotations
import json, sys
from collections import defaultdict
from itertools import permutations
from pathlib import Path

W = 16

def parse_color(s):
    v = int(s.strip(), 2); return 0 if v == 65535 else v

def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces[pid] = (parse_color(cols[0]), parse_color(cols[1]), parse_color(cols[2]), parse_color(cols[3]))
                pid += 1
            except ValueError: pass
    return pieces

def rotate(edges, rot):
    t, r, b, l = edges
    return [(t,r,b,l),(l,t,r,b),(b,l,t,r),(r,b,l,t)][rot]

def classify(pieces):
    corners, edges, interiors = [], [], []
    for pid, e in pieces.items():
        n = sum(1 for c in e if c == 0)
        if n == 2: corners.append(pid)
        elif n == 1: edges.append(pid)
        else: interiors.append(pid)
    return corners, edges, interiors

def corner_rots(pieces, pid, pos):
    e = pieces[pid]; out = []
    for r in range(4):
        t, ri, b, l = rotate(e, r)
        if (pos=='TL' and t==0 and l==0) or (pos=='TR' and t==0 and ri==0) \
           or (pos=='BL' and b==0 and l==0) or (pos=='BR' and b==0 and ri==0):
            out.append(r)
    return out

def side_options(pieces, edge_pids, side):
    out = defaultdict(list)
    for pid in edge_pids:
        for r in range(4):
            t, ri, b, l = rotate(pieces[pid], r)
            if side == 'T' and t == 0:
                out[pid].append((r, l, ri, b))
            elif side == 'R' and ri == 0:
                out[pid].append((r, t, b, l))
            elif side == 'B' and b == 0:
                out[pid].append((r, ri, l, t))
            elif side == 'L' and l == 0:
                out[pid].append((r, b, t, ri))
    return out

def enumerate_chains(start_color, target_color, side_opts, used_pids, max_results=1):
    out = []
    def recurse(cell_i, state_color, chain, used_local):
        if len(out) >= max_results: return
        if cell_i == 14:
            if state_color == target_color:
                out.append(tuple(chain))
            return
        for pid, opts in side_opts.items():
            if pid in used_local: continue
            for (r, back, fwd, ii) in opts:
                if back != state_color: continue
                used_local.add(pid); chain.append((pid, r, ii))
                recurse(cell_i + 1, fwd, chain, used_local)
                chain.pop(); used_local.discard(pid)
                if len(out) >= max_results: return
    recurse(0, start_color, [], set(used_pids))
    return out

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output/vol-122/border_partial.json")
    ap.add_argument("--max-borders", type=int, default=5,
                    help="how many border configs to dump (each → separate file)")
    args = ap.parse_args()

    pieces = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))
    corners, edges, interiors = classify(pieces)
    sides_opt = {s: side_options(pieces, edges, s) for s in 'TRBL'}

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_dumped = 0
    for perm_i, (tl, tr, br, bl) in enumerate(permutations(corners)):
        if n_dumped >= args.max_borders: break
        tl_rs = corner_rots(pieces, tl, 'TL')
        tr_rs = corner_rots(pieces, tr, 'TR')
        bl_rs = corner_rots(pieces, bl, 'BL')
        br_rs = corner_rots(pieces, br, 'BR')
        if not (tl_rs and tr_rs and bl_rs and br_rs): continue
        for tl_r in tl_rs:
            if n_dumped >= args.max_borders: break
            te = rotate(pieces[tl], tl_r)
            for tr_r in tr_rs:
                if n_dumped >= args.max_borders: break
                tre = rotate(pieces[tr], tr_r)
                for br_r in br_rs:
                    if n_dumped >= args.max_borders: break
                    bre = rotate(pieces[br], br_r)
                    for bl_r in bl_rs:
                        if n_dumped >= args.max_borders: break
                        ble = rotate(pieces[bl], bl_r)
                        c1 = enumerate_chains(te[1], tre[3], sides_opt['T'], set(), max_results=1)
                        if not c1: continue
                        chain1 = c1[0]
                        used = {pid for (pid,_,_) in chain1}
                        c2 = enumerate_chains(tre[2], bre[0], sides_opt['R'], used, max_results=1)
                        if not c2: continue
                        chain2 = c2[0]; used |= {pid for (pid,_,_) in chain2}
                        c3 = enumerate_chains(bre[3], ble[1], sides_opt['B'], used, max_results=1)
                        if not c3: continue
                        chain3 = c3[0]; used |= {pid for (pid,_,_) in chain3}
                        c4 = enumerate_chains(ble[0], te[2], sides_opt['L'], used, max_results=1)
                        if not c4: continue
                        chain4 = c4[0]

                        # Build placement: 4 corners + 14 cells per side
                        placement = []
                        # corners
                        placement.append({"pos": 0,   "piece_id": tl, "rotation": tl_r})
                        placement.append({"pos": 15,  "piece_id": tr, "rotation": tr_r})
                        placement.append({"pos": 255, "piece_id": br, "rotation": br_r})
                        placement.append({"pos": 240, "piece_id": bl, "rotation": bl_r})
                        # top row: (1,0) to (14,0) = pos 1 .. 14
                        for i, (pid, r, _) in enumerate(chain1):
                            placement.append({"pos": 1 + i, "piece_id": pid, "rotation": r})
                        # right col: (15,1) to (15,14) = pos 31, 47, 63, ..., 239
                        for i, (pid, r, _) in enumerate(chain2):
                            placement.append({"pos": 15 + W*(i+1), "piece_id": pid, "rotation": r})
                        # bottom row (CW reversed): (14,15) to (1,15) = pos 254 .. 241
                        for i, (pid, r, _) in enumerate(chain3):
                            placement.append({"pos": 254 - i, "piece_id": pid, "rotation": r})
                        # left col: (0,14) to (0,1) = pos 224, 208, ..., 16
                        for i, (pid, r, _) in enumerate(chain4):
                            placement.append({"pos": 224 - W*i, "piece_id": pid, "rotation": r})

                        # Sort by pos
                        placement.sort(key=lambda p: p["pos"])

                        # Sanity: all 60 unique positions
                        positions = [p["pos"] for p in placement]
                        assert len(set(positions)) == 60, f"got {len(set(positions))} unique positions"

                        # Write
                        this_out = str(out_path).replace(".json", f"_perm{perm_i}_b{n_dumped}.json")
                        doc = {
                            "placement": placement,
                            "metadata": {
                                "source": "vol122_inv3_border_dp",
                                "corner_perm_idx": perm_i,
                                "corners": [tl, tr, br, bl],
                                "corner_rots": [tl_r, tr_r, br_r, bl_r],
                                "border_matched": 60,
                            }
                        }
                        with open(this_out, "w") as f:
                            json.dump(doc, f, indent=2)
                        print(f"wrote {this_out}", file=sys.stderr)
                        n_dumped += 1

    print(f"# Dumped {n_dumped} border partials")

if __name__ == "__main__":
    main()
