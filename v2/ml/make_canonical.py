#!/usr/bin/env python3
"""
Make-canonical: take a record board (sparse format) where some hint pieces
are displaced, drop the displaced positions + the canonical hint positions,
add canonical hints, and emit a partial that prune_restart can fill.

Usage: make_canonical.py INPUT.json OUTPUT.json
"""
import json
import sys

# Canonical 5-clue E2 hints + canonical rotations.
# Hint rotations are NOT publicly documented to me in the codebase; use the
# rotations from any existing valid canonical record (e.g. the make_canonical
# v1 output saved at vol-36 from prune_restart, which CP-completed at rot 1
# for 210 and rot 0 for 221). 34, 45, 135 use the rotations vol-32 had
# (which were canonical-honored: 34→pid207, 45→pid254, 135→pid138).
# Canonical 5-clue E2 hints (pos: (piece_id, rotation)).
# Rotations confirmed via prune_restart fill that produces valid completion.
CANONICAL = {
    34: (207, 1),
    45: (254, 1),
    135: (138, 0),
    210: (180, 1),
    221: (248, 2),
}

def main():
    if len(sys.argv) != 3:
        print("Usage: make_canonical.py INPUT OUTPUT", file=sys.stderr)
        sys.exit(1)
    in_path = sys.argv[1]
    out_path = sys.argv[2]

    d = json.load(open(in_path))
    placement = d['placement']

    # Determine format: dense (list of None|{piece_id, rotation}) or sparse ([{pos,piece_id,rotation}])
    is_sparse = bool(placement) and isinstance(placement[0], dict) and 'pos' in placement[0]
    if is_sparse:
        pos_to_pr = {p['pos']: (p['piece_id'], p['rotation']) for p in placement if p is not None}
    else:
        # dense: index = pos
        pos_to_pr = {i: (p['piece_id'], p['rotation']) for i, p in enumerate(placement) if p is not None}

    hint_pids = set(pid for pid, _ in CANONICAL.values())
    # Find where each hint piece is currently placed
    pid_to_current_pos = {}
    pid_to_current_rot = {}
    for pos, (pid, rot) in pos_to_pr.items():
        if pid in hint_pids:
            pid_to_current_pos[pid] = pos
            pid_to_current_rot[pid] = rot

    # Determine if canonical: each hint piece must already be at its canonical pos
    canonical_ok = all(
        pid_to_current_pos.get(pid) == pos
        for pos, (pid, _) in CANONICAL.items()
    )

    # Drop positions: any canonical hint position that has the WRONG piece,
    # AND any non-hint position currently holding a hint piece.
    to_drop = set()
    canonical_positions = set(CANONICAL.keys())
    for pos, (canonical_pid, _) in CANONICAL.items():
        actual = pos_to_pr.get(pos)
        if actual is None or actual[0] != canonical_pid:
            to_drop.add(pos)
    for pid in hint_pids:
        current_pos = pid_to_current_pos.get(pid)
        canonical_pos = [p for p, (q, _) in CANONICAL.items() if q == pid][0]
        if current_pos is not None and current_pos != canonical_pos:
            to_drop.add(current_pos)

    # For hint pieces that aren't placed at all, we can place them at their canonical position.
    # For hint positions we're now dropping, we want to add the canonical placement.
    # For non-hint positions we're dropping, we leave them as "to fill".

    # Build new placement:
    new_placement_sparse = []
    for pos, (pid, rot) in pos_to_pr.items():
        if pos in to_drop:
            continue
        new_placement_sparse.append({'pos': pos, 'piece_id': pid, 'rotation': rot})
    # Add canonical hints at their positions if dropped (or if missing)
    # Need rotation — use whatever the original record had at the canonical position,
    # OR if not present, use the rotation we found this piece at (which we shouldn't unless wrong),
    # OR fall back to 0 (CP can re-rotate via piece-rotation choice).
    # Simpler: for hint positions in to_drop, find the right rotation.
    # The hint piece's canonical rotation isn't loadable here; use the rotation from
    # the input record that placed this piece at its CURRENT (displaced) position.
    # CP will try all 4 rotations; pinning a SPECIFIC rotation forces only one.
    # For canonical compliance the rotation must be correct too. Without that info,
    # we can't pin canonical hints cleanly. Workaround: pin (pid, current_rot_from_input).
    # If current_rot is wrong, CP will fail the round.
    # Better: load the canonical hint rotations from the puzzle file.
    # For now, use the rotation from the original record's placement of this hint piece
    # (whether at canonical pos or displaced). If hint piece is missing from input
    # entirely, skip and let CP figure it out (drop the canonical pos too).

    for canonical_pos, (canonical_pid, canonical_rot) in CANONICAL.items():
        if canonical_pos not in to_drop:
            continue
        # Use the canonical rotation, not whatever the input had
        new_placement_sparse.append({'pos': canonical_pos, 'piece_id': canonical_pid, 'rotation': canonical_rot})

    # Verify uniqueness
    pids = [p['piece_id'] for p in new_placement_sparse]
    if len(set(pids)) != len(pids):
        from collections import Counter
        dupes = [p for p, c in Counter(pids).items() if c > 1]
        print(f"WARNING: duplicate pieces in output: {dupes}", file=sys.stderr)

    # Determine the cells that need filling: 256 - len(new_placement_sparse)
    n_filled = len(new_placement_sparse)
    n_to_fill = 256 - n_filled

    out = {'placement': new_placement_sparse}
    with open(out_path, 'w') as f:
        json.dump(out, f)

    print(f"input: {in_path}")
    print(f"  was canonical: {canonical_ok}")
    print(f"  pinned: {n_filled} cells")
    print(f"  to fill: {n_to_fill} cells")
    print(f"  dropped: {sorted(to_drop)}")
    print(f"output: {out_path}")

if __name__ == '__main__':
    main()
