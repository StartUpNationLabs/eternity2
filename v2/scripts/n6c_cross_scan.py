#!/usr/bin/env python3
"""
N6c: cross-scan-order backbone analysis.

Compare consensus from BOTTOM-UP Blackwood boards (vol-17 chunks +
PT-457 derivatives) against TOP-DOWN gacolor_ac3_random_par boards
(vol-20 N6c).

Real structural backbone = cells where BOTH families agree.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/Users/raphaelanjou/Documents/dev-projects/polytech/eternity2/v2")


def find_placement(d):
    if not isinstance(d, dict):
        return None
    if "placement" in d and isinstance(d["placement"], list):
        return d["placement"]
    return None


def find_score(d):
    if not isinstance(d, dict):
        return None
    for k in ("matched_best", "best_score", "best_matched", "matched", "score"):
        v = d.get(k)
        if isinstance(v, int):
            return v
    return None


def board_to_dict(placement):
    out = {}
    for c in placement:
        if c is None:
            continue
        pos = c.get("pos")
        pid = c.get("piece_id", c.get("pid"))
        rot = c.get("rotation", c.get("rot"))
        if pos is not None and pid is not None and rot is not None:
            out[int(pos)] = (int(pid), int(rot))
    return out


def load_set(paths, min_score):
    boards = []
    for p in paths:
        try:
            d = json.load(open(p))
        except Exception:
            continue
        pl = find_placement(d)
        sc = find_score(d)
        if not pl or sc is None or sc < min_score:
            continue
        bd = board_to_dict(pl)
        if len(bd) < 100:
            continue
        boards.append({"path": str(p), "score": sc, "board": bd})
    return boards


def main():
    bottom_up = load_set(sorted((ROOT / "output").rglob("*.json")), min_score=440)
    # Re-cluster bottom_up to ~19 independent representatives.
    THRESHOLD = 0.85
    clusters = []
    for b in bottom_up:
        merged = False
        for cl in clusters:
            common = set(b["board"]) & set(cl["rep"]["board"])
            if common:
                agree = sum(1 for k in common if b["board"][k] == cl["rep"]["board"][k])
                if agree / len(common) >= THRESHOLD:
                    cl["members"].append(b)
                    if b["score"] > cl["rep"]["score"]:
                        cl["rep"] = b
                    merged = True
                    break
        if not merged:
            clusters.append({"rep": b, "members": [b]})
    bottom_up_reps = [cl["rep"] for cl in clusters]
    print(f"Bottom-up: {len(bottom_up)} boards → {len(bottom_up_reps)} clusters (≥440)")

    # Top-down boards: lower scores (281-303), partial placements.
    top_down_paths = sorted((ROOT / "output/n6_topdown").glob("topdown_gacolor_ac3_random_par_*.json"))
    top_down = load_set(top_down_paths, min_score=0)
    print(f"Top-down: {len(top_down)} boards (random)")

    # Tally consensus separately.
    def tally(boards):
        t = defaultdict(Counter)
        for b in boards:
            for pos, pr in b["board"].items():
                t[pos][pr] += 1
        return t

    bu_tally = tally(bottom_up_reps)
    td_tally = tally(top_down)

    # Cells covered by both sets.
    bu_total = len(bottom_up_reps)
    td_total = len(top_down)
    print(f"\nConsensus per cell — only cells with PLACED in BOTH sets:")
    real_backbone = []
    bu_only = []
    td_only = []
    disagree = []
    for pos in range(256):
        bu_top = bu_tally[pos].most_common(1)[0] if bu_tally.get(pos) else None
        td_top = td_tally[pos].most_common(1)[0] if td_tally.get(pos) else None
        if not bu_top:
            continue
        if not td_top:
            bu_only.append((pos, bu_top, bu_total))
            continue
        bu_frac = bu_top[1] / bu_total
        td_frac = td_top[1] / td_total
        if bu_top[0] == td_top[0] and bu_frac >= 0.9 and td_frac >= 0.5:
            real_backbone.append((pos, bu_top[0], bu_top[1], td_top[1]))
        elif bu_top[0] != td_top[0]:
            disagree.append((pos, bu_top, td_top))

    print(f"\nReal backbone (BU consensus ≥ 90% AND TD top mode matches with ≥ 50%):")
    print(f"  count = {len(real_backbone)}")
    for pos, pr, bu_n, td_n in sorted(real_backbone):
        r, c = pos // 16, pos % 16
        print(f"  ({r:2d},{c:2d}) pos={pos:3d}  {pr}  BU {bu_n}/{bu_total} ; TD {td_n}/{td_total}")

    print(f"\nCells where BU and TD top modes DISAGREE (top {min(20, len(disagree))}):")
    for pos, bu_top, td_top in disagree[:20]:
        r, c = pos // 16, pos % 16
        print(f"  ({r:2d},{c:2d}) pos={pos:3d}  BU={bu_top[0]} n={bu_top[1]}/{bu_total} ; TD={td_top[0]} n={td_top[1]}/{td_total}")

    # Also: cells in BU's 17-cell backbone that AREN'T confirmed by TD.
    bu_backbone = [pos for pos in range(256) if bu_tally.get(pos) and bu_tally[pos].most_common(1)[0][1] / bu_total >= 0.9]
    print(f"\nBU's 17-cell backbone confirmation by TD:")
    for pos in sorted(bu_backbone):
        bu_top = bu_tally[pos].most_common(1)[0]
        td_top = td_tally[pos].most_common(1)[0] if td_tally.get(pos) else None
        r, c = pos // 16, pos % 16
        if td_top is None:
            print(f"  ({r:2d},{c:2d}) BU agrees {bu_top[0]}@{bu_top[1]}/{bu_total}; TD: NO BOARDS COVER")
        elif td_top[0] == bu_top[0]:
            print(f"  ({r:2d},{c:2d}) BU agrees {bu_top[0]}@{bu_top[1]}/{bu_total}; TD agrees: {td_top[1]}/{td_total}  ✓")
        else:
            print(f"  ({r:2d},{c:2d}) BU agrees {bu_top[0]}@{bu_top[1]}/{bu_total}; TD disagrees: top {td_top[0]} {td_top[1]}/{td_total}  ✗")


if __name__ == "__main__":
    sys.exit(main() or 0)
