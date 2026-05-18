#!/usr/bin/env python3
"""Vol-125 T2 — generate a corpus of 1000 distinct 60-matched border partials.

Extends vol122_inv3_border_to_partial.py:
  - Enumerates MULTIPLE chains per side (max_chains_per_side configurable).
  - Iterates over all valid (corner-perm × corner-rot) configurations.
  - Randomizes piece-iteration order with a seed so different runs produce
    different border samples (the chain-DFS visit order matters for which
    chains are found first when max-results is bounded).
  - Deduplicates by full placement signature.

Output: 1000+ JSON partials under output/vol-125/borders/, plus
        a summary index with interior-color profile per partial.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from itertools import permutations
from pathlib import Path

W = 16


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v


def load_puzzle(csv_path):
    pieces = {}
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    pid = 0
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces[pid] = (parse_color(cols[0]), parse_color(cols[1]),
                               parse_color(cols[2]), parse_color(cols[3]))
                pid += 1
            except ValueError:
                pass
    return pieces


def rotate(edges, rot):
    t, r, b, l = edges
    return [(t, r, b, l), (l, t, r, b), (b, l, t, r), (r, b, l, t)][rot]


def classify(pieces):
    corners, edges, interiors = [], [], []
    for pid, e in pieces.items():
        n = sum(1 for c in e if c == 0)
        if n == 2:
            corners.append(pid)
        elif n == 1:
            edges.append(pid)
        else:
            interiors.append(pid)
    return corners, edges, interiors


def corner_rots(pieces, pid, pos):
    e = pieces[pid]
    out = []
    for r in range(4):
        t, ri, b, l = rotate(e, r)
        if (pos == 'TL' and t == 0 and l == 0) or (pos == 'TR' and t == 0 and ri == 0) \
           or (pos == 'BL' and b == 0 and l == 0) or (pos == 'BR' and b == 0 and ri == 0):
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


def enumerate_chains(start_color, target_color, side_opts, used_pids, max_results, rng):
    """Iterative DFS, returning up to max_results chains. Randomizes piece order."""
    out = []
    pids_shuffled = list(side_opts.keys())
    rng.shuffle(pids_shuffled)

    def recurse(cell_i, state_color, chain, used_local):
        if len(out) >= max_results:
            return
        if cell_i == 14:
            if state_color == target_color:
                out.append(tuple(chain))
            return
        for pid in pids_shuffled:
            if pid in used_local:
                continue
            opts = side_opts[pid]
            for (r, back, fwd, ii) in opts:
                if back != state_color:
                    continue
                used_local.add(pid)
                chain.append((pid, r, ii))
                recurse(cell_i + 1, fwd, chain, used_local)
                chain.pop()
                used_local.discard(pid)
                if len(out) >= max_results:
                    return

    recurse(0, start_color, [], set(used_pids))
    return out


def make_placement(tl, tl_r, tr, tr_r, br, br_r, bl, bl_r, chain1, chain2, chain3, chain4):
    placement = []
    placement.append({"pos": 0, "piece_id": tl, "rotation": tl_r})
    placement.append({"pos": 15, "piece_id": tr, "rotation": tr_r})
    placement.append({"pos": 255, "piece_id": br, "rotation": br_r})
    placement.append({"pos": 240, "piece_id": bl, "rotation": bl_r})
    for i, (pid, r, _) in enumerate(chain1):
        placement.append({"pos": 1 + i, "piece_id": pid, "rotation": r})
    for i, (pid, r, _) in enumerate(chain2):
        placement.append({"pos": 15 + W * (i + 1), "piece_id": pid, "rotation": r})
    for i, (pid, r, _) in enumerate(chain3):
        placement.append({"pos": 254 - i, "piece_id": pid, "rotation": r})
    for i, (pid, r, _) in enumerate(chain4):
        placement.append({"pos": 224 - W * i, "piece_id": pid, "rotation": r})
    placement.sort(key=lambda p: p["pos"])
    return placement


def placement_signature(placement):
    blob = json.dumps([(p["pos"], p["piece_id"], p["rotation"]) for p in placement]).encode()
    return hashlib.md5(blob).hexdigest()[:16]


def interior_profile(chain1, chain2, chain3, chain4):
    return (
        tuple(ii for (_, _, ii) in chain1),
        tuple(ii for (_, _, ii) in chain2),
        tuple(ii for (_, _, ii) in chain3),
        tuple(ii for (_, _, ii) in chain4),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--out-dir", default="output/vol-125/borders")
    ap.add_argument("--target", type=int, default=1000, help="target distinct borders to produce")
    ap.add_argument("--max-per-config", type=int, default=8,
                    help="max distinct borders per (perm, corner-rots) config")
    ap.add_argument("--chains-per-side", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--summary", default=None,
                    help="optional path for the index JSON (default: <out-dir>/index.json)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    pieces = load_puzzle(Path(args.puzzle))
    corners, edges, interiors = classify(pieces)
    sides_opt = {s: side_options(pieces, edges, s) for s in 'TRBL'}

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = Path(args.summary) if args.summary else out_dir / "index.json"

    # Enumerate all (perm, corner-rot) configurations admissible.
    perm_configs = []
    for perm_i, (tl, tr, br, bl) in enumerate(permutations(corners)):
        tl_rs = corner_rots(pieces, tl, 'TL')
        tr_rs = corner_rots(pieces, tr, 'TR')
        bl_rs = corner_rots(pieces, bl, 'BL')
        br_rs = corner_rots(pieces, br, 'BR')
        if not (tl_rs and tr_rs and bl_rs and br_rs):
            continue
        for tl_r in tl_rs:
            for tr_r in tr_rs:
                for br_r in br_rs:
                    for bl_r in bl_rs:
                        perm_configs.append((perm_i, tl, tl_r, tr, tr_r, br, br_r, bl, bl_r))
    rng.shuffle(perm_configs)
    print(f"# {len(perm_configs)} valid (corner-perm × corner-rot) configurations",
          file=sys.stderr)

    seen_sigs = set()
    seen_profiles = set()
    index_entries = []
    n_dumped = 0

    for config_idx, cfg in enumerate(perm_configs):
        if n_dumped >= args.target:
            break
        (perm_i, tl, tl_r, tr, tr_r, br, br_r, bl, bl_r) = cfg
        te = rotate(pieces[tl], tl_r)
        tre = rotate(pieces[tr], tr_r)
        bre = rotate(pieces[br], br_r)
        ble = rotate(pieces[bl], bl_r)

        produced_this_cfg = 0
        c1_list = enumerate_chains(te[1], tre[3], sides_opt['T'], set(),
                                    args.chains_per_side, rng)
        if not c1_list:
            continue
        for chain1 in c1_list:
            if produced_this_cfg >= args.max_per_config or n_dumped >= args.target:
                break
            used_1 = {pid for (pid, _, _) in chain1}
            c2_list = enumerate_chains(tre[2], bre[0], sides_opt['R'], used_1,
                                        args.chains_per_side, rng)
            for chain2 in c2_list:
                if produced_this_cfg >= args.max_per_config or n_dumped >= args.target:
                    break
                used_2 = used_1 | {pid for (pid, _, _) in chain2}
                c3_list = enumerate_chains(bre[3], ble[1], sides_opt['B'], used_2,
                                            args.chains_per_side, rng)
                for chain3 in c3_list:
                    if produced_this_cfg >= args.max_per_config or n_dumped >= args.target:
                        break
                    used_3 = used_2 | {pid for (pid, _, _) in chain3}
                    c4_list = enumerate_chains(ble[0], te[2], sides_opt['L'], used_3,
                                                args.chains_per_side, rng)
                    for chain4 in c4_list:
                        if produced_this_cfg >= args.max_per_config or n_dumped >= args.target:
                            break
                        placement = make_placement(tl, tl_r, tr, tr_r, br, br_r, bl, bl_r,
                                                    chain1, chain2, chain3, chain4)
                        sig = placement_signature(placement)
                        if sig in seen_sigs:
                            continue
                        seen_sigs.add(sig)
                        profile = interior_profile(chain1, chain2, chain3, chain4)
                        profile_new = profile not in seen_profiles
                        seen_profiles.add(profile)

                        fname = f"b{n_dumped:04d}_perm{perm_i}_sig{sig}.json"
                        path = out_dir / fname
                        doc = {
                            "placement": placement,
                            "metadata": {
                                "source": "vol125_border_corpus",
                                "corner_perm_idx": perm_i,
                                "corners": [tl, tr, br, bl],
                                "corner_rots": [tl_r, tr_r, br_r, bl_r],
                                "border_matched": 60,
                                "profile_unique": profile_new,
                                "seed": args.seed,
                                "config_idx": config_idx,
                            }
                        }
                        with open(path, "w") as f:
                            json.dump(doc, f)
                        index_entries.append({
                            "id": n_dumped,
                            "path": str(path),
                            "sig": sig,
                            "perm_i": perm_i,
                            "corners": [tl, tr, br, bl],
                            "corner_rots": [tl_r, tr_r, br_r, bl_r],
                            "profile_unique": profile_new,
                        })
                        n_dumped += 1
                        produced_this_cfg += 1
                        if n_dumped % 100 == 0:
                            print(f"# progress: {n_dumped}/{args.target} borders dumped "
                                  f"({len(seen_profiles)} unique profiles)", file=sys.stderr)

    with open(summary_path, "w") as f:
        json.dump({
            "n_borders": n_dumped,
            "n_distinct_profiles": len(seen_profiles),
            "n_configs_visited": config_idx + 1,
            "seed": args.seed,
            "entries": index_entries,
        }, f, indent=2)
    print(f"# DONE: dumped {n_dumped} borders, {len(seen_profiles)} distinct profiles, "
          f"summary at {summary_path}")


if __name__ == "__main__":
    main()
