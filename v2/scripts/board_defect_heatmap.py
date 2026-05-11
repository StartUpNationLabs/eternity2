#!/usr/bin/env python3
"""Quick ASCII visualization of mismatch heatmap on a board."""
import argparse, json, re, sys

W = 16; H = 16; BORDER = 0
HINT_X, HINT_Y = 7, 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board_json")
    args = ap.parse_args()

    j = json.load(open(args.board_json))
    url = j['bucas_url']
    blob = re.search(r'board_edges=([a-z]+)', url).group(1)
    quads = [tuple(ord(blob[pos*4+i])-ord('a') for i in range(4)) for pos in range(W*W)]

    score = j.get('score', {}).get('matched_edges', 0)
    print(f"=== {args.board_json} (score={score}/480) ===\n")

    n_inc = [0] * (W*W)
    miss_h = set()
    miss_v = set()
    for y in range(H):
        for x in range(W):
            pos = y*W+x
            if x+1<W:
                a, b = quads[pos][1], quads[pos+1][3]
                if a!=BORDER and b!=BORDER and a!=b:
                    n_inc[pos] += 1; n_inc[pos+1] += 1
                    miss_h.add((x, y))
            if y+1<H:
                a, b = quads[pos][2], quads[pos+W][0]
                if a!=BORDER and b!=BORDER and a!=b:
                    n_inc[pos] += 1; n_inc[pos+W] += 1
                    miss_v.add((x, y))

    print(f"mismatches: {len(miss_h)} h + {len(miss_v)} v = {len(miss_h)+len(miss_v)}\n")
    print(f"Legend: '*'=hint, '#'=2+ defects, '+'=1, '.'=0; '~'=h-mismatch right, '|'=v-mismatch below")
    print()
    print("    " + "  ".join(f"{x:>2}" for x in range(W)))
    for y in range(H):
        line = f"{y:>2}  "
        for x in range(W):
            if (x, y) == (HINT_X, HINT_Y): line += ' *'
            else:
                n = n_inc[y*W+x]
                line += ' #' if n >= 2 else (' +' if n == 1 else ' .')
            if x + 1 < W:
                line += '~' if (x, y) in miss_h else ' '
        print(line)
        if y + 1 < H:
            line = "    "
            for x in range(W):
                line += ' |' if (x, y) in miss_v else '  '
                if x + 1 < W: line += ' '
            print(line)

if __name__ == "__main__":
    main()
