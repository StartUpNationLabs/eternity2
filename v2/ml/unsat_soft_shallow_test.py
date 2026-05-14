"""Vol-34 follow-up — test SOFT-pruner at varying placement depths.

Hypothesis: capiman's unsat database is most discriminative at shallow
depths (where capiman's heuristic-rich search prunes harder); at deep
depths (200+) the database is too sparse to distinguish good from bad
moves.

Test: take the verified vol-32 458 board (256 cells, score 458) and
the vol-32 RECORD_TIE_457 boards. For each depth k ∈ {30, 50, 100,
150, 200}:
  - Build a "partial" by truncating the board to first k positions
  - At position k, enumerate all encoder candidates
  - Rank them by ascending forbidden-partner count
  - Record the rank of the "ground truth" candidate (what the
    record board placed at position k)
"""

from __future__ import annotations

import json
import struct
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
    row_starts, col, decoder, encoder = load_forbidden("output/vol-34/forbidden_round1.bin")
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

    record_paths = [
        ("vol-32 458 RECORD", "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json"),
        ("vol-34 457 verified", "output/vol-34/t3_signal/REAL_RECORD_TIE_457_vol34_t1signal_seed1.json"),
        ("vol-32 457 seed7", "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json"),
    ]
    depths = [30, 50, 80, 120, 160, 200]

    print(f"{'record':<32s} | " + " | ".join(f"d={d:>3} (rank/N, pct)" for d in depths))
    print("-" * 130)

    for label, path in record_paths:
        if not Path(path).exists():
            continue
        b = json.load(open(path))
        pl = b.get("placement") or []

        # Normalize: support {"pos": ..., "piece_id": ..., "rotation": ...} entries
        # or positional [{pid, rot}, ...]
        def at(pos):
            if pos >= len(pl) or pl[pos] is None:
                return None
            entry = pl[pos]
            if isinstance(entry, dict):
                return (entry["piece_id"], entry["rotation"])
            return None

        results = []
        for d in depths:
            # Build placed_literals from positions 0..d-1
            placed_lits = set()
            for p in range(d):
                pir = at(p)
                if pir is None:
                    continue
                lit = our_to_lit(p, pir[0], pir[1])
                if lit is not None:
                    placed_lits.add(lit)

            # Truth at position d
            truth = at(d)
            if truth is None:
                results.append("N/A")
                continue
            truth_lit = our_to_lit(d, truth[0], truth[1])
            if truth_lit is None:
                results.append("truth-not-in-encoder")
                continue

            # Rank candidates
            candidates = []
            for our_pid in range(256):
                for our_rot in range(4):
                    lit = our_to_lit(d, our_pid, our_rot)
                    if lit is None:
                        continue
                    s = row_starts[lit]
                    e = row_starts[lit + 1]
                    count = len(placed_lits & set(col[s:e]))
                    candidates.append((our_pid, our_rot, lit, count))
            candidates.sort(key=lambda x: (x[3], x[0], x[1]))
            rank = next((i for i, c in enumerate(candidates) if c[2] == truth_lit), None)
            N = len(candidates)
            if rank is None:
                results.append(f"truth-not-found")
            else:
                pct = 100 * rank / N
                results.append(f"{rank:>3}/{N:>3} ({pct:>5.1f}%)")
        print(f"{label:<32s} | " + " | ".join(f"{r:>18s}" for r in results))


if __name__ == "__main__":
    main()
