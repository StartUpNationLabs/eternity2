#!/usr/bin/env python3
"""Vol-122 J6 — Frontier-State Memoized CSP (FSMC) convergence-rate PoC.

User-proposed idea: many CSP paths diverge and CONVERGE on equivalent
partial states (same placed-piece set, same frontier color signature).
Measure how often this happens on a small puzzle (6×6).

If convergence rate ≥10%, the idea has legs — implement memoization
for real (multi-day project, ZDD-style).
If <1%, the state space is too sparse.

METHOD:
1. Load a small puzzle.
2. Do row-major CSP with the engine.
3. At every search-tree node, compute a canonical state key:
     - bitset of placed piece IDs
     - frontier color signature: colors of placed cells facing UN-placed neighbors
4. Hash-set of visited states; count how often we re-encounter the same key.

We use a Python recursive backtracker (slow but easy to instrument)
rather than instrument the Rust engine, since the question is about
state-graph structure, not raw speed.
"""

from __future__ import annotations
import sys
from collections import defaultdict
from pathlib import Path
from time import time


def parse_color(s):
    v = int(s.strip(), 2)
    return 0 if v == 65535 else v


def load_puzzle(csv_path):
    pieces = []
    with open(csv_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    for line in lines[1:]:
        cols = line.split(',')
        if len(cols) >= 4:
            try:
                pieces.append((parse_color(cols[0]), parse_color(cols[1]),
                               parse_color(cols[2]), parse_color(cols[3])))
            except ValueError:
                pass
    return pieces


def rotate(edges, rot):
    return tuple(edges[(i - rot) % 4] for i in range(4))


def all_rotations(piece):
    return [rotate(piece, r) for r in range(4)]


def is_valid_at(rotated, pos, side):
    """Border-side check: BORDER (0) edges must face boundary, non-0 face interior."""
    r, c = pos // side, pos % side
    top, right, bot, left = rotated
    if (r == 0) != (top == 0): return False
    if (r == side - 1) != (bot == 0): return False
    if (c == 0) != (left == 0): return False
    if (c == side - 1) != (right == 0): return False
    return True


def frontier_signature(board, side, pos_order, depth):
    """For each placed cell, list the colors facing UN-placed neighbors.
    Canonical: sorted list of (canonical_pos_id, side, color)."""
    placed_positions = set(pos_order[:depth])
    sig = []
    for pos in placed_positions:
        if pos not in board: continue
        r, c = pos // side, pos % side
        edges = board[pos]  # (T, R, B, L) rotated
        # Check 4 neighbors
        neighbors = [
            (r-1, c, 0, 2),  # north neighbor; my top edge; their bottom
            (r, c+1, 1, 3),  # east; my right; their left
            (r+1, c, 2, 0),  # south; my bottom; their top
            (r, c-1, 3, 1),  # west; my left; their right
        ]
        for nr, nc, my_side, their_side in neighbors:
            if 0 <= nr < side and 0 <= nc < side:
                npos = nr * side + nc
                if npos not in placed_positions:
                    sig.append((pos, my_side, edges[my_side]))
    sig.sort()
    return tuple(sig)


def canonical_state_key(placed_pids, sig):
    return (frozenset(placed_pids), sig)


def solve_with_memo(puzzle_path, max_nodes=200_000, time_budget_s=60):
    pieces = load_puzzle(puzzle_path)
    n = len(pieces)
    side = int(n ** 0.5)
    assert side * side == n, f"non-square puzzle ({n} pieces)"

    # Row-major scan order
    pos_order = list(range(n))

    # Pre-compute for each (cell, piece, rot) whether the placement is border-valid
    pieces_rot = {pid: all_rotations(pieces[pid]) for pid in range(n)}

    # State-graph stats
    state_visits = defaultdict(int)  # canonical_state_key -> # visits
    state_first_node_count = {}  # key -> nodes_visited at first encounter
    state_subtree_size = {}  # key -> nodes spent IN this subtree at first encounter
    nodes_visited = 0
    best_depth = 0
    convergences = 0  # number of times we re-visited a known state
    nodes_saved_by_memo = 0  # nodes we would have skipped with memoization
    visited_at_depth = defaultdict(int)
    revisits_at_depth = defaultdict(int)

    board = {}  # pos -> (rotated_edges, pid, rot)
    used_pids = set()
    t_start = time()

    def edge_compat(pos, rotated, board, side):
        """Check that placing rotated piece at pos matches already-placed neighbors."""
        r, c = pos // side, pos % side
        T, R, B, L = rotated
        # north neighbor
        if r > 0 and (npos := (r-1)*side + c) in board:
            if board[npos][0][2] != T: return False
        if r < side-1 and (npos := (r+1)*side + c) in board:
            if board[npos][0][0] != B: return False
        if c > 0 and (npos := r*side + c-1) in board:
            if board[npos][0][1] != L: return False
        if c < side-1 and (npos := r*side + c+1) in board:
            if board[npos][0][3] != R: return False
        return True

    def recurse(depth):
        nonlocal nodes_visited, best_depth, convergences, nodes_saved_by_memo
        nodes_visited += 1
        my_entry_count = nodes_visited
        if nodes_visited > max_nodes:
            return False
        if time() - t_start > time_budget_s:
            return False
        if depth > best_depth:
            best_depth = depth
        if depth == n:
            return True

        # Compute state key for current placed state
        placed_board_edges = {pos: v[0] for pos, v in board.items()}
        sig = frontier_signature(placed_board_edges, side, pos_order, depth)
        key = canonical_state_key(used_pids, sig)
        state_visits[key] += 1
        visited_at_depth[depth] += 1
        if state_visits[key] > 1:
            revisits_at_depth[depth] += 1
            convergences += 1
            # Count nodes saved: if we'd memoized, we'd skip the subtree this visit would
            # otherwise explore. Approximation: the FIRST visit's subtree size.
            saved = state_subtree_size.get(key, 0)
            nodes_saved_by_memo += saved
            # In a real memoized solver, we'd return cached result here.

        pos = pos_order[depth]
        for pid in range(n):
            if pid in used_pids: continue
            for rot in range(4):
                rotated = pieces_rot[pid][rot]
                if not is_valid_at(rotated, pos, side): continue
                if not edge_compat(pos, rotated, board, side): continue
                board[pos] = (rotated, pid, rot)
                used_pids.add(pid)
                if recurse(depth + 1):
                    return True
                del board[pos]
                used_pids.discard(pid)
        # Record subtree size for THIS state's first visit
        if state_visits[key] == 1:
            state_subtree_size[key] = nodes_visited - my_entry_count
        return False

    solved = recurse(0)
    elapsed = time() - t_start

    print(f"puzzle: {puzzle_path.name}  size {side}x{side}  pieces {n}")
    print(f"solved: {solved}  best_depth: {best_depth}/{n}  nodes_visited: {nodes_visited}  elapsed: {elapsed:.2f}s")
    print(f"unique states visited: {len(state_visits)}")
    print(f"total state-visit events: {sum(state_visits.values())}")
    print(f"convergence events (re-visits): {convergences}")
    if sum(state_visits.values()) > 0:
        conv_rate = convergences / sum(state_visits.values())
        print(f"convergence rate: {conv_rate * 100:.3f}%")
    print(f"NODES SAVED if memoized: {nodes_saved_by_memo} "
          f"({nodes_saved_by_memo / max(1, nodes_visited) * 100:.1f}% of total nodes)")

    print("\nPer-depth stats (depth, total_visits, revisits, rate):")
    for d in sorted(visited_at_depth):
        tv = visited_at_depth[d]
        rv = revisits_at_depth[d]
        rate = rv / tv * 100 if tv else 0
        if d < 5 or d > best_depth - 5 or rv > 0:
            print(f"  depth {d:3d}: visits={tv:8d} revisits={rv:8d} ({rate:6.2f}%)")

    # Top-10 most-revisited states
    top = sorted(state_visits.items(), key=lambda kv: -kv[1])[:10]
    print(f"\nTop 10 most-visited states (visit count):")
    for key, cnt in top:
        if cnt > 1:
            placed_count = len(key[0])
            print(f"  {cnt}× visits, placed_pieces={placed_count}, sig_len={len(key[1])}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default: try several small puzzles
        candidates = [
            "../data/generated/size_3_colors_2_6ffda29a.csv",
            "../data/generated/size_3_colors_4_1e7fe488.csv",
            "../data/generated/size_4_colors_2_56adf9a3.csv",
            "../data/generated/size_4_colors_3_8931df0a.csv",
            "../data/generated/size_4_colors_4_e2d68b48.csv",
            "../data/generated/size_5_colors_3_4ab6bb20.csv",
            "../data/generated/size_5_colors_4_3347f2df.csv",
            "../data/generated/size_6_colors_4_a45cd068.csv",
        ]
        for c in candidates:
            p = Path(c)
            if p.exists():
                print("=" * 70)
                solve_with_memo(p, max_nodes=500_000, time_budget_s=30)
                print()
    else:
        solve_with_memo(Path(sys.argv[1]), max_nodes=int(sys.argv[2]) if len(sys.argv) > 2 else 500_000)
