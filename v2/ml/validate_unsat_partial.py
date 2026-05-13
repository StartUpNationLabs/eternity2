"""Vol-32 sanity check: do the placed pieces in a known-good partial
contradict the unsat-clause database?

If any placed pair (P1@F1@R1, P2@F2@R2) is in the forbidden set, the
database is wrong (those pairs DO co-exist in a valid prefix).
"""

import json
import struct
import sys
from pathlib import Path


def load_forbidden(path):
    """Parse the UCP1 binary format from unsat-clauses-load."""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"UCP1"
    n_lit = struct.unpack("<I", data[4:8])[0]
    n_col = struct.unpack("<I", data[8:12])[0]
    off = 12

    # row_starts: (n_lit + 2) u32
    row_count = n_lit + 2
    row_starts = struct.unpack(f"<{row_count}I", data[off:off + row_count * 4])
    off += row_count * 4

    # col: n_col u32
    col = struct.unpack(f"<{n_col}I", data[off:off + n_col * 4])
    off += n_col * 4

    # decoder: (n_lit + 1) records of 4 bytes each: u8 field, u16 pid_0idx, u8 rot_0idx
    decoder_count = n_lit + 1
    decoder = []
    for i in range(decoder_count):
        field = data[off]
        pid = struct.unpack("<H", data[off + 1:off + 3])[0]
        rot = data[off + 3]
        decoder.append((field, pid, rot))
        off += 4

    # Build encoder: (field, piece, rot) -> literal
    encoder = {}
    for lit, (f_, p, r) in enumerate(decoder):
        if lit == 0:
            continue
        encoder[(f_, p, r)] = lit
    return row_starts, col, decoder, encoder


def main():
    forbidden = sys.argv[1] if len(sys.argv) > 1 else "output/vol-33/forbidden_all.bin"
    partial = sys.argv[2] if len(sys.argv) > 2 else "output/vol-32/t4/edge_bp_165.json"

    print(f"[load] forbidden table from {forbidden}")
    row_starts, col, decoder, encoder = load_forbidden(forbidden)
    print(f"[load] n_lit={len(decoder)-1}, n_col={len(col)}, encoder_entries={len(encoder)}")

    print(f"[load] partial from {partial}")
    with open(partial) as f:
        b = json.load(f)

    # Extract placements
    placements = []
    for pos, c in enumerate(b.get("cells", [])):
        if c is None: continue
        if isinstance(c, list) and len(c) == 2:
            placements.append((pos, c[0], c[1]))
    print(f"[partial] {len(placements)} placed cells")

    # Look up each placement's literal
    placed_literals = []
    for pos, pid, rot in placements:
        lit = encoder.get((pos, pid, rot), None)
        if lit is None:
            print(f"  WARN: ({pos}, {pid}, {rot}) not in encoder — likely not in canonical set")
            continue
        placed_literals.append((lit, pos, pid, rot))
    print(f"[partial] {len(placed_literals)} placements have valid literals")

    # For each pair, check if either is in the other's forbidden set
    conflict_count = 0
    placed_set = {lit for lit, _, _, _ in placed_literals}
    for lit, pos, pid, rot in placed_literals:
        s = row_starts[lit]
        e = row_starts[lit + 1]
        forbidden_for_lit = set(col[s:e])
        # Intersect with other placed literals
        conflicts = placed_set & forbidden_for_lit
        conflicts.discard(lit)  # don't count self
        if conflicts:
            conflict_count += len(conflicts)
            # Sample one
            other_lit = next(iter(conflicts))
            other = decoder[other_lit]
            print(f"  CONFLICT: literal {lit} (pos={pos}, pid={pid}, rot={rot}) forbidden with literal {other_lit} (pos={other[0]}, pid={other[1]}, rot={other[2]})")
            if conflict_count > 20:
                print("  ... more conflicts; stopping enumeration")
                break

    print(f"\nTotal conflict pairs found: {conflict_count}")
    if conflict_count == 0:
        print("PASS: all placed pieces are compatible per the unsat-clause database.")
    else:
        print(f"FAIL: {conflict_count} conflicts — either the partial isn't actually valid, or the database has false positives.")


if __name__ == "__main__":
    main()
