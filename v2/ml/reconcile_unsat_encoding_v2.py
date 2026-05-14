"""Vol-34 T2 — robust reconciliation of capiman's color labels with ours.

The vol-32 frequency-pair attempt mapped only 22/256 pieces. The reason:
ours and capiman have ~5 distinct frequency classes (with 5/4 colors at
count 24, 5/6 at 47-48, etc.), so naive frequency-pairing has multiple
permutations to choose from.

Strategy: refine the frequency class by **piece co-occurrence**. For each
color c, build a fingerprint:

    sig(c) = sorted multiset of (other colors that appear on the same
             piece as c, weighted by how many edges of c are on that piece)

This fingerprint is invariant under color relabeling: if π maps c to c',
then sig(c) under π corresponds to sig(c') unrelabeled.

After computing sig(c) for both encodings, we partition colors by
fingerprint. If each fingerprint class has size 1, the bijection is
determined. Otherwise, recurse: include 2-hop neighbour info, etc.

Output: ml/data/color_map.json with all 23 our_color → capiman_color
entries, plus a verification pass that confirms every our piece has a
matching capiman card.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path


def parse_our_csv(path: str):
    with open(path) as f:
        lines = [l.rstrip() for l in f if l.strip()]
    n = int(lines[0]) ** 2
    pieces = []
    for line in lines[1 : n + 1]:
        cols = line.split(",")
        edges = []
        for col in cols[:4]:
            v = int(col, 2)
            edges.append(0 if v == 65535 else v)
        pieces.append(tuple(edges))
    return pieces


def parse_capiman_info(path: str):
    """All rotations; returns dict[card] = (N, E, S, W) at canonical rot=1.

    Each card appears 4 times (once per rot). We collect rot=1 first; if
    a card has no rot=1 entry (corners?), fall back to rot=0.
    """
    pat = re.compile(
        r"^\s*\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}"
    )
    by_card = defaultdict(dict)  # card -> rot -> (n,e,s,w)
    with open(path) as f:
        for line in f:
            m = pat.match(line)
            if not m:
                continue
            _, _, card, rot, pn, pe, ps, pw = [int(x) for x in m.groups()]
            by_card[card][rot] = (pn, pe, ps, pw)
    out = {}
    for card, rots in by_card.items():
        for r in (1, 0, 2, 3):
            if r in rots:
                out[card] = rots[r]
                break
    return out


def piece_fingerprint(pieces, color):
    """For each piece containing `color`, count co-occurrences of OTHER colors.
    Return a sorted tuple of (count_of_color_on_piece, sorted multiset of
    the 4 - count_of_color other edges).
    """
    sigs = []
    for edges in pieces:
        c_count = sum(1 for e in edges if e == color)
        if c_count == 0:
            continue
        others = sorted(e for e in edges if e != color)
        # Pad to 4 entries for fixed-length signature.
        while len(others) < 4:
            others.append(-1)
        sigs.append((c_count, tuple(others)))
    return tuple(sorted(sigs))


def find_color_map_by_fingerprint(our_pieces, capiman_pieces):
    """Direct fingerprint matching. Works when fingerprints are unique."""
    our_colors = sorted({e for piece in our_pieces for e in piece})
    cap_colors = sorted({e for piece in capiman_pieces for e in piece})
    assert len(our_colors) == len(cap_colors), (our_colors, cap_colors)

    # Naive direct fingerprint uses raw color labels of co-occurring edges,
    # which is NOT invariant under relabeling. Use a count-only signature
    # instead: for color c, the multiset of (count of c on piece, multiset
    # of frequency-class labels of the 3 other edges).
    # Get the frequency class of each color first.
    our_freq = Counter()
    for e in our_pieces:
        our_freq.update(e)
    cap_freq = Counter()
    for e in capiman_pieces:
        cap_freq.update(e)

    return our_colors, cap_colors, our_freq, cap_freq


def signature_v2(pieces, color, color_freq):
    """Relabeling-invariant signature for `color`. Uses frequency-class
    of co-occurring colors (which is invariant) plus count-of-`color`-on-piece.
    """
    sigs = []
    for edges in pieces:
        c_count = sum(1 for e in edges if e == color)
        if c_count == 0:
            continue
        # Frequency-classes of the OTHER edges.
        others = sorted(color_freq[e] for e in edges if e != color)
        while len(others) < 4:
            others.append(-1)
        sigs.append((c_count, tuple(others)))
    return tuple(sorted(sigs))


def main():
    our = parse_our_csv("../data/puzzles/size_16_official_eternity.csv")
    cap_by_card = parse_capiman_info("output/capiman_e2/e2_info.c")
    cap = [cap_by_card[c] for c in sorted(cap_by_card)]
    print(f"[ours] {len(our)} pieces; [capiman] {len(cap)} cards")

    our_freq = Counter()
    for e in our:
        our_freq.update(e)
    cap_freq = Counter()
    for e in cap:
        cap_freq.update(e)

    our_sigs = {c: signature_v2(our, c, our_freq) for c in sorted(our_freq)}
    cap_sigs = {c: signature_v2(cap, c, cap_freq) for c in sorted(cap_freq)}

    # Group by signature
    our_by_sig = defaultdict(list)
    cap_by_sig = defaultdict(list)
    for c, s in our_sigs.items():
        our_by_sig[s].append(c)
    for c, s in cap_sigs.items():
        cap_by_sig[s].append(c)

    print(f"\n[partition] ours: {len(our_by_sig)} distinct sigs over {len(our_sigs)} colors")
    print(f"[partition] cap:  {len(cap_by_sig)} distinct sigs over {len(cap_sigs)} colors")

    # If each signature has the same multiplicity in both encodings, we can
    # at least narrow down. Print the partition sizes.
    our_partition = sorted([(len(v), v) for v in our_by_sig.values()])
    cap_partition = sorted([(len(v), v) for v in cap_by_sig.values()])
    print(f"\n[our class sizes] {[s for s, _ in our_partition]}")
    print(f"[cap class sizes] {[s for s, _ in cap_partition]}")

    # If both partitions agree by-multiset of (sig → size), we can
    # iterate within each class. Otherwise the encodings differ
    # non-trivially.

    sig_to_pair = {}
    unmatched = []
    for s, ours_in_class in our_by_sig.items():
        if s in cap_by_sig:
            sig_to_pair[s] = (ours_in_class, cap_by_sig[s])
        else:
            unmatched.append(("ours", s, ours_in_class))
    for s, caps_in_class in cap_by_sig.items():
        if s not in our_by_sig:
            unmatched.append(("cap", s, caps_in_class))

    print(f"\n[match] {len(sig_to_pair)} sigs matched")
    print(f"[unmatched] {len(unmatched)} sigs with no counterpart")

    if not unmatched:
        # Within each class of size > 1, we still need to assign. For now,
        # check if all classes have size 1.
        all_unique = all(len(v) == 1 for v in our_by_sig.values())
        print(f"\n[deterministic] all classes have size 1? {all_unique}")

        if all_unique:
            color_map = {}
            for s, (ours_list, caps_list) in sig_to_pair.items():
                color_map[ours_list[0]] = caps_list[0]
            verify_and_save(our, cap, color_map)
            return

        # Try brute-force within each remaining ambiguous class.
        # Total candidates = product of class-size factorials.
        ambiguous = {s: (ours_list, caps_list) for s, (ours_list, caps_list) in sig_to_pair.items() if len(ours_list) > 1}
        n_combos = 1
        for ol, cl in ambiguous.values():
            from math import factorial
            n_combos *= factorial(len(ol))
        print(f"\n[ambiguous] {len(ambiguous)} classes with size > 1; total perms = {n_combos}")

        # Brute-force across all combinations
        unambiguous_pairs = [(s, ours_list, caps_list) for s, (ours_list, caps_list) in sig_to_pair.items() if len(ours_list) == 1]
        base_map = {ol[0]: cl[0] for _, ol, cl in unambiguous_pairs}

        ambig_keys = list(ambiguous.keys())
        ambig_ours = [ambiguous[s][0] for s in ambig_keys]
        ambig_caps = [ambiguous[s][1] for s in ambig_keys]

        # Pre-compute cap-piece signature set for verification (sorted tuple)
        cap_sig_set = set(tuple(sorted(e)) for e in cap)

        def enumerate_perms(idx, current_map):
            if idx == len(ambig_keys):
                # Verify
                bad = 0
                for ours_piece in our:
                    mapped = tuple(sorted(current_map[c] for c in ours_piece))
                    if mapped not in cap_sig_set:
                        bad += 1
                        if bad > 0:
                            return None
                return dict(current_map)
            ours_list = ambig_ours[idx]
            caps_list = ambig_caps[idx]
            for perm in permutations(caps_list):
                new_map = dict(current_map)
                for o, c in zip(ours_list, perm):
                    new_map[o] = c
                res = enumerate_perms(idx + 1, new_map)
                if res is not None:
                    return res
            return None

        if n_combos > 1_000_000:
            print("[brute] too many combos — would need smarter search")
            return

        result = enumerate_perms(0, base_map)
        if result is None:
            print("[brute] no valid mapping found")
            return
        verify_and_save(our, cap, result)
        return

    print("\n[next] partition sizes don't match by signature — need 2-hop or piece-structural refinement.")


def verify_and_save(our, cap, color_map):
    cap_sig_set = Counter(tuple(sorted(e)) for e in cap)
    our_sig_mapped = Counter(tuple(sorted(color_map[c] for c in piece)) for piece in our)
    matches = sum(min(our_sig_mapped[s], cap_sig_set[s]) for s in our_sig_mapped)
    print(f"\n[verify] {matches}/{len(our)} our pieces map to a capiman card (multiset match)")

    if our_sig_mapped == cap_sig_set:
        print("[verify] BIJECTIVE — every piece accounted for both directions")
    else:
        extra = our_sig_mapped - cap_sig_set
        missing = cap_sig_set - our_sig_mapped
        print(f"[verify] not bijective: {sum(extra.values())} our extras, {sum(missing.values())} cap missing")

    Path("ml/data").mkdir(exist_ok=True)
    with open("ml/data/color_map.json", "w") as f:
        json.dump(
            {
                "method": "signature_v2 + brute-force ambiguous classes",
                "our_to_capiman": {str(k): v for k, v in sorted(color_map.items())},
                "matches": f"{matches}/{len(our)}",
            },
            f,
            indent=2,
        )
    print(f"\n[out] ml/data/color_map.json")


if __name__ == "__main__":
    main()
