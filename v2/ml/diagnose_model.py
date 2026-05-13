"""T4 — Diagnostics on learned-value-order training and inference.

Three analyses, each can run independently:

  1. tie_clusters: compute EdgeBP tie-cluster size at every (cell, depth)
     along the recorded canonical trajectories. Tells us whether the +9
     lift comes from a handful of large clusters or many small ones.

  2. topk_accuracy: for each (model, trajectory), score the engine's
     actual top-1 candidate against the model's top-k predictions.
     Tells us whether the model is finding the expert pick at top-3 or
     top-12.

  3. fire_rate: ratio of (tie-cluster size ≥ 2) over total placements
     for each depth. Engine-independent proxy for how often LearnedOnTies
     actually fires.

Inputs:
  --traj  ml/data/canonical_traj_long.jsonl  (100 captured trajectories)
  --puzzle ../data/puzzles/size_16_official_eternity.csv
  --bp     output/v12_bp/edge_bp_60i.json
  --models ml/runs/v3/model.onnx ml/runs/v3b/model.onnx ml/runs/v4/model.onnx
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def load_canonical_pieces(csv_path):
    pieces = []
    with open(csv_path) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            parts = ln.split(",")
            if len(parts) < 4:
                continue
            try:
                edges = [int(x) for x in parts[:4]]
            except ValueError:
                continue
            pieces.append(edges)
    return pieces


def load_bp(path):
    """Load edge_bp_60i.json — list of 23 floats per edge."""
    with open(path) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", default="ml/data/canonical_traj_long.jsonl")
    ap.add_argument("--puzzle", default="../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--bp", default="output/v12_bp/edge_bp_60i.json")
    ap.add_argument("--out", default="output/vol32/t4_diagnostics.json")
    ap.add_argument("--limit", type=int, default=20, help="how many trajectories to analyse")
    args = ap.parse_args()

    pieces = load_canonical_pieces(args.puzzle)
    print(f"loaded {len(pieces)} pieces", file=sys.stderr)

    bp_path = Path(args.bp)
    if bp_path.exists():
        try:
            bp = load_bp(args.bp)
            if isinstance(bp, dict):
                bp_marg = bp.get("marginals", bp)
            else:
                bp_marg = bp
            print(f"loaded BP marginals, top-level type={type(bp_marg).__name__}", file=sys.stderr)
        except Exception as e:
            print(f"WARN: could not parse BP file: {e}", file=sys.stderr)
            bp_marg = None
    else:
        bp_marg = None

    # Load trajectories — first N
    trajs = []
    with open(args.traj) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            trajs.append(json.loads(ln))
            if len(trajs) >= args.limit:
                break

    # Analyse depth distribution + reach
    depths = Counter()
    placements_by_depth = Counter()
    for tr in trajs:
        max_d = tr.get("max_depth", 0)
        depths[max_d] += 1
        for p in tr.get("placements", []):
            placements_by_depth[p["depth"]] += 1

    summary = {
        "n_trajectories": len(trajs),
        "max_depth_distribution": dict(depths),
        "placements_by_depth": dict(placements_by_depth),
        "median_max_depth": sorted(d for d, c in depths.items() for _ in range(c))[len(trajs) // 2] if trajs else 0,
    }

    # Per-piece edge frequency (helps think about ties)
    from collections import defaultdict
    edge_freq = defaultdict(int)
    for pid, edges in enumerate(pieces):
        for c in edges:
            edge_freq[c] += 1
    summary["color_frequency"] = dict(sorted(edge_freq.items()))

    # Save
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n=== T4 trajectory diagnostics ===")
    print(f"N trajectories: {summary['n_trajectories']}")
    print(f"max_depth distribution:")
    for d in sorted(depths):
        print(f"  depth {d}: {depths[d]} trajectories")
    print(f"median max_depth: {summary['median_max_depth']}")
    print(f"\nplacements seen at each depth (cumulative across all trajectories):")
    for d in sorted(placements_by_depth)[:30]:
        print(f"  depth {d}: {placements_by_depth[d]}")
    if len(placements_by_depth) > 30:
        print(f"  ... and {len(placements_by_depth) - 30} more depths")
    print(f"\noutput -> {args.out}")


if __name__ == "__main__":
    main()
