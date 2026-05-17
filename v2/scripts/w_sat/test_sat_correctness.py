"""W-SAT correctness tests.

Validates that the SAT encoding correctly identifies SAT/UNSAT for
known instances.

Tests:
  T1. Empty pinning, no hints → SAT for any small puzzle (must have a solution).
  T2. Pin all cells from a verified 480/480 solution → SAT (trivially).
  T3. Pin all cells from a 459 board → UNSAT (any free? No, all pinned).
       Actually with 0 free cells, encoding is meaningless. Skip.
  T4. Pin all cells from a 480 perfect solution EXCEPT 1 cell → must
       SAT (just need to find that one piece-rotation that matches).
  T5. Pin from a 459 board, mismatch cells free → UNSAT (proven empirically).
  T6. Take a small solved puzzle (4×4), break ONE piece by swapping, pin
      others → SAT (must be able to put it back).
  T7. Take a 4×4 perfect, swap TWO disjoint pieces (genuine swap), pin
      the other 14 cells → SAT (the swap region must allow restoration).
  T8. Take a 4×4 with a known impossible constraint → UNSAT.
"""
from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path


PUZZLE_4X4 = "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/generated/size_4_colors_6_92cd6738.csv"
PUZZLE_16X16 = "/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/data/benchmark/size_16_official_eternity.csv"


