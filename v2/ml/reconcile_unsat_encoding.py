"""Vol-32 → Vol-33 bootstrap: reconcile capiman/e2's literal encoding
with our v2 engine's (position, piece_id, rotation) convention.

This is a starter script — gets partway, leaves the rest as vol-33 work.
The fundamental finding (vol-32) was that capiman's color labels and
piece-id convention don't match ours; this script extracts both
encodings so vol-33 can build the equivalence map.

Steps:
  1. Parse our CSV: piece_id 0..255 with edges [top, right, bottom, left]
     in COLOR units (0=BORDER, 1..22=interior).
  2. Parse capiman's e2_info.c: card 0..255 with edges (N, E, S, W) at
     rot=1, in CAPIMAN COLOR units.
  3. Empirically map our colors → capiman colors via piece-set
     reconciliation:
       - corners share unique 2-border tuples
       - color-frequency distribution gives an initial signal
  4. Output: ml/data/color_map.json (our_color → capiman_color, both 0..22).

This is the gating step for vol-33 T1. Without it, the unsat-clause-
propagator can't be integrated.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def parse_our_csv(path: str):
    """Returns list of (top, right, bottom, left) tuples in OUR color units."""
    with open(path) as f:
        lines = [l.rstrip() for l in f if l.strip()]
    size = int(lines[0])
    n = size * size
    pieces = []
    for line in lines[1:n + 1]:
        cols = line.split(",")
        edges = []
        for col in cols[:4]:
            v = int(col, 2)
            edges.append(0 if v == 65535 else v)
        pieces.append(tuple(edges))
    return pieces


def parse_capiman_info(path: str):
    """Returns dict[card] = (N, E, S, W) tuple at rot=1, in CAPIMAN colors."""
    pat = re.compile(r"^\s*\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}")
    out = {}
    with open(path) as f:
        for line in f:
            m = pat.match(line)
            if not m:
                continue
            idx, field, card, rot, pn, pe, ps, pw = [int(x) for x in m.groups()]
            if rot != 1:
                continue
            # Take the FIRST entry for each card at rot=1 (the canonical orientation)
            if card not in out:
                out[card] = (pn, pe, ps, pw)
    return out


def main():
    our_pieces = parse_our_csv("../data/puzzles/size_16_official_eternity.csv")
    print(f"[ours] {len(our_pieces)} pieces parsed")
    capiman_cards = parse_capiman_info("output/capiman_e2/e2_info.c")
    print(f"[capiman] {len(capiman_cards)} cards parsed")

    # === Color-frequency signal ===
    our_freq = Counter()
    for e in our_pieces:
        our_freq.update(e)
    cap_freq = Counter()
    for e in capiman_cards.values():
        cap_freq.update(e)

    print(f"\n[color-freq] ours and capiman (color→count):")
    for c in sorted(set(our_freq) | set(cap_freq)):
        print(f"  c={c:>3}  ours={our_freq.get(c, 0):>4}  capiman={cap_freq.get(c, 0):>4}")

    # === Detect color = BORDER on both sides ===
    # By construction both should have color 0 = BORDER (occurs 64 times = 4 border edges per border piece × 16 border slots).

    # === Multiset signature per piece ===
    # For each our piece, the *unordered set of 4 edges* is a multiset. Same for capiman cards.
    # If both label systems list the SAME pieces just with different color labels, then we can
    # find a permutation of {0..22} that maps our pieces to capiman cards.

    our_sigs = [tuple(sorted(e)) for e in our_pieces]
    cap_sigs = {card: tuple(sorted(e)) for card, e in capiman_cards.items()}

    # A signature lookup: tuple(sorted(edges)) → list of (i, our_piece_id)
    our_sig_to_pid = defaultdict(list)
    for i, sig in enumerate(our_sigs):
        our_sig_to_pid[sig].append(i)
    cap_sig_to_card = defaultdict(list)
    for card, sig in cap_sigs.items():
        cap_sig_to_card[sig].append(card)

    # Try a greedy color permutation: align frequency-sorted lists.
    # NOTE: this assumes pieces share the same multiset structure between encodings.
    our_freq_sorted = [c for c, _ in our_freq.most_common()]
    cap_freq_sorted = [c for c, _ in cap_freq.most_common()]
    # Both should have 23 distinct values (0..22).
    print(f"\n[freq-rank] our_freq_sorted = {our_freq_sorted}")
    print(f"[freq-rank] cap_freq_sorted = {cap_freq_sorted}")

    # Naive map: pair by descending frequency.
    naive_map_our_to_cap = dict(zip(our_freq_sorted, cap_freq_sorted))
    print(f"\n[naive-map] our_color → capiman_color (by descending frequency):")
    for k in sorted(naive_map_our_to_cap):
        print(f"  {k} → {naive_map_our_to_cap[k]}")

    # Test the naive map: apply it to our pieces and check coverage.
    def apply_map(edges, m):
        return tuple(m.get(c, c) for c in edges)

    our_mapped = [apply_map(e, naive_map_our_to_cap) for e in our_pieces]
    our_mapped_sig = [tuple(sorted(e)) for e in our_mapped]
    matched = sum(1 for sig in our_mapped_sig if sig in cap_sig_to_card)
    print(f"\n[verify naive] {matched}/{len(our_pieces)} our pieces have a capiman match after naive-map")

    if matched < len(our_pieces):
        print("Naive map insufficient. Vol-33 will need either:")
        print("  a) iterative refinement (start from frequency-pair, adjust on ambiguous classes)")
        print("  b) constraint solve: find permutation π s.t. {apply_map(e, π) for e in our_pieces} = set of capiman card edges")

    # Save what we have
    Path("ml/data").mkdir(exist_ok=True)
    with open("ml/data/color_map_attempt.json", "w") as f:
        json.dump({
            "method": "frequency-pairing (naive)",
            "our_to_capiman": {str(k): v for k, v in naive_map_our_to_cap.items()},
            "coverage": f"{matched}/{len(our_pieces)}",
            "open_question": "exact reconciliation needs constraint solve or iterative refinement",
        }, f, indent=2)
    print(f"\n[out] ml/data/color_map_attempt.json")


if __name__ == "__main__":
    main()
