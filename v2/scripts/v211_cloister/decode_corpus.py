#!/usr/bin/env python3
"""vol-211: decode raw-bucas community corpus boards (board_edges only) into
canonical placement JSONs, via the unique quad->(piece,rot) map of the
canonical piece set. Direct labeling first ('a'=0,...); on failure, attempt
sigma-recovery (color bijection search via constraint propagation).

Output: output/vol-211/corpus_decoded_<ts>/<name>.json  (never overwrites)
"""
import json, glob, os, re, sys, time
from collections import Counter

PUZZLE_CSV = "../data/puzzles/size_16_official_eternity.csv"
BORDER_RAW = 65535


def load_canonical_pieces():
    pieces = []
    with open(PUZZLE_CSV) as f:
        f.readline()
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            def col(s):
                v = int(s.strip(), 2)
                return 0 if v == BORDER_RAW else v
            pieces.append(tuple(col(p) for p in parts[:4]))  # N,E,S,W
    return pieces


def rot(q, r):
    # rotation r: edge at side s comes from base side (s - r) mod 4 (clockwise),
    # matching e2lib.rot_edges convention
    return tuple(q[(s - r) % 4] for s in range(4))


def build_quad_map(pieces):
    m = {}
    for pid, q in enumerate(pieces):
        for r in range(4):
            rq = rot(q, r)
            if rq in m:
                # ambiguous quad (shouldn't happen: pieces rotation-distinct)
                m[rq] = None
            else:
                m[rq] = (pid, r)
    return m


def decode_direct(edge_str, quad_map):
    """Return placement list of (pid, rot) or None."""
    if len(edge_str) != 1024:
        return None
    place = []
    for c in range(256):
        quad = tuple(ord(ch) - ord('a') for ch in edge_str[4 * c:4 * c + 4])
        hit = quad_map.get(quad)
        if hit is None:
            return None
        place.append(hit)
    pids = [p for p, _ in place]
    if sorted(pids) != list(range(256)):
        return None
    return place


def try_sigma(edge_str, pieces):
    """Attempt color-bijection recovery: find sigma: obs_color -> canon_color
    such that every observed quad maps to a distinct canonical piece.
    Approach: anchor on color frequency profiles, then DFS over candidates."""
    obs_quads = [tuple(ord(ch) - ord('a') for ch in edge_str[4 * c:4 * c + 4])
                 for c in range(256)]
    obs_colors = sorted({c for q in obs_quads for c in q})
    canon_colors = sorted({c for q in pieces for c in q})
    if len(obs_colors) != len(canon_colors):
        return None
    obs_freq = Counter(c for q in obs_quads for c in q)
    canon_freq = Counter(c for q in pieces for c in q)
    # group colors by frequency; bijection must preserve frequency
    from collections import defaultdict
    cand = {}
    canon_by_freq = defaultdict(list)
    for c, f in canon_freq.items():
        canon_by_freq[f].append(c)
    for c in obs_colors:
        cand[c] = canon_by_freq.get(obs_freq[c], [])
        if not cand[c]:
            return None
    # border color: 0 in canon appears on outer rim; obs color 0 ('a') likewise
    if 0 in cand and 0 in cand.get(0, []):
        cand[0] = [0]
    quad_map = build_quad_map(pieces)
    order = sorted(obs_colors, key=lambda c: len(cand[c]))
    sigma = {}
    used = set()

    def consistent_partial():
        # quick check: each obs quad fully in sigma domain must map
        for q in obs_quads:
            if all(c in sigma for c in q):
                if quad_map.get(tuple(sigma[c] for c in q)) is None:
                    return False
        return True

    def dfs(i):
        if i == len(order):
            place = decode_direct(
                "".join(chr(ord('a') + sigma[c]) for q in obs_quads for c in q),
                quad_map)
            return place
        c = order[i]
        for t in cand[c]:
            if t in used:
                continue
            sigma[c] = t
            used.add(t)
            if consistent_partial():
                r = dfs(i + 1)
                if r is not None:
                    return r
            del sigma[c]
            used.discard(t)
        return None

    return dfs(0)


def main():
    pieces = load_canonical_pieces()
    quad_map = build_quad_map(pieces)
    ts = time.strftime("%Y%m%dT%H%M%S")
    outdir = f"output/vol-211/corpus_decoded_{ts}"
    os.makedirs(outdir, exist_ok=True)
    n_ok = n_sigma = n_fail = 0
    for f in sorted(glob.glob("output/community_corpus/*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict) or "url" not in d:
            continue
        m = re.search(r"board_edges=([a-w]+)", d["url"])
        if not m:
            continue
        name = os.path.basename(f)
        place = decode_direct(m.group(1), quad_map)
        how = "direct"
        if place is None:
            place = try_sigma(m.group(1), pieces)
            how = "sigma"
        if place is None:
            n_fail += 1
            print(f"FAIL  {name}")
            continue
        if how == "sigma":
            n_sigma += 1
        else:
            n_ok += 1
        out = {
            "source": f, "decode": how,
            "placement": [{"pos": i, "piece_id": int(p), "rotation": int(r)}
                          for i, (p, r) in enumerate(place)],
        }
        with open(os.path.join(outdir, name), "w") as g:
            json.dump(out, g)
        print(f"OK({how})  {name}")
    print(f"\ndecoded direct={n_ok} sigma={n_sigma} fail={n_fail} -> {outdir}")


if __name__ == "__main__":
    main()
