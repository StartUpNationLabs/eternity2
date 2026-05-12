#!/usr/bin/env python3
"""MAP-Elites for Eternity II.

Maintain an archive of structurally-diverse boards indexed by behaviour
descriptor. Each iteration:
  1. Sample a random elite from the archive.
  2. Mutate it (destroy a random 4x4 region, refill via pt_e2 with
     --pin-cells to fix everything else).
  3. Compute behaviour descriptor of the child.
  4. Insert into archive if better than the current elite at that
     descriptor slot.

Behaviour descriptor:
  D0 = border family bucket  (corner-piece id, 0-3)
  D1 = mismatch quadrant signature (SE, SW, NE, NW; binned)
  D2 = total Z_22 charge count bucket (0=low, 1=mid-low, 2=mid-high, 3=high)
Total niches: 4 x 6 x 4 = 96. (Some unreachable; archive sparse.)

Initialisation: load all available boards (corpus 451-454 + vol-6's
top-K synthetic borders if they have polish results). Compute their
descriptors. Place each in its niche.

Iteration: parallel mutation across multiple workers (PT calls are
~100s each at 1 replica; we run 4 in parallel).
"""

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

BORDER = 65535
W = 16
HINT_CELLS = {(7, 8), (2, 13), (2, 2), (13, 13), (13, 2)}


def parse_color(s):
    v = int(s.strip(), 2)
    return -1 if v == BORDER else v


def load_pieces(puzzle_csv):
    pieces = []
    with open(puzzle_csv) as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    for ln in lines[1:]:
        cols = ln.split(",")
        pieces.append(tuple(parse_color(c) for c in cols[:4]))
    return pieces


def rotate(piece, rot):
    t, r, b, l = piece
    return [(t, r, b, l), (l, t, r, b), (b, l, t, r), (r, b, l, t)][rot]


def board_cells(placement, pieces):
    """Return dict (x,y) -> (top, right, bottom, left) for the rotated edges."""
    cells = {}
    for idx, e in enumerate(placement):
        if e is None:
            continue
        pid, rot = e["piece_id"], e["rotation"]
        x = idx % W
        y = idx // W
        cells[(x, y)] = rotate(pieces[pid], rot)
    return cells


def score_board(placement, pieces):
    cells = board_cells(placement, pieces)
    s = 0
    for (x, y), (t, r, b, l) in cells.items():
        if x + 1 < W and (x + 1, y) in cells:
            if r == cells[(x + 1, y)][3] and r > 0:
                s += 1
        if y + 1 < W and (x, y + 1) in cells:
            if b == cells[(x, y + 1)][0] and b > 0:
                s += 1
    return s


def mismatched_cells(placement, pieces):
    cells = board_cells(placement, pieces)
    mm = set()
    for (x, y), (t, r, b, l) in cells.items():
        if x + 1 < W and (x + 1, y) in cells:
            if r != cells[(x + 1, y)][3]:
                mm.add((x, y))
                mm.add((x + 1, y))
        if y + 1 < W and (x, y + 1) in cells:
            if b != cells[(x, y + 1)][0]:
                mm.add((x, y))
                mm.add((x, y + 1))
    return mm


def z22_charges(placement, pieces):
    """Per-interior-vertex Z_22 charge: sum of 4 incident edge colours mod 22."""
    cells = board_cells(placement, pieces)
    charges = {}
    for vy in range(1, W):
        for vx in range(1, W):
            nw = cells.get((vx - 1, vy - 1))
            ne = cells.get((vx, vy - 1))
            sw = cells.get((vx - 1, vy))
            se = cells.get((vx, vy))
            if not (nw and ne and sw and se):
                continue
            d1 = (nw[1] - ne[3]) % 22
            d2 = (sw[1] - se[3]) % 22
            d3 = (nw[2] - sw[0]) % 22
            d4 = (ne[2] - se[0]) % 22
            c = (d1 + d2 + d3 + d4) % 22
            charges[(vx, vy)] = c
    return charges


