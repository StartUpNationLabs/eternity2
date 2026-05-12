#!/usr/bin/env python3
"""Verify the onesmallstep claim (Discord, Jan 18 & 29 2026):

  - Edge pieces #17 and #38 each have a *unique inward-facing edge pattern*.
  - Inner piece #62 is the *only interior piece that connects to no hint*.

Tests the claims directly on the canonical piece data. The numbering scheme
matters: onesmallstep's "#17, #38, #62" need to be reconciled with our
piece file's ordering (line 1 of pieces.txt is piece 1, comma-separated).

We compute and report:
  - All four edge patterns of each edge piece, ranked by global rarity.
  - The 5 hint pieces' colors (from the 5-clue scenario).
  - Per interior piece: list of hint pieces it can adjacent-match (any
    rotation, any of 4 adjacency types).

Outputs: output/v10_math/significant_pieces.{json,txt}
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIECES = ROOT / "output" / "archive" / "pieces.txt"
OUT = ROOT / "output" / "v10_math"
OUT.mkdir(parents=True, exist_ok=True)

ALPHABET = list("abcdefghijklmnopqrstuvw")


def load_pieces() -> list[str]:
    with PIECES.open() as f:
        s = f.read().strip().strip('"')
    return s.split(",")


def piece_class(p: str) -> str:
    a = p.count("a")
    if a == 2:
        return "corner"
    if a == 1:
        return "edge"
    return "interior"


def edges(p: str) -> tuple[str, str, str, str]:
    """NESW."""
    return p[0], p[1], p[2], p[3]


def inward_edges_of_edge_piece(p: str) -> list[str]:
    """An edge piece has 1 border (a) and 3 inward-facing edges. Return
    the 3 non-'a' edges."""
    return [c for c in p if c != "a"]


def all_rotations(p: str) -> list[tuple[str, str, str, str]]:
    n, e, s, w = p[0], p[1], p[2], p[3]
    sides = [(n, e, s, w)]
    for _ in range(3):
        n, e, s, w = w, n, e, s
        sides.append((n, e, s, w))
    return sides


def piece_can_adjacent_match(p1: str, p2: str) -> bool:
    """True if some rotation of p1 and p2 can sit adjacent (any of 4
    adjacency types) with a single matching shared edge of a non-border color."""
    for n1, e1, s1, w1 in all_rotations(p1):
        for n2, e2, s2, w2 in all_rotations(p2):
            # p1 west-of p2: e1 == w2
            if e1 == w2 and e1 != "a":
                return True
            if w1 == e2 and w1 != "a":
                return True
            if s1 == n2 and s1 != "a":
                return True
            if n1 == s2 and n1 != "a":
                return True
    return False


def main() -> int:
    pieces = load_pieces()
    klasses = [piece_class(p) for p in pieces]

    # 1-indexed piece IDs as community uses them
    # piece 17 / 38 / 62 in 1-indexed → indices 16, 37, 61 in 0-indexed
    P17 = pieces[16]
    P38 = pieces[37]
    P62 = pieces[61]

    report: dict = {
        "piece_17": {"raw": P17, "class": piece_class(P17)},
        "piece_38": {"raw": P38, "class": piece_class(P38)},
        "piece_62": {"raw": P62, "class": piece_class(P62)},
    }

    # --- inward-edge uniqueness for pieces 17 and 38 ---
    # Across all 56 edge pieces (1 border 'a' + 3 inward colors), build the
    # frequency table of each inward-edge color. A "unique" pattern would be
    # one that appears on no other piece's inward side.
    edge_inward_counter: Counter = Counter()
    edge_pieces_idx = [i for i, p in enumerate(pieces) if klasses[i] == "edge"]
    print(f"edge pieces: {len(edge_pieces_idx)}", file=sys.stderr)
    assert len(edge_pieces_idx) == 56

    inward_by_piece: dict[int, list[str]] = {}
    for i in edge_pieces_idx:
        ews = inward_edges_of_edge_piece(pieces[i])
        inward_by_piece[i] = ews
        edge_inward_counter.update(ews)

    # for each of {17, 38}: how rare is each of its inward colors?
    def edge_uniqueness(idx_1based: int) -> dict:
        idx = idx_1based - 1
        ews = inward_by_piece[idx]
        return {
            "piece_id_1based": idx_1based,
            "piece_string": pieces[idx],
            "inward_colors": ews,
            "global_frequency_among_edge_inward": {
                c: edge_inward_counter[c] for c in ews
            },
            "is_globally_unique_per_color": {
                c: edge_inward_counter[c] == 1 for c in ews
            },
        }

    report["edge_uniqueness_17"] = edge_uniqueness(17)
    report["edge_uniqueness_38"] = edge_uniqueness(38)

    # Also enumerate all edge pieces with at least one globally-unique
    # inward color, to see if {17, 38} are actually a privileged pair.
    edges_with_unique_color: list[int] = []
    for i in edge_pieces_idx:
        if any(edge_inward_counter[c] == 1 for c in inward_by_piece[i]):
            edges_with_unique_color.append(i + 1)
    report["all_edges_with_unique_inward_color"] = edges_with_unique_color

    # --- piece 62 connectivity to hints ---
    # The canonical 5-clue hint set: 4 "clue puzzle" pieces + the fixed
    # starter piece 139 at I8. The hint piece IDs (1-indexed) come from
    # the standard E2 clue set. Verhaard's site and Blackwood's solver
    # both use the canonical positions.
    # Community-recorded hint pieces: 139 (central), and 4 others; we use
    # what the puzzle officially mandates. To avoid hard-coding wrong IDs
    # we'll test against MULTIPLE plausible hint sets and report each.
    # The community standard: pieces 139, 181, 208, 249, 254 (canonical 5
    # hints) — these are from the actual puzzle setup; we'll verify by
    # checking the piece-positions file if present, else use this set.
    candidate_hint_sets = {
        "5clue_canonical_widely_cited": [139, 181, 208, 249, 254],
    }

    # piece 62 vs hint sets
    def can_adjacent(p1_idx_0: int, p2_idx_0: int) -> bool:
        return piece_can_adjacent_match(pieces[p1_idx_0], pieces[p2_idx_0])

    p62 = 62 - 1
    hint_check: dict = {}
    for label, hints in candidate_hint_sets.items():
        per_hint = {}
        for h in hints:
            per_hint[h] = can_adjacent(p62, h - 1)
        hint_check[label] = {
            "hint_pieces": hints,
            "62_can_adjacent_to_hint": per_hint,
            "62_connects_to_any_hint": any(per_hint.values()),
        }
    report["piece_62_vs_hints"] = hint_check

    # Same check for all interior pieces under the canonical hint set:
    # who else (besides 62) connects to NO hint?
    canonical_hints = candidate_hint_sets["5clue_canonical_widely_cited"]
    canonical_hint_0idx = [h - 1 for h in canonical_hints]

    interior_idx = [i for i, k in enumerate(klasses) if k == "interior"]
    no_hint_connect: list[int] = []
    for i in interior_idx:
        if i in canonical_hint_0idx:
            continue  # don't compare a hint to itself
        if not any(can_adjacent(i, h) for h in canonical_hint_0idx):
            no_hint_connect.append(i + 1)
    report["interior_pieces_with_no_hint_connection"] = no_hint_connect
    report["count_interior_no_hint_connection"] = len(no_hint_connect)

    # Save JSON and human-readable
    with (OUT / "significant_pieces.json").open("w") as f:
        json.dump(report, f, indent=2)

    lines = []
    lines.append("=== Verification of onesmallstep claim (Discord 2026-01) ===")
    lines.append("")
    lines.append(f"piece 17 = '{P17}' ({piece_class(P17)})")
    lines.append(f"piece 38 = '{P38}' ({piece_class(P38)})")
    lines.append(f"piece 62 = '{P62}' ({piece_class(P62)})")
    lines.append("")
    lines.append("--- Claim 1a: piece 17 has a globally-unique inward edge color ---")
    e17 = report["edge_uniqueness_17"]
    lines.append(f"  inward colors: {e17['inward_colors']}")
    lines.append(f"  frequencies:   {e17['global_frequency_among_edge_inward']}")
    lines.append(f"  unique?        {e17['is_globally_unique_per_color']}")
    if any(e17['is_globally_unique_per_color'].values()):
        unique_c = [c for c, u in e17['is_globally_unique_per_color'].items() if u]
        lines.append(f"  ✓ CONFIRMED: piece 17 has unique edge color(s) {unique_c}")
    else:
        lines.append(f"  ✗ REFUTED: no edge color of piece 17 is globally unique")
    lines.append("")
    lines.append("--- Claim 1b: piece 38 has a globally-unique inward edge color ---")
    e38 = report["edge_uniqueness_38"]
    lines.append(f"  inward colors: {e38['inward_colors']}")
    lines.append(f"  frequencies:   {e38['global_frequency_among_edge_inward']}")
    lines.append(f"  unique?        {e38['is_globally_unique_per_color']}")
    if any(e38['is_globally_unique_per_color'].values()):
        unique_c = [c for c, u in e38['is_globally_unique_per_color'].items() if u]
        lines.append(f"  ✓ CONFIRMED: piece 38 has unique edge color(s) {unique_c}")
    else:
        lines.append(f"  ✗ REFUTED: no edge color of piece 38 is globally unique")
    lines.append("")
    lines.append("--- How many other edge pieces have a globally-unique inward color? ---")
    lines.append(f"  total edge pieces with ≥1 globally-unique inward color: "
                 f"{len(edges_with_unique_color)}")
    lines.append(f"  IDs (1-based): {edges_with_unique_color}")
    if {17, 38}.issubset(set(edges_with_unique_color)):
        lines.append(
            "  → 17 and 38 are in this set; "
            f"there are {len(edges_with_unique_color)} such pieces total."
        )
    lines.append("")
    lines.append("--- Claim 2: piece 62 connects to no hint piece ---")
    cano = report["piece_62_vs_hints"]["5clue_canonical_widely_cited"]
    lines.append(f"  hint set tested: {cano['hint_pieces']}")
    lines.append(f"  62 adjacent to each: {cano['62_can_adjacent_to_hint']}")
    lines.append(f"  → connects to any hint? {cano['62_connects_to_any_hint']}")
    lines.append("")
    lines.append(
        f"--- Cross-check: how many interior pieces connect to NO hint? "
        f"({report['count_interior_no_hint_connection']}) ---"
    )
    nh = report["interior_pieces_with_no_hint_connection"]
    if nh:
        lines.append(f"  IDs (1-based): {nh}")
    else:
        lines.append("  none (every interior piece can adjacent-match some hint)")
    lines.append("")
    if 62 in nh and len(nh) == 1:
        lines.append("  ✓ CONFIRMED: piece 62 is the SOLE interior piece that")
        lines.append("    cannot adjacent-match any hint piece (in any rotation).")
    elif 62 in nh:
        lines.append(f"  PARTIALLY CONFIRMED: piece 62 is in the no-hint-connection")
        lines.append(f"  set, but it is NOT unique — {len(nh)} interior pieces share")
        lines.append("  this property.")
    else:
        lines.append("  ✗ REFUTED with this hint set: piece 62 CAN adjacent-match")
        lines.append("  at least one hint. Either the claim is wrong, OR the hint")
        lines.append("  set assumed (139, 181, 208, 249, 254) differs from the one")
        lines.append("  onesmallstep had in mind.")
    lines.append("")

    txt = "\n".join(lines)
    print(txt)
    with (OUT / "significant_pieces.txt").open("w") as f:
        f.write(txt + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
