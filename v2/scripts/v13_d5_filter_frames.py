#!/usr/bin/env python3
"""Vol-13 D5 — filter the vol-12 frame catalog by rare-color multiset.

The 75,173 valid 60-cell border frames from vol-12 are matched ALREADY
on every pair-wise adjacency (otherwise they wouldn't be valid frames).
We add the *global multiset* check: each rare color {1..5} must appear
exactly 12 times in the 60 ring-internal matchings.

The 60 ring-internal matchings are determined by the ordered piece list:
walking the ring, each consecutive pair contributes ONE matched color
(the shared edge). The two endpoints of that edge agree (it's a valid
frame).

Output:
- raw count of frames
- count surviving each per-color filter
- count surviving the joint {12,12,12,12,12} filter
- histograms of multiset deviations
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from v11_load_e2 import load


BORDER = 0
RARE = {1, 2, 3, 4, 5}


def piece_in_rotation(piece, rot):
    """Return the 4 edges (N, E, S, W) of `piece` after `rot` clockwise rotations.

    piece: tuple (T, R, B, L) as in pieces[i].
    """
    t, r, b, l = piece
    if rot == 0:
        return (t, r, b, l)
    elif rot == 1:
        return (l, t, r, b)
    elif rot == 2:
        return (b, l, t, r)
    elif rot == 3:
        return (r, b, l, t)


def compute_ring_matchings(frame_ring, pieces):
    """Walk the frame_ring (list of (piece_id, rotation)) around the 60
    border positions and return the 60 ring-internal matched colors.

    The ring positions in canonical order (clockwise starting at NW corner):
      0..15: top row (16 cells: 4 corners + 14 edges -- well, only NW and NE
             corners + 14 top edges)
      16..29: right col downward (14 right edges)
      30..45: bottom row reversed (NE -> NW bottom = 16 cells)
      46..59: left col upward (14 left edges)
    Total 60 cells. Layout: 4 corners + 56 edges.

    Adjacency: position i and position (i+1) % 60 are adjacent on the ring.
    The shared edge depends on which sides they touch.

    For positions 0..15 (top row), traveling LEFT->RIGHT, the shared edge
    between i and i+1 is the EAST of i / WEST of i+1.
    For 16..29 (right col top->bottom), the shared edge is SOUTH of i /
    NORTH of i+1.
    For 30..45 (bottom row right->left), shared edge is WEST of i / EAST
    of i+1.
    For 46..59 (left col bottom->top), shared edge is NORTH of i /
    SOUTH of i+1.
    Then 59 wraps to 0 (left col top cell back to NW corner): NORTH of
    59 / SOUTH of 0... wait, position 0 is NW corner and 59 is just below
    NW. So the matching is SOUTH of 0 / NORTH of 59? Actually moving
    around the ring CW, the last edge (59 -> 0) closes from the left col
    back to the top row.
    """
    n = len(frame_ring)
    assert n == 60, f"expected 60-cell ring, got {n}"

    # Orient each piece into its ring-canonical orientation already (it's
    # encoded in the (piece_id, rotation) tuple).
    cells = []
    for pid, rot in frame_ring:
        cells.append(piece_in_rotation(tuple(int(c) for c in pieces[pid]), rot))

    matchings = []

    # Top row positions 0..15: matching between i and i+1 is E of i = W of i+1
    for i in range(15):
        a, b = cells[i], cells[i + 1]
        e_of_a = a[1]
        w_of_b = b[3]
        assert e_of_a == w_of_b, f"unmatched at top {i}: E={e_of_a} W={w_of_b}"
        matchings.append(e_of_a)
    # Position 15 (NE corner) → 16 (right col top): S of 15 = N of 16
    a, b = cells[15], cells[16]
    matchings.append(a[2])
    # Right col 16..29 (14 cells): matching between i and i+1 is S of i = N of i+1
    for i in range(16, 29):
        a, b = cells[i], cells[i + 1]
        assert a[2] == b[0]
        matchings.append(a[2])
    # Position 29 → 30 (right col bottom → SE corner — wait, where is the corner?).
    # Let's verify ring length: top row (16) + right col after top corner (14)
    # + bottom row from SE (16) + left col after SW corner (14) = 60. Good.
    # So 16..29 are 14 right-col cells (no corner). Position 30 is SE corner.
    # Matching 29 → 30: S of 29 = N of 30.
    a, b = cells[29], cells[30]
    matchings.append(a[2])
    # Bottom row from SE (pos 30) going LEFT to SW: positions 30..45 (16 cells).
    # Walking right->left, the shared edge between pos i and pos i+1 is
    # W of i = E of i+1.
    for i in range(30, 45):
        a, b = cells[i], cells[i + 1]
        assert a[3] == b[1], f"unmatched at bottom {i}: W={a[3]} E={b[1]}"
        matchings.append(a[3])
    # Position 45 (SW corner) → 46 (left col bottom cell): N of 45 = S of 46
    a, b = cells[45], cells[46]
    matchings.append(a[0])
    # Left col 46..59 (14 cells), going bottom->top. Matching i → i+1 is
    # N of i = S of i+1.
    for i in range(46, 59):
        a, b = cells[i], cells[i + 1]
        assert a[0] == b[2]
        matchings.append(a[0])
    # Final wrap-around 59 → 0 (left col top cell → NW corner). N of 59 = S of 0.
    a, b = cells[59], cells[0]
    matchings.append(a[0])

    assert len(matchings) == 60, f"got {len(matchings)} matchings"
    return matchings


def main():
    e2 = load()
    pieces = e2['pieces']

    catalog_path = Path('output/v12_hamilton/frames_full.json')
    print(f"loading frame catalog {catalog_path} ...")
    t0 = time.time()
    with open(catalog_path) as f:
        cat = json.load(f)
    frames = cat['frames']
    print(f"  loaded {len(frames)} frames in {time.time()-t0:.2f}s")
    print(f"  catalog stats: {cat.get('stats', {})}")

    # Iterate frames, compute ring multisets
    t0 = time.time()
    surv_full = 0
    surv_per_color = {c: 0 for c in (1, 2, 3, 4, 5)}
    multiset_dev_sum = Counter()  # (deviation_from_12) histogram per color
    total_rare_per_frame = []
    examples = {'pass': [], 'fail_close': [], 'fail_far': []}
    for idx, frame in enumerate(frames):
        try:
            matchings = compute_ring_matchings(frame['ring'], pieces)
        except AssertionError as e:
            # frame is malformed — should not happen
            print(f"  WARNING frame {idx} malformed: {e}")
            continue

        c = Counter(matchings)
        total_rare = sum(c.get(r, 0) for r in (1, 2, 3, 4, 5))
        total_rare_per_frame.append(total_rare)

        passed_per_color = {}
        for col in (1, 2, 3, 4, 5):
            cnt = c.get(col, 0)
            passed_per_color[col] = (cnt == 12)
            if cnt == 12:
                surv_per_color[col] += 1
            multiset_dev_sum[(col, cnt - 12)] += 1

        if all(passed_per_color.values()):
            surv_full += 1
            if len(examples['pass']) < 3:
                examples['pass'].append((idx, dict(c)))
        else:
            # how far off?
            max_dev = max(abs(c.get(col, 0) - 12) for col in (1,2,3,4,5))
            if max_dev <= 2:
                if len(examples['fail_close']) < 3:
                    examples['fail_close'].append((idx, dict(c), max_dev))
            elif len(examples['fail_far']) < 3:
                examples['fail_far'].append((idx, dict(c), max_dev))

    elapsed = time.time() - t0
    n_total = len(frames)
    print(f"\nprocessed {n_total} frames in {elapsed:.1f}s ({n_total/elapsed:.0f}/s)")
    print(f"\nSURVIVAL UNDER {{12,12,12,12,12}} MULTISET FILTER:")
    print(f"  full multiset:      {surv_full:>6} / {n_total} ({100*surv_full/n_total:.3f}%)")
    for c, s in sorted(surv_per_color.items()):
        print(f"  count({c}) == 12:    {s:>6} / {n_total} ({100*s/n_total:.3f}%)")
    print(f"\nfilter speedup: {n_total / max(surv_full, 1):.1f}x reduction at frame layer")

    print(f"\nMULTISET DEVIATION DISTRIBUTION (color, count_minus_12, num_frames):")
    for (col, dev), cnt in sorted(multiset_dev_sum.items()):
        if cnt > 0:
            print(f"  color {col}: dev = {dev:>+3d}  → {cnt:>6} frames")

    if examples['pass']:
        print(f"\nEXAMPLE PASSING FRAMES (multiset {{12,12,12,12,12}}):")
        for idx, ms in examples['pass']:
            rare = {c: ms.get(c, 0) for c in (1,2,3,4,5)}
            print(f"  frame {idx}: rare = {rare}")
    if examples['fail_close']:
        print(f"\nEXAMPLE NEAR-MISS FRAMES (max dev ≤ 2):")
        for idx, ms, mdev in examples['fail_close']:
            rare = {c: ms.get(c, 0) for c in (1,2,3,4,5)}
            print(f"  frame {idx}: rare = {rare}  (max_dev={mdev})")
    if examples['fail_far']:
        print(f"\nEXAMPLE FAR-MISS FRAMES (max dev > 2):")
        for idx, ms, mdev in examples['fail_far']:
            rare = {c: ms.get(c, 0) for c in (1,2,3,4,5)}
            print(f"  frame {idx}: rare = {rare}  (max_dev={mdev})")


if __name__ == '__main__':
    main()
