#!/usr/bin/env python3
"""V21: survey gap across ALL high-score boards we have."""

from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")
EDGE_RELAX = ROOT / "target/release/edge_relax"

def score_of(p: Path):
    try:
        d = json.load(p.open())
        s = d.get('matched_best') or d.get('matched') or d.get('score') or 0
        if isinstance(s, dict): return 0
        return int(s)
    except: return 0

def gap_of(p: Path):
    """Run edge_relax and parse the final score."""
    try:
        r = subprocess.run(
            [str(EDGE_RELAX), "--board", str(p), "--max-iters", "30"],
            capture_output=True, text=True, cwd=ROOT, timeout=30,
        )
        for line in r.stdout.split('\n') + r.stderr.split('\n'):
            if line.startswith("Final score:"):
                # "Final score: 461/480"
                parts = line.split(':')[1].strip().split('/')
                return int(parts[0])
    except Exception as e:
        return None
    return None

def main():
    # Collect all high-score boards (score >= 440)
    boards = []
    for p in ROOT.glob("output/**/*.json"):
        s = score_of(p)
        if s >= 440:
            boards.append((s, p))
    boards.sort(reverse=True)
    print(f"Found {len(boards)} boards with score >= 440")

    # Compute gap for each
    print(f"{'Score':<5} {'Bound':<5} {'Gap':<5}  Path")
    seen_sigs = set()  # avoid byte-identical boards
    for s, p in boards:
        # Skip if duplicate by signature
        try:
            d = json.load(p.open())
            sig = tuple((c['piece_id'], c['rotation']) if c else (-1, -1) for c in d.get('placement', []))
            if sig in seen_sigs:
                continue
            seen_sigs.add(sig)
        except: continue
        b = gap_of(p)
        if b is None: continue
        gap = b - s
        print(f"{s:<5} {b:<5} {gap:<+5} {p.relative_to(ROOT)}")

if __name__ == "__main__":
    sys.exit(main() or 0)
