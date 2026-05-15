#!/usr/bin/env python3
"""Vol-65 — Pairwise σ-cycle decomposition for all known 458+ records.

For every pair of 458+ records, compute:
- Hamming distance (cells differ)
- σ-cycle decomposition (lengths sorted desc)
- Cells matched in both / one / neither basin
- Bounding box of diff cells

Goal: characterize the σ-orbit structure of the 458+ plateau.
"""

import collections
import glob
import json
import urllib.parse
from itertools import combinations
from pathlib import Path


def load_placement(path):
    try:
        with open(path) as f:
            d = json.load(f)
    except Exception:
        return None, None
    arr = d.get("placement", [])
    pos_to_pid = {}
    pid_to_pos = {}
    for idx, item in enumerate(arr):
        if item is None:
            continue
        pos = item.get("pos", idx)
        pid = item["piece_id"]
        rot = item["rotation"]
        pos_to_pid[pos] = (pid, rot)
        pid_to_pos[pid] = pos
    return pos_to_pid, pid_to_pos


def sigma_decomposition(p17, p200):
    """Given two piece-id -> position dicts, decompose the permutation."""
    sigma = {}  # pos -> pos (where piece at pos in board1 went in board2)
    for pid, pos in p17.items():
        new_pos = p200.get(pid)
        if new_pos is not None and new_pos != pos:
            sigma[pos] = new_pos
    visited = set()
    cycles = []
    for start in sigma:
        if start in visited:
            continue
        cycle = []
        cur = start
        while cur in sigma and cur not in visited:
            visited.add(cur)
            cycle.append(cur)
            cur = sigma[cur]
        if len(cycle) >= 2:
            cycles.append(cycle)
    return cycles, sigma


def main():
    # Find all matched ≥ 458 records in output/
    records = []
    for f in glob.glob("output/**/*.json", recursive=True):
        try:
            with open(f) as fp:
                d = json.load(fp)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        matched = d.get("matched")
        if not isinstance(matched, int):
            continue
        if matched < 458:
            continue
        if "INVALID" in f:
            continue
        records.append((matched, f))

    # Dedupe by content (we have known byte-identical copies)
    seen_hashes = set()
    dedup = []
    for matched, f in records:
        try:
            with open(f) as fp:
                blob = json.load(fp)
            url = blob.get("bucas_url", "")
        except Exception:
            continue
        if url and url in seen_hashes:
            continue
        if url:
            seen_hashes.add(url)
        dedup.append((matched, f))

    print(f"Records ≥ 458: {len(records)} found, {len(dedup)} unique by bucas URL")
    for m, f in sorted(dedup, key=lambda x: -x[0]):
        print(f"  {m} {f}")
    print()

    # Load all
    boards = {}
    for matched, f in dedup:
        pos_to_pid, pid_to_pos = load_placement(f)
        if pid_to_pos:
            label = f"{matched}-{Path(f).stem[:30]}"
            boards[label] = pid_to_pos

    print(f"Loaded {len(boards)} board placements")
    print()

    # Pairwise sigma analysis
    print("=" * 100)
    print(f"{'pair':<60} | {'Ham':>4} | {'cycles':<40}")
    print("=" * 100)
    labels = sorted(boards.keys())
    pair_data = []
    for a, b in combinations(labels, 2):
        cycles, sigma = sigma_decomposition(boards[a], boards[b])
        ham = sum(1 for pid in boards[a] if boards[a][pid] != boards[b].get(pid))
        cycle_lens = sorted([len(c) for c in cycles], reverse=True)
        cycle_str = "+".join(str(l) for l in cycle_lens) if cycle_lens else "(identity)"
        pair_data.append((a, b, ham, cycle_lens, cycle_str))
        # truncate label for display
        pair_label = f"{a[:28]} vs {b[:28]}"
        print(f"{pair_label:<60} | {ham:>4} | {cycle_str[:40]}")
    print()

    # Summary statistics
    print("=" * 70)
    print("CYCLE-LENGTH HISTOGRAM (across all pairs)")
    all_cycle_lens = collections.Counter()
    for _, _, _, lens, _ in pair_data:
        for l in lens:
            all_cycle_lens[l] += 1
    for l in sorted(all_cycle_lens.keys()):
        print(f"  cycle length {l:3d}: {all_cycle_lens[l]} occurrences")

    print()
    print("Pair-distance distribution:")
    hams = sorted([h for _, _, h, _, _ in pair_data])
    print(f"  min={min(hams)} median={hams[len(hams)//2]} max={max(hams)}")


if __name__ == "__main__":
    main()
