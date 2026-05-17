"""W11 prototype: SAT-screen a border configuration.

Given a 60-cell border partial JSON, add the 5 canonical hints, then
SAT-test if the remaining interior admits a 480 solution.

Usage:
  python3 screen_one_border.py <puzzle.csv> <border_partial.json> [--timeout 60]
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Hint positions (canonical 16x16 with 5 hints):
HINT_POSITIONS = {135, 210, 34, 221, 45}
# Hints by piece+rotation
CANONICAL_HINTS = {
    135: (138, 0),
    210: (180, 1),
    34: (207, 1),
    221: (248, 2),
    45: (254, 1),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle_csv")
    ap.add_argument("border_json")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--out-dir", default="/tmp/w11_sat_screen")
    args = ap.parse_args()

    # Load border partial
    data = json.load(open(args.border_json))
    border_placement = {p['pos']: (p['piece_id'], p['rotation'])
                        for p in data.get('placement', [])}
    print(f"Border partial: {len(border_placement)} cells")

    # Add the 5 hints
    for pos, val in CANONICAL_HINTS.items():
        if pos not in border_placement:
            border_placement[pos] = val
    print(f"With hints: {len(border_placement)} cells pinned")

    # Free cells = all 256 - pinned
    pinned_pos = set(border_placement.keys())
    free_cells = sorted(set(range(256)) - pinned_pos)
    print(f"Free cells: {len(free_cells)}")

    # Write the "pinned" board JSON (border + hints) so sat_e2 can read it.
    # NOTE: sat_e2 expects placement[pos] = entry at that flat position. So we
    # need DENSE indexing: position 0..255, with null for unfilled cells.
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    pin_path = Path(args.out_dir) / "pinned.json"
    dense_placement = [None] * 256
    for pos, (pid, rot) in border_placement.items():
        dense_placement[pos] = {'pos': pos, 'piece_id': pid, 'rotation': rot}
    pin_data = {
        'source': 'w11_border_pin',
        'placement': dense_placement,
    }
    pin_path.write_text(json.dumps(pin_data))

    # Run sat_e2 to encode
    enc = subprocess.run([
        './target/release/sat_e2',
        '--puzzle', args.puzzle_csv,
        '--output-dir', args.out_dir,
        '--pin-outside-from', str(pin_path),
        '--free-cells', json.dumps(free_cells),
    ], capture_output=True, text=True, timeout=120)
    # Check for warnings/errors in stderr
    for line in enc.stderr.split('\n'):
        if 'WARN' in line or 'ERROR' in line.upper():
            print(f"  enc: {line}")
    cnfs = sorted(Path(args.out_dir).glob('sat_e2_*.cnf'))
    if not cnfs:
        print("ENCODE FAILED")
        print(enc.stderr[-500:])
        return
    cnf_path = cnfs[-1]
    vars_match = re.search(r'total vars: (\d+)', enc.stderr)
    clauses_match = re.search(r'hard clauses: (\d+)', enc.stderr)
    print(f"vars: {vars_match.group(1) if vars_match else '?'}, clauses: {clauses_match.group(1) if clauses_match else '?'}")

    # Run kissat
    t0 = time.time()
    kissat = subprocess.run(
        ['kissat', f'--time={args.timeout}', str(cnf_path)],
        capture_output=True, text=True, timeout=args.timeout + 30,
    )
    wall = time.time() - t0
    out = kissat.stdout
    status = '?'
    if 's UNSATISFIABLE' in out: status = 'UNSAT'
    elif 's SATISFIABLE' in out: status = 'SAT'
    else: status = 'TIMEOUT'

    pt = re.search(r'process-time:\s+(\d+s)?\s+([\d.]+) seconds', out)
    kissat_time = float(pt.group(2)) if pt else None

    print(f"\nResult: {status}")
    if kissat_time:
        print(f"kissat time: {kissat_time:.2f}s")
    print(f"wall time: {wall:.2f}s")


if __name__ == "__main__":
    main()
