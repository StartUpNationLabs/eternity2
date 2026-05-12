#!/usr/bin/env python3
# Convert v14 bench-audit board JSON (sparse {pos,piece_id,rotation} array)
# to alns_e2-compatible format (length-256 array indexed by pos, null = empty).
# Usage: v14_convert_board_for_alns.py <in.json> <out.json>
import json, sys

if len(sys.argv) != 3:
    print("usage: v14_convert_board_for_alns.py <in.json> <out.json>", file=sys.stderr)
    sys.exit(2)

with open(sys.argv[1]) as f:
    doc = json.load(f)

# Support both flat and nested layouts.
placement = doc.get("placement") or doc.get("board", {}).get("placement")
if placement is None:
    print("no placement[]", file=sys.stderr); sys.exit(1)

out = [None] * 256
for entry in placement:
    if entry is None: continue
    pos = entry["pos"]
    out[pos] = {"piece_id": entry["piece_id"], "rotation": entry["rotation"]}

with open(sys.argv[2], "w") as f:
    json.dump({"placement": out}, f)
print(f"wrote {sys.argv[2]} ({sum(1 for x in out if x)} pieces placed)")
