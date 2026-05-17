#!/usr/bin/env python3
"""Extract a 60-cell border partial from a full 256-cell board."""
import json, sys

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} FULL_BOARD.json OUT.json")
    sys.exit(1)

side = 16
with open(sys.argv[1]) as f:
    full = json.load(f)
out_placement = []
for entry in full.get("placement", []):
    if entry is None:
        continue
    pos = entry["pos"] if isinstance(entry, dict) and "pos" in entry else None
    if pos is None: continue
    r, c = pos // side, pos % side
    if r == 0 or r == side-1 or c == 0 or c == side-1:
        out_placement.append({"pos": pos, "piece_id": entry["piece_id"], "rotation": entry["rotation"]})

print(f"extracted {len(out_placement)} border cells")
with open(sys.argv[2], "w") as f:
    json.dump({"source": f"border_extract_{sys.argv[1]}", "placement": out_placement}, f, indent=2)
print(f"wrote {sys.argv[2]}")
