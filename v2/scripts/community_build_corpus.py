#!/usr/bin/env python3
"""Build a flat searchable text corpus from community-exports/.

Emits output/v8_grep/corpus.txt where each non-blank line is one of:
  [groups:<id>|<date>|<author>|<subject>] <body line>
  [discord:<row>|<date>|<author>] <content>

Body lines are de-HTML'd to plain text. The output is one big grep-friendly
file with provenance baked into every line, so downstream awk/grep can pull
the source back out without re-parsing JSON.
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "community-exports"
OUT_DIR = ROOT / "output" / "v8_grep"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "corpus.txt"
INDEX = OUT_DIR / "corpus_index.tsv"

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"[ \t]+")


def detag(s: str) -> str:
    if not s:
        return ""
    s = s.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
    s = s.replace("</p>", "\n").replace("</div>", "\n")
    s = TAG_RE.sub("", s)
    s = html.unescape(s)
    s = s.replace("\r", "")
    return s


def emit_lines(prefix: str, body: str, fout) -> int:
    n = 0
    for raw in body.split("\n"):
        line = WS_RE.sub(" ", raw).strip()
        if not line:
            continue
        # keep lines reasonably short for grep readability
        if len(line) > 4000:
            line = line[:4000] + "  …[truncated]"
        fout.write(f"{prefix} {line}\n")
        n += 1
    return n


def process_groups(fout, idx) -> tuple[int, int]:
    """Parse messages.jsonl. Returns (messages, body_lines)."""
    path = EXPORTS / "messages.jsonl"
    if not path.exists():
        return 0, 0
    msg_count = 0
    line_count = 0
    with path.open() as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                m = json.loads(raw)
            except json.JSONDecodeError:
                continue
            mid = m.get("id", "?")
            date = (m.get("created") or "")[:10]
            author = (m.get("name") or "?").replace("|", "/").replace("\t", " ")
            # author often looks like "Foo <bar@...>"; keep handle only
            author = re.sub(r"\s*<[^>]*>\s*$", "", author).strip() or "?"
            subject = (m.get("subject") or "").replace("|", "/").replace("\t", " ").strip()
            body = detag(m.get("body") or "")
            prefix = f"[groups:{mid}|{date}|{author}|{subject}]"
            nl = emit_lines(prefix, body, fout)
            line_count += nl
            msg_count += 1
            idx.write(f"groups\t{mid}\t{date}\t{author}\t{subject}\t{nl}\n")
    return msg_count, line_count


def process_discord(fout, idx) -> tuple[int, int]:
    path = EXPORTS / "eternity2-discord-general.csv"
    if not path.exists():
        return 0, 0
    msg_count = 0
    line_count = 0
    with path.open() as f:
        reader = csv.DictReader(f)
        for row_i, row in enumerate(reader):
            author = (row.get("Author") or "?").replace("|", "/").strip()
            date = (row.get("Date") or "")[:10]
            content = row.get("Content") or ""
            attach = row.get("Attachments") or ""
            if attach:
                content = (content + "\nATTACH: " + attach).strip()
            content = content.replace("\\n", "\n")
            prefix = f"[discord:{row_i}|{date}|{author}]"
            nl = emit_lines(prefix, content, fout)
            line_count += nl
            msg_count += 1
            idx.write(f"discord\t{row_i}\t{date}\t{author}\t\t{nl}\n")
    return msg_count, line_count


def main() -> int:
    with OUT.open("w") as fout, INDEX.open("w") as idx:
        idx.write("source\tid\tdate\tauthor\tsubject\tlines\n")
        gm, gl = process_groups(fout, idx)
        dm, dl = process_discord(fout, idx)
    print(f"groups.io: {gm} msgs, {gl} body lines", file=sys.stderr)
    print(f"discord  : {dm} msgs, {dl} body lines", file=sys.stderr)
    print(f"output   : {OUT} ({OUT.stat().st_size/1e6:.1f} MB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