def run_sat_test(puzzle, board_json, free_cells, timeout=60, out_dir='/tmp/sat_correctness_test'):
    """Encode + run kissat. Returns (status, time, info)."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    # Clean prev
    for f in Path(out_dir).glob("*.cnf"):
        f.unlink()

    free_json = json.dumps(free_cells)
    enc = subprocess.run(
        ['./target/release/sat_e2',
         '--puzzle', puzzle,
         '--output-dir', out_dir,
         '--pin-outside-from', board_json,
         '--free-cells', free_json],
        capture_output=True, text=True, timeout=120,
    )
    cnfs = sorted(Path(out_dir).glob('sat_e2_*.cnf'))
    if not cnfs:
        return 'ENCODE_FAILED', 0, enc.stderr[:500]

    cnf_path = cnfs[-1]
    t0 = time.time()
    kissat = subprocess.run(
        ['kissat', f'--time={timeout}', str(cnf_path)],
        capture_output=True, text=True, timeout=timeout + 30,
    )
    wall = time.time() - t0
    if 's UNSATISFIABLE' in kissat.stdout:
        return 'UNSAT', wall, ''
    elif 's SATISFIABLE' in kissat.stdout:
        return 'SAT', wall, ''
    else:
        return 'TIMEOUT', wall, kissat.stdout[-500:]


def make_board_json(placement, out_path):
    """Write a board JSON."""
    data = {
        'source': 'test',
        'placement': [{'pos': pos, 'piece_id': pid, 'rotation': rot}
                      for pos, (pid, rot) in sorted(placement.items())],
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(data))


def load_board_json(path):
    data = json.loads(Path(path).read_text())
    return {p['pos']: (p['piece_id'], p['rotation']) for p in data['placement']}


def main():
    results = []

    # T1: 4×4 perfect with 1 cell free → SAT (must find the missing piece)
    print("T1: 4×4 perfect board, 1 cell free → expected SAT")
    # First generate a 4×4 perfect via BP-decim (we know it works)
    if not Path('/tmp/test_4x4_perfect.json').exists():
        print("  generating 4x4 perfect via BP-decim...")
        subprocess.run([
            'python3', 'scripts/w2_sp/bp_decimation.py', PUZZLE_4X4,
            '--out', '/tmp/test_4x4_perfect.json'
        ], capture_output=True, timeout=30)
    if Path('/tmp/test_4x4_perfect.json').exists():
        status, wall, info = run_sat_test(PUZZLE_4X4, '/tmp/test_4x4_perfect.json',
                                          free_cells=[5])  # free cell 5 only
        print(f"  → {status} in {wall:.2f}s")
        results.append(('T1 4x4-perfect-1-free', 'SAT', status))
    else:
        print("  SKIP: couldn't generate 4×4 perfect")
        results.append(('T1', 'SAT', 'SKIPPED'))

    # T2: 4×4 perfect with 4 cells free → SAT
    if Path('/tmp/test_4x4_perfect.json').exists():
        print("\nT2: 4×4 perfect, 4 cells free → expected SAT")
        status, wall, info = run_sat_test(PUZZLE_4X4, '/tmp/test_4x4_perfect.json',
                                          free_cells=[5, 6, 9, 10])
        print(f"  → {status} in {wall:.2f}s")
        results.append(('T2 4x4-perfect-4-free', 'SAT', status))

    # T3: 4×4 perfect with all 16 cells free → SAT
    if Path('/tmp/test_4x4_perfect.json').exists():
        print("\nT3: 4×4 perfect, all 16 cells free → expected SAT")
        status, wall, info = run_sat_test(PUZZLE_4X4, '/tmp/test_4x4_perfect.json',
                                          free_cells=list(range(16)))
        print(f"  → {status} in {wall:.2f}s")
        results.append(('T3 4x4-perfect-all-free', 'SAT', status))

    # T4: 4×4 perfect with broken middle (1 cell wrong, free that cell + 1 other) → SAT
    if Path('/tmp/test_4x4_perfect.json').exists():
        print("\nT4: 4×4 BROKEN perfect (1 cell swapped to wrong piece), 2 cells free → expected SAT")
        # Load perfect, swap cell 5 and cell 6's pieces, save as broken
        perfect = load_board_json('/tmp/test_4x4_perfect.json')
        broken = dict(perfect)
        broken[5], broken[6] = broken[6], broken[5]
        make_board_json(broken, '/tmp/test_4x4_broken.json')
        status, wall, info = run_sat_test(PUZZLE_4X4, '/tmp/test_4x4_broken.json',
                                          free_cells=[5, 6])
        print(f"  → {status} in {wall:.2f}s")
        results.append(('T4 4x4-broken-2-free', 'SAT', status))

    # T5: 4×4 perfect with cell 0 corner placed WRONG and only that cell free → UNSAT
    # because the corner can't be filled with another piece-rotation that gives all border + matches
    # Actually corners have several valid options (4 corner pieces), so this might be SAT.
    # Pick a corner piece with WRONG rotation and free only that cell.
    if Path('/tmp/test_4x4_perfect.json').exists():
        print("\nT5: 4×4 perfect, with cell 0 piece rotated wrongly, FREE only cell 0 → expected UNSAT (only 4 rotation choices, only 1 right)")
        # NOTE: this doesn't really test UNSAT because corners have 4 piece options.
        # Skip this test — it's actually likely SAT.
        results.append(('T5', 'N/A', 'SKIPPED-not-clean-test'))

    # T6: 16×16 — pin a 459 board with halo-0 → expected UNSAT (empirically)
    print("\nT6: 16×16 459 board with halo-0 (32 mismatch cells free) → expected UNSAT")
    if Path('output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json').exists():
        cells = [28, 29, 59, 60, 76, 77, 78, 91, 92, 93, 94, 109, 110, 140, 141, 158, 172, 173, 174, 188, 189, 190, 204, 205, 206, 219, 220, 221, 222, 236, 237, 238]
        status, wall, info = run_sat_test(PUZZLE_16X16,
                                          'output/vol-60/RECORDS/RECORD_TIE_459_p06_corner_1_0_2_3_seed2.json',
                                          free_cells=cells)
        print(f"  → {status} in {wall:.2f}s")
        results.append(('T6 16x16-459-halo0', 'UNSAT', status))

    # T7: 16×16 — McGavin 469 with halo-0 → SAT means we found a 480!
    # Either the encoding has a bug, OR the McGavin board can be improved.
    print("\nT7: 16×16 McGavin 469 with halo-0 → empirically: SAT (need to verify is real)")
    if Path('output/vol-65/mcgavin_469.json').exists():
        # First get mismatch cells of McGavin
        ms = subprocess.run(['./target/release/mismatch_map', 'output/vol-65/mcgavin_469.json'],
                            capture_output=True, text=True)
        import re
        cells = set()
        for line in ms.stdout.split('\n'):
            if 'cluster' in line:
                for y, x in re.findall(r'\((\d+),(\d+)\)', line):
                    cells.add(int(y) * 16 + int(x))
        cells = sorted(cells)
        print(f"  McGavin 469 mismatch cells: {len(cells)}")
        status, wall, info = run_sat_test(PUZZLE_16X16,
                                          'output/vol-65/mcgavin_469.json',
                                          free_cells=cells)
        print(f"  → {status} in {wall:.2f}s")
        results.append(('T7 16x16-McGavin-469-halo0', '?', status))

    # T8: 4×4 perfect, cell 0 free, but PIECE PINNED ELSEWHERE so cell 0 can't have the correct piece → UNSAT
    if Path('/tmp/test_4x4_perfect.json').exists():
        print("\nT8: 4×4 perfect with piece-conflict (piece needed at cell 0 is pinned elsewhere) → expected UNSAT")
        # Load perfect, modify cell 1 to use cell 0's original piece. Pin cells 1-15.
        # Cell 0's only options are pieces matching corner + cell 1's W. If we steal cell 0's piece for cell 1, cell 0 is impossible.
        perfect = load_board_json('/tmp/test_4x4_perfect.json')
        # Find what's at cell 0
        cell0_piece, cell0_rot = perfect[0]
        cell1_piece, cell1_rot = perfect[1]
        # Move cell 0's piece to cell 1 (replacing existing). Now cell 0 has no piece (we'll free it).
        # cell 1 now has cell 0's piece — but we need ALL pieces used exactly once.
        # Better: swap cell 0 and cell 1's pieces. Then cell 0 has cell 1's piece (wrong rotation/edges).
        # Pin cell 1 to the perfect value, free cell 0. Cell 0's correct piece (cell0_piece) is NOT in any free cell.
        # Actually we need it to be PINNED ELSEWHERE so SAT can't use it.
        # Simplest: make cell 0 conflict — put cell0_piece at cell 1 (overwriting). Free cell 0.
        modified = dict(perfect)
        modified[1] = (cell0_piece, 0)  # put cell0's piece at cell 1 with rotation 0
        make_board_json(modified, '/tmp/test_4x4_conflict.json')
        status, wall, info = run_sat_test(PUZZLE_4X4, '/tmp/test_4x4_conflict.json',
                                          free_cells=[0])
        print(f"  → {status} in {wall:.2f}s")
        # cell 0's piece is at cell 1 (pinned); cell 0 must find another piece. The only choices for cell 0
        # are pieces 0/1/2/3 (corners), but cell 1 took one. Still 3 corners left → SAT.
        # Hmm not a clean UNSAT test.
        results.append(('T8 4x4-piece-conflict', '?', status))

    # Summary
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"{'Test':<40} {'Expected':<8} {'Got':<8}")
    print("-" * 60)
    for name, exp, got in results:
        ok = "✓" if exp == got else ("?" if exp == '?' or got == 'SKIPPED-not-clean-test' else "✗")
        print(f"{name:<40} {exp:<8} {got:<8} {ok}")


if __name__ == "__main__":
    main()
