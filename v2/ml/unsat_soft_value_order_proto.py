"""Vol-34 post-T2 — prototype the SOFT-pruner / value-order use of
capiman's unsat-clause database.

The hard-pruner version was refuted: capiman's "unsat" clauses are
heuristic-search-regime-specific (per-round), so using them as a
hard prune silently kills valid moves (e.g., 56 conflicts on the
vol-32 458 record board).

The soft version: rank candidate placements by their *unsat-distance*
from the already-placed pieces. For each candidate (pos, our_pid,
our_rot), count the already-placed pieces whose literal appears in
this candidate's forbidden-partner set. Lower count = "more compatible"
with the current partial → try first.

Measurement: take a deep partial (vol-34 T1 snapshot, ~200 cells
placed). For the position one beyond max_depth, rank ALL legal
candidates by unsat-distance and compare to the random / insertion
order baseline. Does the unsat-aware ranking put community-validated
moves earlier?

If yes (median rank of "good moves" ≤ baseline), the soft propagator
is worth a Rust port. If no, mark refuted.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path


def load_forbidden(path):
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
    forbidden_path = sys.argv[1] if len(sys.argv) > 1 else "output/vol-34/forbidden_round1.bin"
    partial_path = sys.argv[2] if len(sys.argv) > 2 else "output/vol-34/t1_probe/t00_s002_d207.json"

    print(f"[load] forbidden = {forbidden_path}")
    row_starts, col, decoder, encoder = load_forbidden(forbidden_path)
    print(f"[load] n_lit={len(decoder) - 1}, encoder entries={len(encoder)}")

    pcm = json.load(open("ml/data/piece_card_map.json"))
    pid_to_card = {int(k): v for k, v in pcm["our_pid_to_cap_card"].items()}
    cap_rot_table = {int(k): v for k, v in pcm["cap_rot_for_our_rot"].items()}

    def our_to_lit(pos, our_pid, our_rot):
        card = pid_to_card.get(our_pid)
        if card is None:
            return None
        cap_rot = cap_rot_table[our_pid][our_rot]
        if cap_rot is None:
            return None
        return encoder.get((pos, card - 1, cap_rot - 1))

    print(f"[load] partial = {partial_path}")
    b = json.load(open(partial_path))
    placement = b.get("placement") or []
    placed_literals = set()
    for pos, p in enumerate(placement):
        if p is None:
            continue
        lit = our_to_lit(pos, p["piece_id"], p["rotation"])
        if lit is not None:
            placed_literals.add(lit)
    print(f"[partial] {sum(1 for p in placement if p)} placed; {len(placed_literals)} have valid literals")

    # Pick the first unplaced position in row-major order.
    next_pos = next((p for p in range(256) if placement[p] is None), None)
    if next_pos is None:
        print("partial is fully placed")
        return
    print(f"[next-pos] {next_pos}")

    # Enumerate all (pid, rot) that are in capiman's encoder for this position
    # AND would be locally edge-matched (north + west match already-placed
    # neighbours). For prototype simplicity, just enumerate all encoder
    # entries at this field.
    candidates = []  # (our_pid, our_rot, lit, forbidden_partner_count)
    for our_pid, card in pid_to_card.items():
        for our_rot in range(4):
            lit = our_to_lit(next_pos, our_pid, our_rot)
            if lit is None:
                continue
            # Count placed literals in this lit's forbidden set
            s = row_starts[lit]
            e = row_starts[lit + 1]
            forbidden_for_lit = set(col[s:e])
            count = len(placed_literals & forbidden_for_lit)
            candidates.append((our_pid, our_rot, lit, count))

    print(f"[candidates] {len(candidates)} legal candidates at field {next_pos}")
    by_count = sorted(candidates, key=lambda x: x[3])
    print(f"[unsat-rank] top 10 candidates by ascending forbidden-partner count:")
    for c in by_count[:10]:
        print(f"  pid={c[0]:>3} rot={c[1]} → count={c[3]}")

    # Histogram of counts
    from collections import Counter
    hist = Counter(c[3] for c in candidates)
    print(f"\n[hist] forbidden-partner count distribution:")
    for k in sorted(hist):
        print(f"  count={k:>3}: {hist[k]} candidates")

    # The "ideal" candidate would be one matching what a 469-class solution
    # would place here. We don't have that ground truth from a 469 board,
    # but we DO have the vol-34 457 board which extends past this position.
    # Use it as a proxy for "what a high-scoring solution wants".
    ref_path = "output/vol-34/t3_signal/REAL_RECORD_TIE_457_vol34_t1signal_seed1.json"
    if Path(ref_path).exists():
        ref = json.load(open(ref_path))
        ref_pl = ref["placement"]
        ref_at = ref_pl[next_pos]
        if ref_at:
            print(f"\n[oracle] vol-34 457 board at pos {next_pos}: pid={ref_at['piece_id']}, rot={ref_at['rotation']}")
            rank = next((i for i, c in enumerate(by_count) if c[0] == ref_at['piece_id'] and c[1] == ref_at['rotation']), None)
            print(f"[oracle] in unsat-ranking, that candidate is at rank {rank} out of {len(candidates)}")
            if rank is not None:
                print(f"[oracle] percentile = {100*rank/len(candidates):.1f}% (lower = better)")


if __name__ == "__main__":
    main()