def descriptor(placement, pieces):
    """Return (D0, D1, D2): border-family, mismatch quadrant signature, charge count bucket."""
    cells = board_cells(placement, pieces)
    HX, HY = 7, 8

    # D0: top-left corner piece (positions (0,0))
    tl = placement[0]
    d0 = tl["piece_id"] if tl else 0  # 0..3 for the 4 corner pieces, but raw pid

    # D1: mismatch quadrant — which quadrant has the most mismatches?
    mm = mismatched_cells(placement, pieces)
    q = {"NW": 0, "NE": 0, "SW": 0, "SE": 0}
    for x, y in mm:
        if x < HX and y < HY:
            q["NW"] += 1
        elif x >= HX and y < HY:
            q["NE"] += 1
        elif x < HX and y >= HY:
            q["SW"] += 1
        else:
            q["SE"] += 1
    sorted_q = sorted(q.items(), key=lambda kv: -kv[1])
    # Pair of top-2 quadrant names; 6 possible pairs
    d1 = "+".join(sorted([sorted_q[0][0], sorted_q[1][0]]))

    # D2: total nonzero Z_22 charges, bucketed
    chs = z22_charges(placement, pieces)
    nonzero = sum(1 for c in chs.values() if c != 0)
    if nonzero <= 15:
        d2 = 0
    elif nonzero <= 31:
        d2 = 1
    elif nonzero <= 47:
        d2 = 2
    else:
        d2 = 3

    return (d0, d1, d2)


def load_board(path):
    with open(path) as f:
        d = json.load(f)
    return d.get("placement"), d.get("score", {}).get("matched_edges", 0), path


class Archive:
    def __init__(self):
        self.elites = {}  # descriptor -> (score, path)

    def insert(self, desc, score, path):
        if desc not in self.elites or score > self.elites[desc][0]:
            self.elites[desc] = (score, path)
            return True
        return False

    def random_elite(self, rng):
        keys = list(self.elites.keys())
        if not keys:
            return None
        return random.choice(keys), *self.elites[random.choice(keys)]

    def random_elite_path(self, rng):
        keys = list(self.elites.keys())
        if not keys:
            return None, None, None
        d = rng.choice(keys)
        score, path = self.elites[d]
        return d, score, path

    def best(self):
        if not self.elites:
            return None
        return max(self.elites.values(), key=lambda v: v[0])

    def size(self):
        return len(self.elites)

    def save(self, path):
        with open(path, "w") as f:
            json.dump({str(k): [v[0], str(v[1])] for k, v in self.elites.items()}, f)

    def summary(self):
        scores = [v[0] for v in self.elites.values()]
        return {
            "n_elites": len(self.elites),
            "max_score": max(scores) if scores else 0,
            "mean_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
        }


