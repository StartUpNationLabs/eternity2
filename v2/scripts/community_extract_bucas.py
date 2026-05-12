#!/usr/bin/env python3
"""Extract every bucas board URL from the v8 corpus, decode, score, save.

For each unique URL with a `board_edges=` blob:
  - parse 16x16 quads (N/E/S/W) — same encoding scripts/compare_boards.py uses
  - count matched interior+border edges (excluding the implicit-grey edges)
  - record provenance: source/id/date/author from the [tag] prefix in the corpus
  - write JSON to output/community_corpus/<source>_<id>_<score>.json
  - write tsv summary to output/community_corpus/_index.tsv
"""
from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "output" / "v8_grep" / "corpus.txt"
OUT = ROOT / "output" / "community_corpus"
OUT.mkdir(parents=True, exist_ok=True)
INDEX = OUT / "_index.tsv"

W = H = 16
BORDER = 0  # color 'a' = 0 = border / gray

URL_RE = re.compile(r"https://e2\.bucas\.name/[^\s\"]+")
TAG_RE = re.compile(r"^\[(?P<source>[a-z]+):(?P<id>[^|]+)\|(?P<date>[^|]+)\|(?P<author>[^|\]]+)(?:\|(?P<subject>[^\]]*))?\]")
EDGES_RE = re.compile(r"board_edges=([a-z]+)")
PIECES_RE = re.compile(r"board_pieces=([0-9]+)")
PUZZLE_RE = re.compile(r"#puzzle=([^&]+)")


def parse_quads(blob: str):
    n = W * H
    if len(blob) < n * 4:
        return None
    qs = []
    for pos in range(n):
        chunk = blob[pos * 4: pos * 4 + 4]
        qs.append(tuple(ord(c) - ord('a') for c in chunk))
    return qs


def score(quads) -> tuple[int, int, int]:
    """Return (interior_matched, border_inward_matched, pieces_placed).

    interior+border are the canonical 480 internal joins. A piece is
    considered placed if any non-border edge is non-grey, i.e. quad is not
    all-zero.
    """
    matched_interior = 0
    matched_border = 0
    for y in range(H):
        for x in range(W):
            pos = y * W + x
            n, e, s, w = quads[pos]
            if x + 1 < W:
                rn, re_, rs, rw = quads[pos + 1]
                if e != BORDER and rw != BORDER and e == rw:
                    if x == 0 or x + 1 == W - 1:
                        # neither — both interior columns
                        pass
                    matched_interior += 1
                elif e != BORDER and rw != BORDER:
                    pass  # mismatch
            if y + 1 < H:
                bn, be, bs, bw = quads[pos + W]
                if s != BORDER and bn != BORDER and s == bn:
                    matched_interior += 1
    placed = sum(1 for q in quads if q != (0, 0, 0, 0))
    # The canonical /480 score is exactly the number of matching internal
    # (non-grey-non-grey) joins, which is what matched_interior counts.
    return matched_interior, matched_border, placed


def looks_like_full_e2(url: str) -> bool:
    """Heuristic: 16x16, references the official puzzle, has board_edges of length 1024."""
    if "board_w=16" not in url and "puzzle=size_16_official" not in url:
        # url may omit board_w if puzzle param is the official one
        pass
    m = EDGES_RE.search(url)
    if not m:
        return False
    return len(m.group(1)) == W * H * 4


def main() -> int:
    seen: "OrderedDict[str, dict]" = OrderedDict()
    line_no = 0
    with CORPUS.open() as f:
        for line in f:
            line_no += 1
            if "bucas.name" not in line:
                continue
            tag = TAG_RE.match(line)
            if not tag:
                continue
            urls = URL_RE.findall(line)
            for url in urls:
                if "board_edges=" not in url:
                    continue
                key = url
                if key in seen:
                    continue
                seen[key] = {
                    "url": url,
                    "line": line_no,
                    "source": tag.group("source"),
                    "id": tag.group("id"),
                    "date": tag.group("date"),
                    "author": tag.group("author"),
                    "subject": (tag.group("subject") or "").strip(),
                }

    print(f"unique bucas URLs in corpus: {len(seen)}", file=sys.stderr)

    rows = []
    failed = 0
    for url, meta in seen.items():
        edges_m = EDGES_RE.search(url)
        if not edges_m:
            failed += 1
            continue
        blob = edges_m.group(1)
        quads = parse_quads(blob)
        if quads is None:
            failed += 1
            continue
        puz = (PUZZLE_RE.search(url) or [None, ""])[1]
        s_int, s_bor, placed = score(quads)
        rec = {
            **meta,
            "puzzle": puz,
            "edges_len": len(blob),
            "interior_matched": s_int,
            "pieces_placed": placed,
        }
        rows.append(rec)

    # rank by interior_matched
    rows.sort(key=lambda r: (-r["interior_matched"], r["date"]))

    written = 0
    with INDEX.open("w") as idx:
        idx.write("score\tplaced\tpuzzle\tsource\tid\tdate\tauthor\tsubject\tline\tjson\n")
        for r in rows:
            fname = f"{r['source']}_{r['id']}_{r['interior_matched']:03d}.json"
            outp = OUT / fname
            with outp.open("w") as f:
                json.dump(r, f, indent=2)
            written += 1
            idx.write(
                f"{r['interior_matched']}\t{r['pieces_placed']}\t{r['puzzle']}\t"
                f"{r['source']}\t{r['id']}\t{r['date']}\t{r['author']}\t"
                f"{r['subject']}\t{r['line']}\t{fname}\n"
            )

    print(f"failed parses: {failed}", file=sys.stderr)
    print(f"wrote: {written} json + {INDEX}", file=sys.stderr)

    # quick summary on stderr
    high = [r for r in rows if r["interior_matched"] >= 400]
    print(f"boards with interior_matched ≥ 400: {len(high)}", file=sys.stderr)
    for r in rows[:15]:
        print(
            f"  {r['interior_matched']:3d}  placed={r['pieces_placed']:3d}  "
            f"{r['source']}:{r['id']}  {r['date']}  {r['author']}  "
            f"{(r['subject'] or '')[:40]}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
