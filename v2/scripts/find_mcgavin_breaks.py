#!/usr/bin/env python3
"""Decode mismatch positions in the McGavin 469 board into scan-order
break indices for BlackwoodSchedule.

McGavin's 469 has 11 mismatched edges. For each mismatch, the "later
cell" in bottom-up row-major scan order is where the Blackwood
algorithm consumes its break license. So the schedule's
`break_indexes_allowed` should be the LATER-cell scan-index of each
mismatch.

Output (current): [187, 188, 190, 199, 200, 202, 206, 216, 222, 233, 249]
"""
import json
import re
from pathlib import Path
import sys

CORPUS = Path('output/community_corpus/groups_172011298_469.json')
W = H = 16

def main():
    if not CORPUS.exists():
        print(f"missing {CORPUS}", file=sys.stderr)
        sys.exit(1)
    data = json.load(open(CORPUS))
    m = re.search(r'board_edges=([a-z]+)', data['url'])
    if not m:
        print("no board_edges in url", file=sys.stderr); sys.exit(2)
    blob = m.group(1)
    if len(blob) < W*H*4:
        print(f"short blob {len(blob)}", file=sys.stderr); sys.exit(3)
    cell_edges = []
    for pos in range(W*H):
        q = [ord(c) - ord('a') for c in blob[pos*4:(pos+1)*4]]
        cell_edges.append(q)

    mismatches = []
    for y in range(H):
        for x in range(W):
            pos = y*W + x
            e = cell_edges[pos]
            if x+1 < W:
                er = cell_edges[pos+1]
                if e[1] != 0 and er[3] != 0 and e[1] != er[3]:
                    scan_a = (H-1-y)*W + x
                    scan_b = (H-1-y)*W + (x+1)
                    mismatches.append((min(scan_a, scan_b), max(scan_a, scan_b)))
            if y+1 < H:
                eb = cell_edges[pos+W]
                if e[2] != 0 and eb[0] != 0 and e[2] != eb[0]:
                    scan_a = (H-1-y)*W + x
                    scan_b = (H-1-(y+1))*W + x
                    mismatches.append((min(scan_a, scan_b), max(scan_a, scan_b)))

    later = sorted(b for a, b in mismatches)
    print(f"McGavin 469: {len(mismatches)} mismatched edges")
    print(f"break_indexes_allowed (sorted later-cell scan indices) = {later}")

if __name__ == '__main__':
    main()
