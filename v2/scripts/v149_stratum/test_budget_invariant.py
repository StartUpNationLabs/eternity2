#!/usr/bin/env python3
"""V149-T3 — Test the per-color budget invariant on real partials.

For each board in database-400-480 (or a stratified sample), simulate
row-major DFS reaching that final state and check: at how many
intermediate depths does $U_c > R_c$ fire for ANY color c?

If 0% of partials trigger the invariant at any depth, the propagator
is vacuous on canonical (matching paths already obey it).

If e.g. 30% of partials trigger it at some depth, the propagator
catches 30% of paths early.
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_canonical_pieces(path):
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]
    size = int(lines[0])
    pieces = []
    for line in lines[1:]:
        parts = line.split(",")
        cw = lambda s: (lambda v: 0 if v == 65535 else v)(int(s.strip(), 2))
        t, r, b, l = cw(parts[0]), cw(parts[1]), cw(parts[2]), cw(parts[3])
        pieces.append((t, r, b, l))
    assert len(pieces) == size * size
    return size, pieces


def rotate(piece, r):
    n, e, s, w = piece
    arr = [n, e, s, w]
    return tuple(arr[(i + 4 - r) % 4] for i in range(4))


def load_board(path, size=16):
    """Return placement[pos] = (piece_id, rotation) or None."""
    with open(path) as f:
        d = json.load(f)
    pl = d.get("placement", [])
    out = [None] * (size * size)
    has_pos = any(isinstance(e, dict) and "pos" in e for e in pl)
    if has_pos:
        for e in pl:
            if isinstance(e, dict):
                out[int(e["pos"])] = (int(e["piece_id"]), int(e["rotation"]))
    else:
        for i, e in enumerate(pl):
            if isinstance(e, dict):
                out[i] = (int(e["piece_id"]), int(e["rotation"]))
    return out


def per_color_counts(pieces):
    """For each color c (1..22), |c| = total piece-set sides showing c."""
    counts = defaultdict(int)
    for p in pieces:
        for c in p:
            if c != 0:
                counts[c] += 1
    return counts


def simulate_row_major(placement, pieces, N, target_score=480):
    """Walk through placement in row-major order. At each depth,
    compute U_c and R_c for all colors. Return at which depth (if any)
    U_c > R_c fires."""
    abs_counts = per_color_counts(pieces)  # |c|

    # State trackers.
    U = defaultdict(int)  # color → # placed-sides pending
    M = defaultdict(int)  # color → # placed-sides matched (counted per side, so always even)
    X = defaultdict(int)  # color → # placed-sides mismatched
    used = [False] * len(pieces)

    fire_depths = []  # depths at which invariant fires

    for d in range(N * N):
        pos = d
        cell = placement[pos]
        if cell is None:
            return fire_depths, d  # incomplete board, stop here
        pid, rot = cell
        n, e, s, w = rotate(pieces[pid], rot)

        # Effect on U/M/X.
        # N side:
        if d >= N:
            # N-neighbor at pos - N is already placed.
            n_cell = placement[pos - N]
            if n_cell is None:
                pass  # weird; non-row-major or incomplete
            else:
                np_pid, np_rot = n_cell
                n_n, n_e, n_s, n_w = rotate(pieces[np_pid], np_rot)
                # N-neighbor's S faces our N.
                n_neigh_s_color = n_s
                # Update: that S was in U (pending). Now match or mismatch.
                if n_neigh_s_color != 0:
                    U[n_neigh_s_color] -= 1
                if n == n_neigh_s_color:
                    # Matched. Our N goes from "would be U" to M; neighbor's S goes from U to M.
                    if n != 0:
                        M[n] += 2  # both sides
                else:
                    # Mismatched.
                    if n != 0:
                        X[n] += 1
                    if n_neigh_s_color != 0:
                        X[n_neigh_s_color] += 1
        else:
            # OOB; N must be BORDER (or accept mismatch).
            pass

        # W side:
        if pos % N != 0:
            w_cell = placement[pos - 1]
            if w_cell is not None:
                wp_pid, wp_rot = w_cell
                w_n, w_e, w_s, w_w = rotate(pieces[wp_pid], wp_rot)
                w_neigh_e_color = w_e
                if w_neigh_e_color != 0:
                    U[w_neigh_e_color] -= 1
                if w == w_neigh_e_color:
                    if w != 0:
                        M[w] += 2
                else:
                    if w != 0:
                        X[w] += 1
                    if w_neigh_e_color != 0:
                        X[w_neigh_e_color] += 1

        # E side: enters U if E-neighbor in board.
        if pos % N != N - 1 and e != 0:
            U[e] += 1
        # S side: enters U if S-neighbor in board.
        if d < N * (N - 1) and s != 0:
            U[s] += 1

        # Piece is used; its 4 sides are removed from R.
        # R_c = |c| - M_c - X_c - U_c (conservation).
        # Check invariant U_c <= R_c, i.e., U_c <= |c| - M_c - X_c - U_c
        # i.e., 2*U_c + M_c + X_c <= |c|.
        used[pid] = True

        for c in range(1, 23):
            r_c = abs_counts[c] - M[c] - X[c] - U[c]
            if U[c] > r_c:
                fire_depths.append((d, c, U[c], r_c, M[c], X[c]))

    return fire_depths, N * N


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data/puzzles/size_16_official_eternity.csv"))
    ap.add_argument("--n-boards", type=int, default=20)
    args = ap.parse_args()

    size, pieces = load_canonical_pieces(args.puzzle)
    abs_counts = per_color_counts(pieces)
    print(f"[v149-t3] |c| per color: {dict(sorted(abs_counts.items()))}", flush=True)

    # First test on vanilla_fast snapshots (strict partials, no mismatches).
    snap_dir = REPO / "output/vol-56/snapshots"
    snaps = sorted(snap_dir.glob("*.json"))[:args.n_boards] if snap_dir.exists() else []
    if snaps:
        print(f"[v149-t3] testing on {len(snaps)} vanilla_fast snapshots (strict, X=0):", flush=True)
        snap_with_fire = 0
        snap_earliest_fire = None
        for sp in snaps:
            placement = load_board(sp, size=size)
            fires, last_depth = simulate_row_major(placement, pieces, size)
            if fires:
                snap_with_fire += 1
                f0 = fires[0]
                if snap_earliest_fire is None or f0[0] < snap_earliest_fire[0]:
                    snap_earliest_fire = f0
                print(f"  {sp.name}: max_placed={last_depth} first_fire @ depth={f0[0]} color={f0[1]} (U={f0[2]} R={f0[3]} M={f0[4]} X={f0[5]})", flush=True)
            else:
                print(f"  {sp.name}: max_placed={last_depth} no fire (= consistent with extending to 480)", flush=True)
        print()
        print(f"[v149-t3] strict-partial summary: {snap_with_fire}/{len(snaps)} fire; earliest={snap_earliest_fire}", flush=True)
        print()

    db = REPO / "database-400-480"
    boards = sorted(db.glob("*.json"))[:args.n_boards]
    print(f"[v149-t3] testing budget invariant on {len(boards)} ALNS-final boards", flush=True)

    total_fires = 0
    boards_with_fire = 0
    earliest_fire = None

    for bp in boards:
        placement = load_board(bp, size=size)
        fires, last_depth = simulate_row_major(placement, pieces, size)
        if fires:
            boards_with_fire += 1
            total_fires += len(fires)
            first_fire = fires[0]
            if earliest_fire is None or first_fire[0] < earliest_fire[0]:
                earliest_fire = first_fire
            score = int(bp.name.split("_")[0])
            print(f"  {bp.name[:50]}: score={score} first_fire @ depth={first_fire[0]} color={first_fire[1]} (U={first_fire[2]} R={first_fire[3]} M={first_fire[4]} X={first_fire[5]})", flush=True)
        else:
            score = int(bp.name.split("_")[0])
            print(f"  {bp.name[:50]}: score={score} no fire", flush=True)

    print()
    print(f"[v149-t3] summary:")
    print(f"  {boards_with_fire}/{len(boards)} boards have invariant fires")
    print(f"  total fires: {total_fires}")
    if earliest_fire:
        print(f"  earliest fire: depth={earliest_fire[0]} color={earliest_fire[1]} U={earliest_fire[2]} R={earliest_fire[3]}")
    print()
    print("INTERPRETATION:")
    print("  - If 0 boards fire → invariant vacuous on real boards.")
    print("  - If most boards fire at low depth → propagator could prune those entire subtrees.")
    print("  - Note: these are ALNS-final boards with mismatches (X_c > 0). For a strict-DFS partial")
    print("    (no mismatches), U_c <= R_c is necessary (= invariant always holds for 480-extendable).")
    print("    A fire means the board IS NOT 480-extendable — useful to confirm at score < 480.")


if __name__ == "__main__":
    main()
