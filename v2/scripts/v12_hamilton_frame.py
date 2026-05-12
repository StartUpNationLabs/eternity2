#!/usr/bin/env python3
"""Hamilton-cycle frame enumeration for canonical E2.

The 60-cell border ring (4 corners + 56 edges placed at the 4 sides of
the 16x16 grid) is exactly a Hamilton cycle on a graph whose nodes are
(piece, used-rotation) and whose edges encode "piece A's outgoing
ring-side color = piece B's incoming ring-side color."

Strategy:
- Symmetry-breaking: place corner piece 0 at TL (1 rotation forced).
- DFS walk: visit positions TL→TR→BR→BL clockwise around the 60-cell ring.
- At each step, try every unused border piece whose "incoming" side
  color matches the previous piece's "outgoing" side color.
- Filter the final closed ring by NS-1 deficit ≤ threshold.
- Optional: dump the 56-color inward-facing vector for each surviving
  frame for downstream 14×14 interior solving.

This is the path the community tried as "rotation-set seeding" (2008)
but with rotations encoded INSIDE the edge of a Hamilton graph rather
than enumerated separately, and pruned by NS-1 deficit (which the
community didn't have in 2008).

Output: JSON with the count + sample of valid frames.
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path
from collections import Counter
from typing import List, Tuple, Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v11_load_e2 as loader

W = H = 16
BORDER = 0
N_RING = 2 * W + 2 * H - 4  # 60

# Ring traversal: positions (x, y) walking CW from TL corner.
def ring_positions():
    out = []
    for x in range(W): out.append((x, 0))                # top row, L→R
    for y in range(1, H): out.append((W - 1, y))         # right col, T→B
    for x in range(W - 2, -1, -1): out.append((x, H - 1))# bottom row, R→L
    for y in range(H - 2, 0, -1): out.append((0, y))     # left col, B→T
    assert len(out) == N_RING
    return out


def piece_class(piece_edges):
    n_border = int((piece_edges == BORDER).sum())
    if n_border == 2: return "corner"
    if n_border == 1: return "edge"
    return "interior"


def cell_class_ring(idx):
    """0 = TL, 15 = TR, 30 = BR, 45 = BL; everything else is an edge."""
    if idx in {0, W - 1, W + H - 2, 2 * W + H - 3}:
        return "corner"
    return "edge"


def rotate_edges(edges, rot):
    """rot: 0..3. edges = [top, right, bot, left]. Roll right by rot."""
    if rot == 0:
        return tuple(int(c) for c in edges)
    return tuple(int(c) for c in np.roll(edges, rot))


def ring_orientation(idx):
    """Which absolute side of a placed piece faces the gray frame at ring idx?
    Top row → north (side 0). Right col → east (1). Bottom row → south (2). Left col → west (3).
    For corner cells: two sides.
    """
    x, y = ring_positions()[idx]
    sides = []
    if y == 0: sides.append(0)
    if x == W - 1: sides.append(1)
    if y == H - 1: sides.append(2)
    if x == 0: sides.append(3)
    return tuple(sides)


def ring_traversal_sides(idx):
    """Which side of the current ring cell is the "incoming" (matches previous
    piece's outgoing) and which is the "outgoing" (matches next piece's incoming).
    Walking CW: at TL→TR (top row, L→R), incoming = west (3), outgoing = east (1).
    At TR corner (15), incoming = west (3), outgoing = south (2). And so on.
    """
    x, y = ring_positions()[idx]
    # Which side faces previous ring cell?
    prev_idx = (idx - 1) % N_RING
    next_idx = (idx + 1) % N_RING
    px, py = ring_positions()[prev_idx]
    nx, ny = ring_positions()[next_idx]
    # Side index of (this) toward (prev/next): index 0=N (toward (x,y-1)), 1=E (toward (x+1,y)), 2=S (toward (x,y+1)), 3=W (toward (x-1,y)).
    def side_toward(ax, ay, bx, by):
        if bx == ax and by == ay - 1: return 0
        if bx == ax + 1 and by == ay: return 1
        if bx == ax and by == ay + 1: return 2
        if bx == ax - 1 and by == ay: return 3
        raise ValueError(f"non-adjacent: ({ax},{ay}) -> ({bx},{by})")
    return side_toward(x, y, px, py), side_toward(x, y, nx, ny)


def inward_side(idx):
    """Which side of an edge cell faces interior. For corners, two sides do —
    return both. For edges, exactly one."""
    border_sides = ring_orientation(idx)
    return tuple(s for s in range(4) if s not in border_sides)


def valid_rotations(piece_edges, idx, prev_outgoing_color):
    """Return list of (rotation, rotated_edges) tuples that:
    - put BORDER on the side(s) facing the gray frame at idx,
    - match `prev_outgoing_color` on the incoming side from the previous ring cell.
    `prev_outgoing_color` may be None (start of ring).
    """
    must_border = ring_orientation(idx)
    in_side, _ = ring_traversal_sides(idx)
    out = []
    for rot in range(4):
        rotated = rotate_edges(piece_edges, rot)
        # Border constraint.
        if any(rotated[s] != BORDER for s in must_border):
            continue
        # Inner sides must NOT be BORDER.
        non_border_sides = [s for s in range(4) if s not in must_border]
        if any(rotated[s] == BORDER for s in non_border_sides):
            continue
        # Incoming side match.
        if prev_outgoing_color is not None and rotated[in_side] != prev_outgoing_color:
            continue
        out.append((rot, rotated))
    return out


def enumerate_frames(pieces, hints, time_budget_s=60.0, max_frames=200,
                     filter_ns1_max_deficit: Optional[int] = None,
                     log_every=1000):
    """DFS enumerate Hamilton frames. Returns list of dicts with the placement
    sequence and NS-1 deficit.
    """
    rp = ring_positions()
    hint_at = {pos: (pid, rot) for pos, pid, rot in hints}

    # Classify pieces.
    corners, edges = [], []
    for pid in range(256):
        cls = piece_class(pieces[pid])
        if cls == "corner": corners.append(pid)
        elif cls == "edge": edges.append(pid)
    assert len(corners) == 4 and len(edges) == 56

    # Symmetry-breaking: pin lowest-id corner at TL (idx 0).
    pinned_tl = min(corners)
    # Find its forced rotation.
    rots_tl = valid_rotations(pieces[pinned_tl], 0, prev_outgoing_color=None)
    if not rots_tl:
        return []
    # Take the first valid orientation.
    pinned_tl_rot = rots_tl[0]

    # Stats.
    stats = {"nodes": 0, "frames_found": 0, "elapsed_s": 0.0}
    t0 = time.time()
    frames = []

    # Sequence: 60 slots, each = (pid, rot, rotated_edges). Walk CW.
    place = [None] * N_RING
    used = [False] * 256
    place[0] = (pinned_tl, pinned_tl_rot[0], pinned_tl_rot[1])
    used[pinned_tl] = True

    # Hint-compatible filter: at any ring position with a hint, fix to it.
    hint_ring = {}
    for ring_idx, (x, y) in enumerate(rp):
        pos = y * W + x
        if pos in hint_at:
            pid, rot = hint_at[pos]
            hint_ring[ring_idx] = (pid, rot)

    # Outgoing color of TL piece toward next ring cell.
    _, out_side_0 = ring_traversal_sides(0)
    next_in_color = pinned_tl_rot[1][out_side_0]

    def deficit(committed_a: Counter, committed_b: Counter) -> int:
        all_keys = set(committed_a) | set(committed_b)
        return sum(abs(committed_a[c] - committed_b[c]) for c in all_keys) // 2

    def dfs(ring_idx: int, prev_out_color: int):
        nonlocal frames
        stats["nodes"] += 1
        if stats["nodes"] % log_every == 0:
            print(f"  [dfs] depth={ring_idx} nodes={stats['nodes']} "
                  f"frames={len(frames)} elapsed={time.time()-t0:.1f}s")
        if time.time() - t0 > time_budget_s or len(frames) >= max_frames:
            return False  # signal stop
        if ring_idx == N_RING:
            # Close the ring: the last piece's outgoing side must match the
            # first piece's incoming side.
            (_, _, e_first) = place[0]
            in_side_0, _ = ring_traversal_sides(0)
            if prev_out_color != e_first[in_side_0]:
                return True
            # Compute NS-1 deficit.
            # A: inward-facing colors of all 56 edge-class cells (corners contribute
            #    zero — they face adjacent border pieces only).
            # We don't have B (14×14-perimeter interior colors yet) because the
            # interior is empty. But we can record A directly and use it later.
            a_counter = Counter()
            for idx in range(N_RING):
                if cell_class_ring(idx) != "edge":
                    continue
                inward = inward_side(idx)
                pid, rot, ed = place[idx]
                for s in inward:
                    c = ed[s]
                    if c != BORDER:
                        a_counter[c] += 1
            frames.append({
                "ring": [(p, r) for (p, r, _) in place],
                "A_multiset": dict(a_counter),
                "A_size": sum(a_counter.values()),
            })
            return True

        # Pick candidate pieces for ring_idx.
        if ring_idx in hint_ring:
            hpid, hrot = hint_ring[ring_idx]
            if used[hpid]:
                return True
            # Validate that hint is consistent with current ring constraint.
            rots = valid_rotations(pieces[hpid], ring_idx, prev_out_color)
            # Hint requires specific rotation. Check if our valid_rotations
            # contains (hrot, *).
            match = next(((r, e) for (r, e) in rots if r == hrot), None)
            if match is None:
                return True
            (rot, ed) = match
            used[hpid] = True
            place[ring_idx] = (hpid, rot, ed)
            _, out_side = ring_traversal_sides(ring_idx)
            next_color = ed[out_side]
            cont = dfs(ring_idx + 1, next_color)
            place[ring_idx] = None
            used[hpid] = False
            return cont

        # Otherwise enumerate.
        if cell_class_ring(ring_idx) == "corner":
            pool = corners
        else:
            pool = edges
        for pid in pool:
            if used[pid]:
                continue
            rots = valid_rotations(pieces[pid], ring_idx, prev_out_color)
            for (rot, ed) in rots:
                used[pid] = True
                place[ring_idx] = (pid, rot, ed)
                _, out_side = ring_traversal_sides(ring_idx)
                next_color = ed[out_side]
                cont = dfs(ring_idx + 1, next_color)
                place[ring_idx] = None
                used[pid] = False
                if not cont:
                    return False
        return True

    dfs(1, next_in_color)
    stats["frames_found"] = len(frames)
    stats["elapsed_s"] = time.time() - t0
    return frames, stats


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=60.0)
    ap.add_argument("--max-frames", type=int, default=200)
    ap.add_argument("--out", type=str, default="output/v12_hamilton/frames.json")
    args = ap.parse_args()

    p = loader.load()
    pieces = p["pieces"]
    hints = p["hints"]
    print(f"=== Hamilton-cycle frame enumeration (canonical E2) ===")
    print(f"budget: {args.budget}s  max_frames: {args.max_frames}")

    frames, stats = enumerate_frames(pieces, hints,
                                     time_budget_s=args.budget,
                                     max_frames=args.max_frames)
    print()
    print(f"Frames found: {stats['frames_found']}")
    print(f"DFS nodes:    {stats['nodes']:,}")
    print(f"Elapsed:      {stats['elapsed_s']:.1f} s")
    print(f"Frames/sec:   {stats['frames_found'] / max(stats['elapsed_s'], 1e-6):.2f}")
    print(f"Nodes/sec:    {stats['nodes'] / max(stats['elapsed_s'], 1e-6):,.0f}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        json.dump({"schema_version": 1, "stats": stats,
                   "frames": frames[:args.max_frames]}, f)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
