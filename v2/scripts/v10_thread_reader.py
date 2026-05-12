#!/usr/bin/env python3
"""Read complete groups.io threads from messages.jsonl.

Usage:
    python3 scripts/v10_thread_reader.py --topic 12345          # single thread
    python3 scripts/v10_thread_reader.py --rank 1 5             # 1st to 5th largest
    python3 scripts/v10_thread_reader.py --subject "SAT"        # by subject
    python3 scripts/v10_thread_reader.py --list                 # list all by size
    python3 scripts/v10_thread_reader.py --min-size 20 --max-size 100  # range

Output: de-HTML-ed thread text written to stdout with one line per
sub-message, prefixed by [date|author]. Quoted-reply lines are
suppressed when they duplicate prior content in the thread.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSONL = ROOT / "community-exports" / "messages.jsonl"

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"[ \t]+")


def detag(s: str) -> str:
    if not s:
        return ""
    s = s.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
    s = s.replace("</p>", "\n").replace("</div>", "\n")
    s = re.sub(r"<blockquote[^>]*>", "\n> ", s)
    s = s.replace("</blockquote>", "\n")
    s = TAG_RE.sub("", s)
    s = html.unescape(s)
    s = s.replace("\r", "")
    return s


def author_short(name: str) -> str:
    if not name:
        return "?"
    n = re.sub(r"\s*<[^>]*>\s*$", "", name).strip()
    return n or "?"


def load_threads():
    threads = defaultdict(list)
    with JSONL.open() as f:
        for raw in f:
            m = json.loads(raw)
            t = m.get("topic_id") or 0
            threads[t].append(m)
    for t in threads:
        threads[t].sort(key=lambda m: m.get("created") or "")
    return threads


def dedupe_lines(text: str, seen: set[str]) -> str:
    """Remove lines (after strip) that have appeared in earlier messages of
    this thread. Keeps the structure of one's own original content."""
    keep = []
    for line in text.split("\n"):
        s = WS_RE.sub(" ", line).strip()
        if not s:
            keep.append("")
            continue
        # skip quoted-reply prefixes
        if s.startswith(">"):
            keep.append(line)
            continue
        if s in seen:
            continue
        seen.add(s)
        keep.append(line)
    return "\n".join(keep)


def print_thread(tid: int, msgs: list[dict]) -> None:
    subj = msgs[0].get("subject", "?")
    print(f"\n{'='*70}")
    print(f"THREAD #{tid}  [{len(msgs)} messages]  subject: {subj}")
    print(f"{'='*70}")
    seen: set[str] = set()
    for i, m in enumerate(msgs):
        date = (m.get("created") or "")[:10]
        author = author_short(m.get("name") or "?")
        body = detag(m.get("body") or "")
        deduped = dedupe_lines(body, seen)
        deduped = re.sub(r"\n{3,}", "\n\n", deduped).strip()
        print(f"\n--- [{i+1}/{len(msgs)}] {date} | {author} ---")
        if deduped:
            print(deduped)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", type=int)
    ap.add_argument("--rank", type=int, nargs=2,
                    help="rank-range: e.g. 1 5 means top-1 to top-5")
    ap.add_argument("--subject", type=str)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--min-size", type=int, default=0)
    ap.add_argument("--max-size", type=int, default=10_000)
    args = ap.parse_args()

    threads = load_threads()
    ranked = sorted(threads.items(), key=lambda kv: -len(kv[1]))

    if args.list:
        for i, (tid, msgs) in enumerate(ranked):
            if not (args.min_size <= len(msgs) <= args.max_size):
                continue
            subj = (msgs[0].get("subject") or "?").replace("\n", " ").strip()
            date = (msgs[0].get("created") or "")[:10]
            print(f"  #{i+1:4d}  tid={tid:<12d}  n={len(msgs):4d}  {date}  {subj[:80]}")
        return 0

    if args.topic:
        print_thread(args.topic, threads[args.topic])
        return 0

    if args.subject:
        sub_lower = args.subject.lower()
        for tid, msgs in ranked:
            subj = (msgs[0].get("subject") or "").lower()
            if sub_lower in subj:
                print_thread(tid, msgs)
        return 0

    if args.rank:
        lo, hi = args.rank
        for tid, msgs in ranked[lo-1:hi]:
            print_thread(tid, msgs)
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
