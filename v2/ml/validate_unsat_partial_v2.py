"""Vol-34 T2 — validate an our-format partial against capiman's
unsat-clause database, using the full encoding map.

Encoding bridge:
  our (pos, our_pid, our_rot) → capiman (field, card, capiman_rot)
    where:
      field = pos  (vol-34 verified: same row-major layout)
      card = piece_card_map[our_pid]
      capiman_rot ∈ {1, 2, 3, 4} = ((our_rot + rotation_offset_per_pid[our_pid]) mod 4) + 1

Verified manually on field 0 (capiman corners at rot=1 → ours pid 0..3 at rot=0).

Usage:
  python ml/validate_unsat_partial_v2.py [forbidden_bin] [partial_json]
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path


def load_forbidden(path):
    """Parse UCP1 binary."""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"UCP1"
    n_lit = struct.unpack("<I", data[4:8])[0]
    n_col = struct.unpack("<I", data[8:12])[0]
    off = 12
    row_count = n_lit + 2
    row_starts = struct.unpack(f"<{row_count}I", data[off : off + row_count * 4])
    off += row_count * 4
    col = struct.unpack(f"<{n_col}I", data[off : off + n_col * 4])
    off += n_col * 4
    decoder_count = n_lit + 1
    decoder = []
    for i in range(decoder_count):
        field = data[off]
        pid = struct.unpack("<H", data[off + 1 : off + 3])[0]
        rot = data[off + 3]
        decoder.append((field, pid, rot))
        off += 4
    encoder = {}
    for lit, (f_, p, r) in enumerate(decoder):
        if lit == 0:
            continue
        encoder[(f_, p, r)] = lit
    return row_starts, col, decoder, encoder


def main():
    forbidden = sys.argv[1] if len(sys.argv) > 1 else "output/vol-33/forbidden_all.bin"
    partial = sys.argv[2] if len(sys.argv) > 2 else "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"

    print(f"[load] forbidden = {forbidden}")
    row_starts, col, decoder, encoder = load_forbidden(forbidden)
    print(f"[load] n_lit={len(decoder) - 1}, encoder entries={len(encoder)}")

    print("[load] encoding maps")
    color_map = {
        int(k): v for k, v in json.load(open("ml/data/color_map.json"))["our_to_capiman"].items()
    }
    pcm = json.load(open("ml/data/piece_card_map.json"))
    pid_to_card = {int(k): v for k, v in pcm["our_pid_to_cap_card"].items()}
    cap_rot_table = {int(k): v for k, v in pcm["cap_rot_for_our_rot"].items()}
    _ = color_map  # we don't need it for forbidden-lookup directly (just for piece-id)

    print(f"[load] partial = {partial}")
    with open(partial) as f:
        b = json.load(f)

    # Extract placements. Partials come in two formats:
    #   {placement: [{"piece_id": p, "rotation": r} or null, ...]}  (pt_e2 / alns_only)
    #   {cells: [[pid, rot] or null, ...]}  (DumpedBoard)
    placements = []
    if "placement" in b:
        for pos, c in enumerate(b["placement"]):
            if c is None:
                continue
            placements.append((pos, c["piece_id"], c["rotation"]))
    elif "cells" in b:
        for pos, c in enumerate(b["cells"]):
            if c is None:
                continue
            placements.append((pos, c[0], c[1]))
    else:
        raise SystemExit("unknown partial format (no placement/cells)")

    print(f"[partial] {len(placements)} placed cells")

    # Translate each (pos, our_pid, our_rot) → capiman (field, card, cap_rot).
    placed_literals = []
    not_in_encoder = 0
    for pos, our_pid, our_rot in placements:
        card = pid_to_card.get(our_pid)
        if card is None:
            print(f"  WARN: our_pid={our_pid} has no card map entry")
            continue
        cap_rot = cap_rot_table[our_pid][our_rot]
        if cap_rot is None:
            not_in_encoder += 1
            if not_in_encoder <= 3:
                print(f"  WARN: our_pid={our_pid} rot={our_rot} has no capiman rotation")
            continue
        # forbidden_all.bin stores card - 1 and rot - 1 (0-indexed); see
        # crates/ml-export/src/bin/unsat_clauses_load.rs:70.
        key = (pos, card - 1, cap_rot - 1)
        lit = encoder.get(key)
        if lit is None:
            not_in_encoder += 1
            if not_in_encoder <= 3:
                print(f"  WARN: ({pos}, card={card}, cap_rot={cap_rot}) not in encoder; our=(pos={pos}, pid={our_pid}, rot={our_rot})")
            continue
        placed_literals.append((lit, pos, our_pid, our_rot))

    print(f"[partial] {len(placed_literals)}/{len(placements)} placements found in encoder, {not_in_encoder} missing")

    # Check conflicts.
    placed_set = {lit for lit, _, _, _ in placed_literals}
    conflict_count = 0
    examples = []
    for lit, pos, pid, rot in placed_literals:
        s = row_starts[lit]
        e = row_starts[lit + 1]
        forbidden_for_lit = set(col[s:e])
        conflicts = placed_set & forbidden_for_lit
        conflicts.discard(lit)
        if conflicts:
            conflict_count += len(conflicts)
            if len(examples) < 5:
                other_lit = next(iter(conflicts))
                other = decoder[other_lit]
                examples.append((lit, (pos, pid, rot), other_lit, other))

    print(f"\n[result] conflict pairs: {conflict_count} (each pair counted twice, once per side)")
    for lit, ours, ol, other in examples:
        print(f"  CONFLICT: ours=lit{lit}@(pos={ours[0]},pid={ours[1]},rot={ours[2]}) vs cap=lit{ol}@(field={other[0]},card={other[1]},rot={other[2]})")

    if conflict_count == 0:
        print("PASS — all placed pieces are mutually compatible per the unsat database.")
    elif not_in_encoder > 0:
        print(f"PARTIAL — {not_in_encoder} placements missing from encoder; {conflict_count} conflicts among the rest.")
    else:
        print("FAIL — conflicts found among encoded placements.")


if __name__ == "__main__":
    main()
