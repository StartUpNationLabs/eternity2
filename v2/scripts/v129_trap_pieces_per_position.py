#!/usr/bin/env python3
"""V129-T5 — Per-position trap-piece analysis.

For each board position, count which (piece_id, rotation) appears in
460+ boards but NEVER in 462+ boards. These are "TRAP PIECES" at that
position — the specific assignment that locks the basin.

Output: per position, top-3 trapped pieces, and per position the
piece-IDs that appear in any 462+ board (the "escape pieces").
"""

from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict, Counter

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "database-400-480"
OUT_DIR = REPO / "output/vol-129" / "trap_pieces_per_position"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W = 16
N_CELLS = 256
HIGH = 462
LOW = 460


def load_record(p):
    try: d = json.load(open(p))
    except: return None
    if not isinstance(d.get("matched"), int): return None
    pl = {}
    for i, pp in enumerate(d.get("placement", [])):
        if isinstance(pp, dict):
            pl[int(pp.get("pos", i))] = (int(pp["piece_id"]), int(pp["rotation"]))
    if len(pl) != N_CELLS: return None
    return d["matched"], pl


def main():
    records = [r for r in (load_record(p) for p in sorted(DB.glob("*.json"))) if r]
    print(f"Records: {len(records)}", flush=True)

    # per_pos_piece_count[pos][pid] = (count_low_only, count_high)
    per_pos = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # pos → (pid, rot) → [count_high, count_low]
    for matched, pl in records:
        bucket = 0 if matched >= HIGH else (1 if matched <= LOW else None)
        if bucket is None: continue
        for pos, (pid, rot) in pl.items():
            per_pos[pos][(pid, rot)][bucket] += 1

    # Per position: find pieces in HIGH and pieces in LOW-only.
    trap_pieces = {}  # pos → list of (pid, rot, count_low)
    escape_pieces = {}  # pos → list of (pid, rot, count_high)
    for pos in range(N_CELLS):
        prs = per_pos.get(pos, {})
        traps_here = []
        escapes_here = []
        for (pid, rot), (h, l) in prs.items():
            if h > 0:
                escapes_here.append((pid, rot, h))
            if h == 0 and l > 5:
                traps_here.append((pid, rot, l))
        traps_here.sort(key=lambda x: -x[2])
        escapes_here.sort(key=lambda x: -x[2])
        trap_pieces[pos] = traps_here
        escape_pieces[pos] = escapes_here

    # Stats.
    pos_with_traps = sum(1 for pos in range(N_CELLS) if trap_pieces[pos])
    pos_with_escapes = sum(1 for pos in range(N_CELLS) if escape_pieces[pos])
    print(f"Positions with ≥1 trap piece: {pos_with_traps}", flush=True)
    print(f"Positions with ≥1 escape piece (from 462+ board): {pos_with_escapes}", flush=True)

    # Top trap-heavy positions and their dominant trap pieces.
    by_trap = sorted(range(N_CELLS), key=lambda c: -sum(t[2] for t in trap_pieces[c]))
    print(f"\nTop 10 trap-heavy positions and their TOP trap pieces:", flush=True)
    print(f"{'pos':>4} {'r,c':>5}  TopTrap            TopEscape", flush=True)
    for pos in by_trap[:10]:
        r, c = pos // W, pos % W
        traps = trap_pieces[pos]
        escs = escape_pieces[pos]
        top_trap = traps[0] if traps else (None, None, 0)
        top_esc = escs[0] if escs else (None, None, 0)
        print(f"{pos:>4} ({r:>2d},{c:>2d})  p={top_trap[0]}r{top_trap[1]} cnt={top_trap[2]}    p={top_esc[0]}r{top_esc[1]} cnt={top_esc[2]}", flush=True)

    # Positions where ANY HIGH (462+) board's piece is DIFFERENT from the dominant LOW trap.
    # I.e., where switching from the trap piece to the escape piece is the move.
    print(f"\nTop 20 ESCAPE OPPORTUNITIES (pos where dominant trap != dominant escape):", flush=True)
    for pos in by_trap[:30]:
        traps = trap_pieces[pos]
        escs = escape_pieces[pos]
        if traps and escs:
            top_trap = traps[0]
            top_esc = escs[0]
            if top_trap[:2] != top_esc[:2]:
                r, c = pos // W, pos % W
                print(f"  pos={pos:>4} ({r:>2d},{c:>2d})  TRAP p={top_trap[0]}r{top_trap[1]} cnt={top_trap[2]}  →  ESCAPE p={top_esc[0]}r{top_esc[1]} cnt={top_esc[2]}", flush=True)

    # Save.
    out = {
        "n_records": len(records),
        "high_threshold": HIGH,
        "low_threshold": LOW,
        "n_positions_with_traps": pos_with_traps,
        "trap_pieces": {str(pos): [list(t) for t in trap_pieces[pos][:5]] for pos in range(N_CELLS)},
        "escape_pieces": {str(pos): [list(t) for t in escape_pieces[pos][:5]] for pos in range(N_CELLS)},
    }
    with open(OUT_DIR / "result.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT_DIR / 'result.json'}", flush=True)


if __name__ == "__main__":
    main()
