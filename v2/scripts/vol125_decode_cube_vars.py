"""Quick: decode cube variable assignments by rebuilding the VarMap in Python.

This duplicates the Rust VarMap::build logic — we mirror cell_admits exactly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "w1_peps"))
from puzzle_loader import load_puzzle, BORDER

W = 16


def cell_class(pos):
    r, c = pos // W, pos % W
    if (r == 0 or r == W-1) and (c == 0 or c == W-1):
        return "corner"
    if r == 0 or r == W-1 or c == 0 or c == W-1:
        return "edge"
    return "interior"


def piece_class(p, pid):
    e = p.piece_edges(pid, 0)
    n = sum(1 for c in e if c == BORDER)
    if n == 2: return "corner"
    if n == 1: return "edge"
    return "interior"


def cell_admits(p, pos, pid, rot):
    r, c = pos // W, pos % W
    cc = cell_class(pos)
    if piece_class(p, pid) != cc: return False
    e = p.piece_edges(pid, rot)
    if r == 0 and e[0] != BORDER: return False
    if r == W-1 and e[2] != BORDER: return False
    if c == 0 and e[3] != BORDER: return False
    if c == W-1 and e[1] != BORDER: return False
    if r != 0 and e[0] == BORDER: return False
    if r != W-1 and e[2] == BORDER: return False
    if c != 0 and e[3] == BORDER: return False
    if c != W-1 and e[1] == BORDER: return False
    return True


def build_var_map(p):
    var_to_cpr = []
    cell_to_vars = {pos: [] for pos in range(W*W)}
    for pos in range(W*W):
        for pid in range(p.n_pieces):
            for rot in range(4):
                if cell_admits(p, pos, pid, rot):
                    v = len(var_to_cpr) + 1
                    var_to_cpr.append((pos, pid, rot))
                    cell_to_vars[pos].append(v)
    return var_to_cpr, cell_to_vars


def main():
    p = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))
    var_to_cpr, cell_to_vars = build_var_map(p)
    print(f"n_piece_vars = {len(var_to_cpr)}")

    for cell in [0, 1, 2, 3, 4, 15, 16]:
        print(f"\ncell {cell}: {len(cell_to_vars[cell])} candidates "
              f"(first 5 vars: {cell_to_vars[cell][:5]})")
        for v in cell_to_vars[cell][:3]:
            pos, pid, rot = var_to_cpr[v-1]
            e = p.piece_edges(pid, rot)
            print(f"  var {v} -> cell {pos}, piece {pid}, rot {rot}, edges N,E,S,W={e}")

    # Decode cube 0: (5, 61, 117, 173)
    print(f"\nCube 0 assignments:")
    for v in [5, 61, 117, 173]:
        pos, pid, rot = var_to_cpr[v-1]
        e = p.piece_edges(pid, rot)
        print(f"  var {v} -> cell {pos}, piece {pid}, rot {rot}, edges N,E,S,W={e}")


if __name__ == "__main__":
    main()
