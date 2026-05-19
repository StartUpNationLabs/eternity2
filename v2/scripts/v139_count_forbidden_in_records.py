#!/usr/bin/env python3
"""V139-T1 — Count forbidden 2x2 patches in real DB boards."""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np
from collections import defaultdict

REPO = Path(__file__).resolve().parents[1]

def load_csv(p):
    BORDER_RAW = 65535
    pieces = []
    with open(p) as f:
        size = int(f.readline().strip())
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split(",")
            sides = [int(s.strip(), 2) for s in parts[:4]]
            sides = [0 if v == BORDER_RAW else v for v in sides]
            pieces.append(tuple(sides))
    return size, pieces

def rotate(p, r):
    n, e, s, w = p
    return [(n,e,s,w),(e,s,w,n),(s,w,n,e),(w,n,e,s)][r]

def is_forbidden_2x2(pr_color, p_tl, p_tr, p_bl, p_br):
    for r_tl in range(4):
        tl = pr_color[p_tl, r_tl]
        if tl[1] == 0 or tl[2] == 0: continue
        for r_tr in range(4):
            tr = pr_color[p_tr, r_tr]
            if tl[1] != tr[3]: continue
            if tr[2] == 0: continue
            for r_bl in range(4):
                bl = pr_color[p_bl, r_bl]
                if tl[2] != bl[0]: continue
                if bl[1] == 0: continue
                for r_br in range(4):
                    br = pr_color[p_br, r_br]
                    if tr[2] != br[0]: continue
                    if bl[1] != br[3]: continue
                    return False
    return True

def count_forbidden_2x2(board, size, pr_color):
    forbidden = 0
    total = 0
    for r in range(size - 1):
        for c in range(size - 1):
            tl = board[r*size + c]
            tr = board[r*size + c + 1]
            bl = board[(r+1)*size + c]
            br = board[(r+1)*size + c + 1]
            total += 1
            if is_forbidden_2x2(pr_color, tl, tr, bl, br):
                forbidden += 1
    return forbidden, total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", required=True)
    ap.add_argument("--records-dir", required=True)
    ap.add_argument("--n-boards", type=int, default=50)
    args = ap.parse_args()
    size, pieces = load_csv(args.puzzle)
    P = len(pieces)
    pr_color = np.zeros((P, 4, 4), dtype=np.int16)
    for p in range(P):
        for r in range(4):
            pr_color[p, r] = rotate(pieces[p], r)

    records_dir = Path(args.records_dir)
    boards = []
    for path in sorted(records_dir.glob("*.json")):
        try: d = json.load(open(path))
        except: continue
        if not isinstance(d.get("matched"), int): continue
        pl = d.get("placement", [])
        if not isinstance(pl, list): continue
        b = [None] * (size*size)
        for i, p in enumerate(pl):
            if not isinstance(p, dict): continue
            pos = p.get("pos", i)
            b[int(pos)] = int(p["piece_id"])
        if any(x is None for x in b): continue
        boards.append((d["matched"], path.name, b))
    boards = sorted(boards, key=lambda x: x[0])
    print(f"Loaded {len(boards)} boards", flush=True)

    buckets = defaultdict(list)
    for m, name, b in boards:
        if m < 440: buckets["LOW (<440)"].append((m, b, name))
        elif m < 460: buckets["MID (440-459)"].append((m, b, name))
        else: buckets["HIGH (>=460)"].append((m, b, name))

    print(f"\nBucket counts:", flush=True)
    for label, bucket in buckets.items():
        print(f"  {label}: {len(bucket)} boards", flush=True)

    for label, bucket in buckets.items():
        if not bucket: continue
        print(f"\n=== {label} ===", flush=True)
        sampled = bucket[:args.n_boards] if len(bucket) > args.n_boards else bucket
        forbiddens = []
        for m, b, name in sampled:
            forbidden, total = count_forbidden_2x2(b, size, pr_color)
            forbiddens.append(forbidden)
        if forbiddens:
            print(f"  n={len(forbiddens)}  min={min(forbiddens)}  max={max(forbiddens)}  "
                  f"mean={sum(forbiddens)/len(forbiddens):.1f}  median={sorted(forbiddens)[len(forbiddens)//2]}", flush=True)

if __name__ == "__main__":
    main()
