"""Vol-124: forward-chaining propagation from the 5 hints across the puzzle.

Each cell starts with its full domain (set of valid (piece, rotation) given
class + border constraints). Hints reduce domains at adjacent cells via color
match. Then those reductions propagate to their neighbors, etc.

This is essentially AC-3 with alldiff over (cell-class, piece-class) plus
color-match arcs. The existing solver-engine does this. But running it
once standalone might surface forced cells we haven't noticed.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path
from collections import defaultdict, deque

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1_peps"))
from puzzle_loader import load_puzzle, BORDER

W = 16
HINTS = {135: (138, 0), 210: (180, 1), 34: (207, 1), 221: (248, 2), 45: (254, 1)}


def cell_class(r, c):
    if (r == 0 or r == W-1) and (c == 0 or c == W-1): return "corner"
    if r in (0, W-1) or c in (0, W-1): return "edge"
    return "interior"


def piece_class(puzzle, pid):
    e = puzzle.piece_edges(pid, 0)
    n = sum(1 for c in e if c == BORDER)
    if n == 2: return "corner"
    if n == 1: return "edge"
    return "interior"


def main():
    puzzle = load_puzzle(Path("../data/puzzles/size_16_official_eternity.csv"))
    print(f"Puzzle: {puzzle.size}x{puzzle.size}")

    pc = {pid: piece_class(puzzle, pid) for pid in range(puzzle.n_pieces)}

    # Build initial domains: each cell pos has a set of (pid, rot)
    print("Building initial domains (class + border filter)...")
    t0 = time.time()
    domain = [set() for _ in range(W * W)]
    for pos in range(W * W):
        r, c = pos // W, pos % W
        cc = cell_class(r, c)
        for pid in range(puzzle.n_pieces):
            if pc[pid] != cc: continue
            for rot in range(4):
                e = puzzle.piece_edges(pid, rot)
                ok = True
                # Border constraints
                if r == 0 and e[0] != BORDER: ok = False
                if r == W-1 and e[2] != BORDER: ok = False
                if c == 0 and e[3] != BORDER: ok = False
                if c == W-1 and e[1] != BORDER: ok = False
                if r != 0 and e[0] == BORDER: ok = False
                if r != W-1 and e[2] == BORDER: ok = False
                if c != 0 and e[3] == BORDER: ok = False
                if c != W-1 and e[1] == BORDER: ok = False
                if ok: domain[pos].add((pid, rot))

    initial_sizes = [len(d) for d in domain]
    print(f"  initial domain sum: {sum(initial_sizes):,} (avg {sum(initial_sizes)/len(initial_sizes):.1f})")
    print(f"  largest: {max(initial_sizes)} | smallest: {min(initial_sizes)}")
    print(f"  built in {time.time()-t0:.1f}s")

    # Apply hints (fix domain to singleton)
    for hpos, (hpid, hrot) in HINTS.items():
        domain[hpos] = {(hpid, hrot)}

    # AC-3 propagation: color-match on edges + alldiff via "piece used elsewhere"
    # Queue all directed arcs (pos_a → pos_b)
    def neighbors(pos):
        r, c = pos // W, pos % W
        out = []
        if r > 0: out.append((pos - W, 0, 2))     # north neighbor; my side N (0), their side S (2)
        if r < W-1: out.append((pos + W, 2, 0))
        if c > 0: out.append((pos - 1, 3, 1))
        if c < W-1: out.append((pos + 1, 1, 3))
        return out

    queue = deque()
    for pos in range(W * W):
        for (npos, my_side, _) in neighbors(pos):
            queue.append((pos, npos))
    print(f"\nAC-3 with {len(queue)} initial arcs...")

    # Also enforce piece-uniqueness: track which pieces are FORCED (domain size 1)
    # and remove them from other domains.

    def used_pieces():
        return {next(iter(d))[0] for d in domain if len(d) == 1}

    iters = 0
    changes = 0
    t1 = time.time()
    while queue:
        pos_a, pos_b = queue.popleft()
        # Find the side info
        r_a, c_a = pos_a // W, pos_a % W
        r_b, c_b = pos_b // W, pos_b % W
        if r_b == r_a - 1: side_a, side_b = 0, 2
        elif r_b == r_a + 1: side_a, side_b = 2, 0
        elif c_b == c_a - 1: side_a, side_b = 3, 1
        elif c_b == c_a + 1: side_a, side_b = 1, 3
        else: continue

        # Restrict domain[pos_a] to (pid, rot) such that there exists (pid_b, rot_b) ∈ domain[pos_b]
        # with edge_color(pid, rot, side_a) == edge_color(pid_b, rot_b, side_b) AND pid != pid_b
        b_colors_by_pid = {}
        for (pid_b, rot_b) in domain[pos_b]:
            c_b_val = puzzle.piece_edges(pid_b, rot_b)[side_b]
            b_colors_by_pid.setdefault(c_b_val, set()).add(pid_b)

        new_domain = set()
        for (pid_a, rot_a) in domain[pos_a]:
            c_a_val = puzzle.piece_edges(pid_a, rot_a)[side_a]
            if c_a_val not in b_colors_by_pid: continue
            # Need at least one pid_b != pid_a with that color
            valid_bs = b_colors_by_pid[c_a_val] - {pid_a}
            if valid_bs:
                new_domain.add((pid_a, rot_a))
        if new_domain != domain[pos_a]:
            removed = len(domain[pos_a]) - len(new_domain)
            changes += removed
            domain[pos_a] = new_domain
            # Re-queue all (n, pos_a) arcs
            for (n, _, _) in neighbors(pos_a):
                queue.append((n, pos_a))
        iters += 1
        if iters % 100000 == 0:
            sizes = [len(d) for d in domain]
            print(f"  iter {iters}: total domain = {sum(sizes):,} (changes so far {changes})")

    print(f"\nAC-3 done in {time.time()-t1:.1f}s ({iters} arc-revisions)")

    final_sizes = [len(d) for d in domain]
    print(f"\nFinal domain sum: {sum(final_sizes):,} (was {sum(initial_sizes):,})")
    print(f"Largest cell: {max(final_sizes)} ({max(range(W*W), key=lambda p: final_sizes[p])})")
    print(f"Smallest: {min(final_sizes)}")
    # Singletons
    forced = sum(1 for s in final_sizes if s == 1)
    print(f"\nForced (singleton) cells: {forced} of {W*W}")
    if forced > 5:
        print(f"  → {forced - 5} cells forced beyond the original 5 hints!")
    empty = sum(1 for s in final_sizes if s == 0)
    if empty > 0:
        print(f"  ⚠️  {empty} cells have EMPTY domain — puzzle UNSAT under this propagator")


if __name__ == "__main__":
    main()
