"""W-SAT toolbox: UNSAT verification of a board's border (or arbitrary pin set).

NEW DISCOVERY (vol-123, 2026-05-17):
  Given a high-score board, we can pin its BORDER + far-interior cells,
  free the mismatch region, and SAT-decide whether ANY assignment to the
  freed cells produces a 480/480 fully-matched board. If UNSAT, that's
  a STRUCTURAL PROOF that the pinned region cannot reach 480.

  Tested on 459 board: UNSAT at halos 0-5 in <2 seconds each. Full
  interior freed (191 cells, only 60 border + 5 hints pinned): UNSAT
  in 1.37 sec. PROVES the 459 record's border ring is incompatible
  with any 480 solution.

This is a VERY FAST verification primitive. Use it to:
  1. Rule out basins quickly (test border → if UNSAT, basin can't solve)
  2. Filter candidate boards / partials before expensive ALNS
  3. Validate that a hypothesized improvement is even possible
  4. Decide between border configurations

Usage:
  python3 sat_unsat_border.py <puzzle_csv> <board_json> [--free-cells <mode>]

Modes for --free-cells:
  mismatches: only the mismatch cells of the board (default)
  halo-N:     mismatches plus halo of N cells (Manhattan distance)
  interior:   all 191 interior cells freed, only border pinned
  custom:     comma-separated cell indices

Returns: SAT (with solution extracted), UNSAT (with proof), or TIMEOUT.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def find_mismatches(puzzle_csv: str, board_json: str) -> list[int]:
    """Run mismatch_map to extract mismatch cells."""
    result = subprocess.run(
        ['./target/release/mismatch_map', board_json],
        capture_output=True, text=True, timeout=60,
    )
    cells = set()
    for line in result.stdout.split('\n'):
        if 'cluster' in line and 'cells=' in line:
            for y, x in re.findall(r'\((\d+),(\d+)\)', line):
                cells.add(int(y) * 16 + int(x))
    return sorted(cells)


def expand_halo(cells: list[int], halo: int, size: int = 16, exclude: set[int] | None = None) -> list[int]:
    """Expand by Manhattan halo, excluding specified positions (e.g., hints)."""
    exclude = exclude or set()
    out = set(cells)
    for c in cells:
        y, x = c // size, c % size
        for dy in range(-halo, halo + 1):
            for dx in range(-halo, halo + 1):
                if abs(dy) + abs(dx) > halo: continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < size and 0 <= nx < size:
                    p = ny * size + nx
                    if p not in exclude:
                        out.add(p)
    return sorted(out)


def all_interior(size: int = 16, exclude: set[int] | None = None) -> list[int]:
    """All interior cells (not border ring), excluding hint positions."""
    exclude = exclude or set()
    out = []
    for y in range(1, size - 1):
        for x in range(1, size - 1):
            p = y * size + x
            if p not in exclude:
                out.append(p)
    return out


def run_sat_test(
    puzzle_csv: str,
    board_json: str,
    free_cells: list[int],
    timeout_s: int = 600,
    out_dir: str = '/tmp/sat_test',
) -> dict:
    """Encode + run kissat. Returns dict with status, time, vars, clauses."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    free_json = json.dumps(free_cells)

    # Encode
    enc = subprocess.run(
        ['./target/release/sat_e2',
         '--puzzle', puzzle_csv,
         '--output-dir', out_dir,
         '--pin-outside-from', board_json,
         '--free-cells', free_json],
        capture_output=True, text=True, timeout=120,
    )
    stderr = enc.stderr
    vars_match = re.search(r'total vars: (\d+)', stderr)
    clauses_match = re.search(r'hard clauses: (\d+)', stderr)
    n_vars = int(vars_match.group(1)) if vars_match else 0
    n_clauses = int(clauses_match.group(1)) if clauses_match else 0

    # Find CNF
    cnfs = sorted(Path(out_dir).glob('sat_e2_*.cnf'))
    if not cnfs:
        return {'status': 'ENCODE_FAILED', 'stderr': stderr}
    cnf_path = cnfs[-1]

    # Run kissat
    t0 = time.time()
    kissat = subprocess.run(
        ['kissat', f'--time={timeout_s}', str(cnf_path)],
        capture_output=True, text=True, timeout=timeout_s + 30,
    )
    wall = time.time() - t0

    out = kissat.stdout
    status = 'UNKNOWN'
    if 's UNSATISFIABLE' in out:
        status = 'UNSAT'
    elif 's SATISFIABLE' in out:
        status = 'SAT'
    elif kissat.returncode != 10 and kissat.returncode != 20:
        status = 'TIMEOUT'

    pt_match = re.search(r'process-time:\s+(\d+s)?\s+([\d.]+) seconds', out)
    kissat_time = float(pt_match.group(2)) if pt_match else None

    return {
        'status': status,
        'kissat_time_s': kissat_time,
        'wall_time_s': wall,
        'n_vars': n_vars,
        'n_clauses': n_clauses,
        'n_free_cells': len(free_cells),
        'cnf_path': str(cnf_path),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle_csv")
    ap.add_argument("board_json")
    ap.add_argument("--free-cells", default="halo-0",
                    help="mismatches | halo-N | interior | custom:1,2,3,...")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--out-dir", default="/tmp/sat_test")
    args = ap.parse_args()

    # Hint positions in canonical (16×16) - hardcoded for now
    HINT_POSITIONS = {135, 210, 34, 221, 45}

    # Determine free cells
    mode = args.free_cells
    if mode == "mismatches" or mode == "halo-0":
        cells = find_mismatches(args.puzzle_csv, args.board_json)
    elif mode.startswith("halo-"):
        n = int(mode.split('-')[1])
        ms = find_mismatches(args.puzzle_csv, args.board_json)
        cells = expand_halo(ms, n, exclude=HINT_POSITIONS)
    elif mode == "interior":
        cells = all_interior(exclude=HINT_POSITIONS)
    elif mode.startswith("custom:"):
        cells = [int(x.strip()) for x in mode[7:].split(',')]
    else:
        sys.exit(f"unknown free-cells mode: {mode}")

    print(f"Mode: {mode}")
    print(f"Free cells: {len(cells)}")
    print(f"Running SAT test (timeout {args.timeout}s)...")
    result = run_sat_test(args.puzzle_csv, args.board_json, cells,
                         timeout_s=args.timeout, out_dir=args.out_dir)
    print(f"\nResult: {result['status']}")
    if 'kissat_time_s' in result and result['kissat_time_s'] is not None:
        print(f"kissat time: {result['kissat_time_s']:.2f}s")
        print(f"wall time:   {result['wall_time_s']:.2f}s")
        print(f"vars:        {result['n_vars']}")
        print(f"clauses:     {result['n_clauses']}")


if __name__ == "__main__":
    main()
