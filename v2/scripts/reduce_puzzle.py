#!/usr/bin/env python3
# Lossy puzzle reduction — find forced piece pairs.
#
# Two interior pieces (P, Q) are a "forced pair" if:
#   there exists a color c and a side s such that
#     P has c on side s AND Q has c on side opposite(s)
#     AND no OTHER piece has color c on side opposite(s) (under any rotation).
#
# Then placing P with c facing s forces Q adjacent on the opposite side.
# Equivalently: count the number of (piece, rotation) tuples that have color c
# on side opposite(s); if exactly one, it's forced.
#
# More general: a piece-side "supply" of (color, side) is the number of
# (piece, rotation) combinations exposing color c on side s. If supply
# is 1, then that color-side pairing is forced.

import csv
import sys
from pathlib import Path
from collections import Counter, defaultdict

V2_ROOT = Path(__file__).resolve().parents[1]
PUZZLE_CSV = V2_ROOT.parent / "data/puzzles/size_16_official_eternity.csv"

BORDER = 0

def parse_color(bits16: str) -> int:
    v = int(bits16, 2)
    return 65535 if v == 65535 else v  # BORDER sentinel

def is_border_sentinel(c): return c == 65535

def load_pieces(path):
    pieces = []
    with path.open() as f:
        for row in csv.reader(f):
            if len(row) < 4:
                continue
            n = parse_color(row[0])
            e = parse_color(row[1])
            s = parse_color(row[2])
            w = parse_color(row[3])
            pieces.append((n, e, s, w))
    return pieces

# After rotation r, the piece's sides cycle: rotation 1 (CW90) means the
# side that WAS on N is now on E. So:
#   board_side[k after rotation r] = piece[(k - r) mod 4]
def rotated_sides(piece, r):
    return (piece[(0 - r) % 4], piece[(1 - r) % 4], piece[(2 - r) % 4], piece[(3 - r) % 4])

def main():
    pieces = load_pieces(PUZZLE_CSV)
    print(f"# loaded {len(pieces)} pieces")

    # Supply: for each (color, side), how many (piece_id, rotation) tuples
    # expose that color on that board-side?
    supply = defaultdict(list)  # (color, side) -> [(piece_id, rot), ...]
    for pid, p in enumerate(pieces):
        for r in range(4):
            sides = rotated_sides(p, r)
            for s in range(4):
                c = sides[s]
                if is_border_sentinel(c):
                    continue
                supply[(c, s)].append((pid, r))

    # Print supply distribution
    print()
    print("## Supply distribution: how many color-side options exist")
    bins = Counter(len(v) for v in supply.values())
    for n in sorted(bins):
        print(f"  supply={n}: {bins[n]} (color,side) pairs")

    # For each color c, look at supply per side
    print()
    print("## Forced pairings (supply == 1 on opposite side)")
    print("color | side | supplier piece+rot")
    forced = []
    for (c, s), opts in sorted(supply.items()):
        if len(opts) == 1:
            forced.append((c, s, opts[0]))
            print(f"  c={c:>2} side={s} | {opts[0]}")
    print(f"  total forced: {len(forced)}")

    # The interesting reduction: for color c with supply 1 on the WEST side,
    # any piece that has c on its EAST side will FORCE the unique supplier
    # adjacent to its east. Count such (consumer, side) pairs.
    print()
    print("## Forced-pair counting")
    print("  for each forced (c, side=W=3) → list (consumer piece, consumer-rotation):")
    # Mapping: when piece A has color c on east side, the cell to A's east
    # must contain a piece with c on its west side. If supply for c on west = 1,
    # then that placement is forced.
    pair_count = 0
    side_opp = {0: 2, 1: 3, 2: 0, 3: 1}  # N↔S, E↔W
    forced_consumers = defaultdict(list)  # (c, consumer_side) -> [(producer_pid, producer_rot), (consumer_pid, consumer_rot)]
    for (c, opp_s), opts in supply.items():
        if len(opts) != 1:
            continue
        producer_pid, producer_rot = opts[0]
        # The CONSUMER side is opposite of opp_s.
        consumer_side = side_opp[opp_s]
        # Count how many (piece, rotation) consume c on consumer_side
        consumers = supply.get((c, consumer_side), [])
        # Note: producer itself might appear as a consumer if its sides match weirdly; filter
        consumers_filt = [(pid, rot) for (pid, rot) in consumers if pid != producer_pid]
        if not consumers_filt:
            continue
        forced_consumers[(c, opp_s, producer_pid, producer_rot)] = consumers_filt
        pair_count += len(consumers_filt)
    print(f"  potential forced placements: {pair_count}")
    # Categorize by # consumers
    cons_hist = Counter(len(v) for v in forced_consumers.values())
    print(f"  distribution of #consumers per supplier: {dict(cons_hist)}")
    print()
    # Pretty-print the top forced suppliers (supply on producer side = 1, consumers also = 1 or 2)
    print("## Mutually-forced pairs (BOTH supply == 1)")
    print("  (c, opp_s, producer_pid_rot, consumer_pid_rot)")
    mutual = 0
    for (c, opp_s, producer_pid, producer_rot), consumers in forced_consumers.items():
        if len(consumers) == 1:
            mutual += 1
            consumer_pid, consumer_rot = consumers[0]
            print(f"  c={c:>2} prod_side={opp_s} producer=(pid={producer_pid:>3}, rot={producer_rot}) consumer=(pid={consumer_pid:>3}, rot={consumer_rot})")
    print(f"  total mutually forced: {mutual}")

if __name__ == "__main__":
    main()
