"""W11 bulk screen: take output of border_enumerate.py and SAT-test each.

For each border in the JSON list, do:
  1. Pin its 60 cells + 5 canonical hints.
  2. Free remaining 191 cells.
  3. Run kissat (with short timeout).
  4. Record: UNSAT | SAT (extract solution!) | TIMEOUT.

Output: results JSON with per-border status. Any SAT means we may have found
a 480 candidate.

Usage:
  python3 screen_bulk.py <puzzle.csv> <borders.json> [--timeout 10] [--out results.json]
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HINT_POSITIONS = {135, 210, 34, 221, 45}
CANONICAL_HINTS = {
    135: (138, 0),
    210: (180, 1),
    34: (207, 1),
    221: (248, 2),
    45: (254, 1),
}


def screen_one(puzzle_csv: str, border_placement: dict, timeout_s: int, out_dir: str) -> dict:
    """SAT-screen one border. Returns dict with status + info."""
    # Add hints
    full_placement = dict(border_placement)
    for pos, val in CANONICAL_HINTS.items():
        if pos not in full_placement:
            full_placement[pos] = val

    free_cells = sorted(set(range(256)) - set(full_placement.keys()))

    # Write pinned.json with DENSE indexing (placement[pos] = entry or null)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    pin_path = Path(out_dir) / "pinned_dense.json"
    dense = [None] * 256
    for pos, (pid, rot) in full_placement.items():
        dense[pos] = {'pos': pos, 'piece_id': pid, 'rotation': rot}
    pin_path.write_text(json.dumps({'source': 'w11_bulk', 'placement': dense}))

    # Encode
    for f in Path(out_dir).glob('sat_e2_*.cnf'):
        f.unlink()
    enc = subprocess.run([
        './target/release/sat_e2',
        '--puzzle', puzzle_csv,
        '--output-dir', out_dir,
        '--pin-outside-from', str(pin_path),
        '--free-cells', json.dumps(free_cells),
    ], capture_output=True, text=True, timeout=120)

    cnfs = list(Path(out_dir).glob('sat_e2_*.cnf'))
    if not cnfs:
        return {'status': 'ENCODE_FAILED', 'stderr': enc.stderr[-300:]}

    cnf_path = cnfs[0]

    # Run kissat
    t0 = time.time()
    kissat = subprocess.run(
        ['kissat', f'--time={timeout_s}', str(cnf_path)],
        capture_output=True, text=True, timeout=timeout_s + 30,
    )
    wall = time.time() - t0
    out = kissat.stdout
    if 's UNSATISFIABLE' in out:
        status = 'UNSAT'
    elif 's SATISFIABLE' in out:
        status = 'SAT'
        # Save the model for later decoding
        model_path = Path(out_dir) / f"sat_model.txt"
        model_path.write_text(out)
    else:
        status = 'TIMEOUT'
    pt = re.search(r'process-time:\s+(\d+s)?\s+([\d.]+) seconds', out)
    kissat_time = float(pt.group(2)) if pt else None

    return {
        'status': status,
        'kissat_time_s': kissat_time,
        'wall_time_s': wall,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle_csv")
    ap.add_argument("borders_json")
    ap.add_argument("--timeout", type=int, default=10)
    ap.add_argument("--limit", type=int, default=None, help="screen only first N borders")
    ap.add_argument("--out", type=Path, default=Path("output/vol-123/w11_borders/screen_results.json"))
    args = ap.parse_args()

    data = json.load(open(args.borders_json))
    if isinstance(data, list):
        borders = data
    else:
        borders = data.get('borders', [])
    if args.limit:
        borders = borders[:args.limit]

    print(f"Screening {len(borders)} borders with timeout {args.timeout}s each")

    results = []
    status_counts = {'UNSAT': 0, 'SAT': 0, 'TIMEOUT': 0, 'ENCODE_FAILED': 0}
    t_start = time.time()

    out_dir = "/tmp/w11_bulk_screen"

    for i, b in enumerate(borders):
        # Format: each border in border_enumerate output is a list of 60 dicts:
        # {piece_id, rotation, x, y}
        border_placement = {}
        if isinstance(b, dict) and 'border' in b:
            for entry in b['border']:
                x = entry['x']
                y = entry['y']
                pos = y * 16 + x
                border_placement[pos] = (entry['piece_id'], entry['rotation'])
        elif isinstance(b, dict) and 'placement' in b:
            for entry in b['placement']:
                border_placement[entry['pos']] = (entry['piece_id'], entry['rotation'])
        else:
            print(f"[{i}] unknown border format, skipping")
            continue

        r = screen_one(args.puzzle_csv, border_placement, args.timeout, out_dir)
        results.append({'idx': i, 'border_signature': b.get('signature'), **r})
        status_counts[r['status']] = status_counts.get(r['status'], 0) + 1

        elapsed = time.time() - t_start
        if r['status'] == 'SAT':
            print(f"🎯 [{i}/{len(borders)}] SAT! signature={b.get('signature')[:80] if b.get('signature') else '?'}")
        if (i + 1) % 50 == 0 or r['status'] == 'SAT':
            print(f"[{i+1}/{len(borders)}] {status_counts} elapsed={elapsed:.0f}s")

    # Save results
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump({'borders_file': args.borders_json,
                   'timeout_s': args.timeout,
                   'status_counts': status_counts,
                   'results': results}, f, indent=2)
    print(f"\nFinal: {status_counts}")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
