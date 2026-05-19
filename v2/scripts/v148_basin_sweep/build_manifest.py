#!/usr/bin/env python3
"""V148 — build the basin manifest.

Mirror V129-T12's logic: for each corner-perm bucket, pick the
highest-score board with score >= 458.

Output: scripts/v148_basin_sweep/manifest.json with
  [{"cp": [c0,c1,c2,c3], "base_score": int, "path": str}, ...]
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "database-400-480"
N_CELLS = 256


def load_record(p):
    try:
        d = json.load(open(p))
    except Exception:
        return None
    m = d.get("matched")
    pl = d.get("placement", [])
    if not isinstance(m, int):
        return None
    has_pos = any(isinstance(e, dict) and "pos" in e for e in pl)
    placement = {}
    if has_pos:
        for entry in pl:
            if isinstance(entry, dict):
                placement[int(entry["pos"])] = (int(entry["piece_id"]), int(entry["rotation"]))
    else:
        for i, entry in enumerate(pl):
            if isinstance(entry, dict):
                placement[i] = (int(entry["piece_id"]), int(entry["rotation"]))
    if len(placement) != N_CELLS:
        return None
    return m, placement


def main():
    by_corner_best = {}
    by_corner_path = {}
    for path in sorted(DB.glob("*.json")):
        r = load_record(path)
        if r is None:
            continue
        m, pl = r
        if m < 458:
            continue
        cp = tuple(pl[c][0] for c in (0, 15, 240, 255))
        if cp not in by_corner_best or m > by_corner_best[cp][0]:
            by_corner_best[cp] = (m, pl, path.name)
            by_corner_path[cp] = path

    manifest = []
    for cp, (score, _, name) in sorted(by_corner_best.items(), key=lambda x: -x[1][0]):
        manifest.append({
            "cp": list(cp),
            "base_score": score,
            "path": str(by_corner_path[cp]),
            "name": name,
        })

    out = REPO / "scripts/v148_basin_sweep/manifest.json"
    json.dump(manifest, open(out, "w"), indent=2)
    print(f"[manifest] {len(manifest)} basins → {out}")
    for entry in manifest:
        print(f"  cp={tuple(entry['cp'])} base={entry['base_score']} src={entry['name']}")


if __name__ == "__main__":
    main()
