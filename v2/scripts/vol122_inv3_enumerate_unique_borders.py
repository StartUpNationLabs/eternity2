#!/usr/bin/env python3
"""Vol-122 INVENTION 3 cont'd — enumerate PIECE-UNIQUE 60-matched borders.

For each (corner-perm, corner-rot) config that admits chain-DP UB=60:
  - Branch-and-bound search over piece-unique edge-piece assignments
    around the ring that achieve all 60 border-matched edges.
  - For each found piece-unique 60-border, output its interior-color
    profile (56 colors — one per interior-facing edge).
"""

from __future__ import annotations
import sys
from collections import defaultdict
from itertools import permutations
from pathlib import Path

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

def enumerate_chains(start_color, target_color, side_opts, used_pids, max_results=3):
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
    pieces = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))
    corners, edges, interiors = classify(pieces)
    sides_opt = {s: side_options(pieces, edges, s) for s in 'TRBL'}

    total_borders_found = 0
    interior_profiles = set()
    SAMPLE_CAP = 50

    for perm_i, (tl, tr, br, bl) in enumerate(permutations(corners)):
        if total_borders_found >= SAMPLE_CAP: break
        tl_rs = corner_rots(pieces, tl, 'TL')
        tr_rs = corner_rots(pieces, tr, 'TR')
        bl_rs = corner_rots(pieces, bl, 'BL')
        br_rs = corner_rots(pieces, br, 'BR')
        if not (tl_rs and tr_rs and bl_rs and br_rs): continue
        for tl_r in tl_rs:
            if total_borders_found >= SAMPLE_CAP: break
            te = rotate(pieces[tl], tl_r)
            for tr_r in tr_rs:
                if total_borders_found >= SAMPLE_CAP: break
                tre = rotate(pieces[tr], tr_r)
                for br_r in br_rs:
                    if total_borders_found >= SAMPLE_CAP: break
                    bre = rotate(pieces[br], br_r)
                    for bl_r in bl_rs:
                        if total_borders_found >= SAMPLE_CAP: break
                        ble = rotate(pieces[bl], bl_r)
                        c1_list = enumerate_chains(te[1], tre[3], sides_opt['T'], set(), max_results=2)
                        for chain1 in c1_list:
                            if total_borders_found >= SAMPLE_CAP: break
                            used_1 = {pid for (pid, _, _) in chain1}
                            c2_list = enumerate_chains(tre[2], bre[0], sides_opt['R'], used_1, max_results=2)
                            for chain2 in c2_list:
                                if total_borders_found >= SAMPLE_CAP: break
                                used_2 = used_1 | {pid for (pid, _, _) in chain2}
                                c3_list = enumerate_chains(bre[3], ble[1], sides_opt['B'], used_2, max_results=2)
                                for chain3 in c3_list:
                                    if total_borders_found >= SAMPLE_CAP: break
                                    used_3 = used_2 | {pid for (pid, _, _) in chain3}
                                    c4_list = enumerate_chains(ble[0], te[2], sides_opt['L'], used_3, max_results=2)
                                    for chain4 in c4_list:
                                        total_borders_found += 1
                                        profile_t = tuple(ii for (_, _, ii) in chain1)
                                        profile_r = tuple(ii for (_, _, ii) in chain2)
                                        profile_b = tuple(ii for (_, _, ii) in chain3)
                                        profile_l = tuple(ii for (_, _, ii) in chain4)
                                        interior_profiles.add((profile_t, profile_r, profile_b, profile_l))
                                        if total_borders_found <= 3:
                                            print(f"[border #{total_borders_found}] perm_i={perm_i} corners=({tl}r{tl_r},{tr}r{tr_r},{br}r{br_r},{bl}r{bl_r})", file=sys.stderr)
                                            print(f"  T-profile: {profile_t}", file=sys.stderr)
                                        if total_borders_found >= SAMPLE_CAP: break

    print(f"# Sample: piece-unique 60-matched borders found = {total_borders_found} (capped at {SAMPLE_CAP})")
    print(f"# Distinct interior-color profiles among sample: {len(interior_profiles)}")

if __name__ == "__main__":
    main()
