"""Verify a partial / full board JSON output from BP-decimation.

Reports:
  - piece-uniqueness (any duplicates?)
  - matched interior edges
  - border correctness
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'w1_peps'))
from puzzle_loader import Puzzle, load_puzzle, BORDER
from verify_solution import verify


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle")
    ap.add_argument("placement_json")
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    data = json.load(open(args.placement_json))
    placement_list = data.get('placement', [])
    placement = {pp['pos']: (pp['piece_id'], pp['rotation']) for pp in placement_list}

    print(f"Puzzle: size={p.size} pieces={p.n_pieces}")
    print(f"Placement: {len(placement)} cells filled")

    stats = verify(p, placement)
    print(f"\nVerification:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