def mutate_via_pt(board_path, region_xy, region_k, pt_seconds, seed,
                   pt_binary, out_dir, replicas=2):
    """Destroy a k×k region at (region_x, region_y), let pt_e2 refill via PT."""
    # Build the list of cells to PIN (everything NOT in the region).
    rx, ry = region_xy
    free = set()
    for dy in range(region_k):
        for dx in range(region_k):
            x = rx + dx
            y = ry + dy
            if (x, y) in HINT_CELLS:
                continue
            free.add((x, y))
    pin_list = [y * W + x for x in range(W) for y in range(W)
                if (x, y) not in free]
    pin_json = json.dumps(pin_list)
    out_log = out_dir / f"mutation_{seed}.log"
    cmd = [
        pt_binary,
        "--start-from", str(board_path),
        "--pin-cells", pin_json,
        "--pt-seconds", str(pt_seconds),
        "--skip-sa-compare",
        "--seed", str(seed),
        "--n-replicas", str(replicas),
        # Don't pin hints redundantly; they're in pin_list already
    ]
    with open(out_log, "w") as f:
        result = subprocess.run(cmd, stdout=f, stderr=f, timeout=pt_seconds + 60)
    if result.returncode != 0:
        return None
    # Extract output JSON path from log
    with open(out_log) as f:
        log = f.read()
    import re
    m = re.search(r"Report:\s+(\S+)", log)
    if m:
        return Path(m.group(1))
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    parser.add_argument("--pt-binary", default="./target/release/pt_e2")
    parser.add_argument("--out-dir", default="output/v7_map_elites")
    parser.add_argument("--n-iters", type=int, default=10)
    parser.add_argument("--pt-seconds", type=int, default=60)
    parser.add_argument("--region-k", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--init-corpus", action="store_true",
                        help="Seed archive from existing HISTORIC and stage-2 boards")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pieces = load_pieces(args.puzzle)
    rng = random.Random(args.seed)

    archive = Archive()

    # Seed archive from corpus
    if args.init_corpus:
        corpus_paths = []
        for pat in [
            "output/HISTORIC_first_454_1778567792.json",
            "output/night-archive/HISTORIC_*.json",
            "output/pt_e2_*_4[2-3][0-9]of480.json",
            "output/pt_e2_*_4[4-5][0-9]of480.json",
        ]:
            corpus_paths.extend(Path(".").glob(pat))
        print(f"loading {len(corpus_paths)} corpus boards...")
        for p in corpus_paths:
            try:
                placement, score, _ = load_board(p)
                if not placement or score < 400:
                    continue
                desc = descriptor(placement, pieces)
                # Copy to archive directory
                archive_path = out_dir / f"elite_{desc[0]}_{desc[1]}_{desc[2]}_{score}.json"
                if archive.insert(desc, score, archive_path):
                    shutil.copy(p, archive_path)
            except Exception as e:
                print(f"  skip {p}: {e}")
        print(f"initial archive size: {archive.size()}, best={archive.best()}")
        print(f"archive summary: {archive.summary()}")
        archive.save(out_dir / "archive_init.json")

    # MAP-Elites iterations
    print(f"\n=== MAP-Elites: {args.n_iters} iterations, {args.pt_seconds}s/mut ===")
    for it in range(args.n_iters):
        if archive.size() == 0:
            print(f"iter {it}: empty archive, abort")
            break
        d, parent_score, parent_path = archive.random_elite_path(rng)
        # Bias region selection toward mismatched-cell zones of the parent
        with open(parent_path) as f:
            parent_placement = json.load(f).get("placement", [])
        if not parent_placement:
            continue
        parent_mm = mismatched_cells(parent_placement, pieces)
        if parent_mm and rng.random() < 0.8:
            # Pick a random mismatched cell, center 4x4 on its neighbourhood
            cx, cy = rng.choice(list(parent_mm))
            rx = max(1, min(W - args.region_k - 1, cx - args.region_k // 2))
            ry = max(1, min(W - args.region_k - 1, cy - args.region_k // 2))
        else:
            rx = rng.randint(1, W - args.region_k - 1)
            ry = rng.randint(1, W - args.region_k - 1)
        seed_mut = rng.randint(1, 2**31)
        print(f"iter {it}: parent desc={d} score={parent_score} -> region ({rx},{ry})+{args.region_k}, seed={seed_mut}")
        child_path = mutate_via_pt(
            parent_path, (rx, ry), args.region_k,
            args.pt_seconds, seed_mut, args.pt_binary, out_dir,
        )
        if not child_path or not child_path.exists():
            print(f"  mutation failed")
            continue
        try:
            placement, child_score, _ = load_board(child_path)
        except Exception as e:
            print(f"  read failed: {e}")
            continue
        child_desc = descriptor(placement, pieces)
        if archive.insert(child_desc, child_score, child_path):
            print(f"  INSERT desc={child_desc} score={child_score} (new niche or improved)")
        else:
            print(f"  reject: desc={child_desc} score={child_score} (existing better)")
        archive.save(out_dir / "archive_current.json")
        print(f"  archive size: {archive.size()}; best: {archive.best()}")


if __name__ == "__main__":
    main()
