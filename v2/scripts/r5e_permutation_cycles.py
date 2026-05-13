#!/usr/bin/env python3
# R5e — permutation cycle decomposition.
#
# σ = oracle ∘ current^-1 as a permutation of cells (position-wise).
# Define σ(p) = oracle_pos_of_piece_at_current_p.
# Cycles of σ are the atomic units of an "applies-as-one" swap operator.

import sys
from pathlib import Path
sys.path.insert(0, "scripts")
import importlib.util
spec = importlib.util.spec_from_file_location("r5", "scripts/r5_mismatch_homology.py")
r5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(r5)

size, pieces = r5.load_puzzle(r5.PUZZLE_CSV)

def load(path):
    return r5.load_placement(Path(path).resolve(), size)[0]

def score(b):
    return r5.score_and_classify_edges(b, size, pieces)[0]

def apply_cycle_swap(board, oracle, cycle):
    # cycle is a list of positions [p0, p1, ..., pk-1] where the piece at p_i
    # should go to p_{i+1} (oracle says so). Implementation: pick up piece at
    # p0, place at p1's oracle rotation; the piece at p1 goes to p2; etc.
    # Equivalent to a coherent k-rotation in S_n.
    new = list(board)
    if len(cycle) < 2:
        return new
    # The piece at cycle[0] should go to cycle[1]'s oracle slot etc.
    # Actually: σ(p) = oracle target of the piece currently at p.
    # So cycle in σ means: piece at p0 belongs at σ(p0) = p1; piece at p1 belongs at p2; etc.
    # To realize: place (piece at p0, oracle_rot for p0_piece) at p1.
    # Capture pieces first
    saved = [board[p] for p in cycle]
    # oracle_rot for piece at cycle[i] is the rotation oracle has at the slot σ(cycle[i]) = cycle[i+1]
    # but we need oracle's (piece, rot) at cycle[i+1]: that's the piece that SHOULD be there.
    # We're moving piece originally at cycle[i] (saved[i]) to cycle[(i+1) % k] with rotation r.
    # The rotation we want is the oracle's rotation for that piece. The oracle says: at position cycle[(i+1) % k],
    # the correct piece is saved[i][0] with some rotation. Let's lookup oracle's piece→rotation:
    piece_rot_oracle = {}
    for pos, e in enumerate(oracle):
        if e is None: continue
        piece_rot_oracle[e[0]] = e[1]
    for i, p in enumerate(cycle):
        old_pid, old_rot = saved[i]
        if old_pid in piece_rot_oracle:
            new_rot = piece_rot_oracle[old_pid]
        else:
            new_rot = old_rot
        target = cycle[(i+1) % len(cycle)]
        new[target] = (old_pid, new_rot)
    return new

def main():
    if len(sys.argv) < 3:
        sys.exit("usage: r5e_permutation_cycles.py <current.json> <oracle.json>")
    cur = load(sys.argv[1])
    oracle = load(sys.argv[2])
    s_cur = score(cur); s_or = score(oracle)
    print(f"current: {s_cur}/480   oracle: {s_or}/480")
    # Map piece -> current_pos and piece -> oracle_pos
    cur_pos = {e[0]: pos for pos, e in enumerate(cur) if e is not None}
    ora_pos = {e[0]: pos for pos, e in enumerate(oracle) if e is not None}
    # σ on positions: σ(p) = ora_pos[piece at p]
    sigma = {p: ora_pos[cur[p][0]] for p in range(size * size) if cur[p] is not None}
    # Cycle decomposition
    seen = set()
    cycles = []
    for p in sorted(sigma.keys()):
        if p in seen: continue
        cyc = []
        q = p
        while q not in seen:
            seen.add(q); cyc.append(q); q = sigma[q]
        if len(cyc) >= 2:
            cycles.append(cyc)
    cycles.sort(key=len, reverse=True)
    print(f"\n# permutation cycles (length >= 2): {len(cycles)}")
    print("idx | len | cells")
    for i, c in enumerate(cycles[:30]):
        rows = sorted(set(p // size for p in c))
        rows_str = ",".join(str(r) for r in rows)
        print(f" {i:>2} | {len(c):>3} | rows={rows_str:<12}  e.g. positions {c[:8]}{'...' if len(c)>8 else ''}")

    # Now: for each cycle individually, what's the score gain if we apply ONLY it?
    print()
    print("# Apply each cycle in isolation; report score delta")
    print("idx | len | score after | delta")
    for i, c in enumerate(cycles):
        new = apply_cycle_swap(cur, oracle, c)
        s = score(new)
        print(f" {i:>2} | {len(c):>3} | {s:>3}/480 | {s - s_cur:+}")

    # Apply ALL cycles together
    print()
    new = list(cur)
    for c in cycles:
        new = apply_cycle_swap(new, oracle, c)
    s = score(new)
    print(f"# apply ALL {len(cycles)} cycles: {s}/480  (oracle = {s_or})")

if __name__ == "__main__":
    main()
