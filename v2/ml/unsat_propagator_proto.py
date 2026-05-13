"""Vol-32+ bootstrap: unsat-clause-propagator prototype.

Parses capiman/e2's literal-encoding table (output/capiman_e2/e2_info.c)
and one or more unsat CNF files (output/capiman_e2/*.cnf.gz) into a
fast lookup table: literal -> forbidden_literals.

The runtime check is: when the engine places piece P at position F in
rotation R, look up the corresponding literal X, then for every
literal Y in forbidden_literals[X], remove the placement decoded from
Y from the relevant domain.

Prototype outputs:
  - A summary of clause counts per file.
  - A literal-decoder table written as JSON for Rust ingestion.
  - A sample lookup: given literal 1 ((Field=0, Card=1, Rot=1)), how
    many forbidden partners exist?
"""

from __future__ import annotations

import gzip
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from time import time


CAPIMAN = Path("output/capiman_e2")


def parse_e2_info(path: Path):
    """Parse e2_info.c rows.
    Each row: {  Index, Field, Card, Rotation, PatternN, PatternE, PatternS, PatternW }.
    Returns dict[literal_index] -> dict with keys field/card/rotation/...
    AND inverse_map (field, card, rotation) -> literal_index.
    """
    rows = []
    pat = re.compile(r"^\s*\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\}")
    with open(path) as f:
        for line in f:
            m = pat.match(line)
            if not m:
                continue
            idx, field, card, rot, pn, pe, ps, pw = [int(x) for x in m.groups()]
            rows.append((idx, field, card, rot, pn, pe, ps, pw))
    by_idx = {r[0]: {"field": r[1], "card": r[2], "rotation": r[3],
                     "pn": r[4], "pe": r[5], "ps": r[6], "pw": r[7]} for r in rows}
    by_fcr = {(r[1], r[2], r[3]): r[0] for r in rows}
    return rows, by_idx, by_fcr


def count_unsat_clauses(path: Path, sample_max=None):
    """Count clauses and return list of (a, b) literal pairs (negated -> negated)."""
    pairs = []
    with gzip.open(path, "rt") as f:
        for i, line in enumerate(f):
            if sample_max is not None and i >= sample_max:
                break
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            # Format: "-X -Y 0" — both literals negated, "0" terminator
            if len(parts) != 3 or parts[-1] != "0":
                continue
            try:
                a = int(parts[0])
                b = int(parts[1])
            except ValueError:
                continue
            if a >= 0 or b >= 0:
                # Some lines could be unit clauses or longer; skip
                continue
            pairs.append((-a, -b))   # store positive literals
    return pairs


def build_forbidden_map(pairs):
    """Build literal -> set of forbidden partners."""
    m = defaultdict(set)
    for a, b in pairs:
        m[a].add(b)
        m[b].add(a)
    return m


def main():
    info_path = CAPIMAN / "e2_info.c"
    if not info_path.exists():
        print(f"FATAL: {info_path} not found", file=sys.stderr)
        sys.exit(1)

    print("Parsing e2_info.c ...")
    t0 = time()
    rows, by_idx, by_fcr = parse_e2_info(info_path)
    dt = time() - t0
    print(f"  {len(rows)} literals parsed in {dt:.2f}s")
    print(f"  max index = {max(r[0] for r in rows)}")
    fields = sorted(set(r[1] for r in rows))
    cards = sorted(set(r[2] for r in rows))
    rots = sorted(set(r[3] for r in rows))
    print(f"  fields = {len(fields)} (0..{max(fields)})")
    print(f"  cards = {len(cards)} (1..{max(cards)})")
    print(f"  rotations = {sorted(rots)}")

    # Save the decoder to JSON for Rust use
    out = Path("output/vol-32/unsat_propagator")
    out.mkdir(parents=True, exist_ok=True)
    decoder = {"literal_to_fcr": {str(idx): [r["field"], r["card"]-1, r["rotation"]-1]
                                   for idx, r in by_idx.items()}}
    with open(out / "literal_decoder.json", "w") as f:
        json.dump(decoder, f)
    print(f"  decoder -> {out / 'literal_decoder.json'} ({(out / 'literal_decoder.json').stat().st_size / 1024:.1f} KB)")

    # Parse smallest CNF file as a sanity check
    cnf_files = sorted(CAPIMAN.glob("*.cnf.gz"), key=lambda p: p.stat().st_size)
    print(f"\nFound {len(cnf_files)} CNF files; smallest first:")
    total = 0
    for p in cnf_files[:5]:
        size = p.stat().st_size
        print(f"  {p.name} ({size/1024:.1f} KB)")

    # Parse a small + a medium + the largest one
    samples = [cnf_files[0], cnf_files[len(cnf_files)//2], cnf_files[-1]]
    full_map = defaultdict(set)
    for p in samples:
        print(f"\nParsing {p.name} ...")
        t0 = time()
        pairs = count_unsat_clauses(p)
        dt = time() - t0
        print(f"  {len(pairs)} clauses in {dt:.2f}s")
        for a, b in pairs:
            full_map[a].add(b)
            full_map[b].add(a)

    # Stats
    deg = [len(s) for s in full_map.values()]
    if deg:
        print(f"\nForbidden-partner-count distribution across {len(full_map)} literals:")
        print(f"  total entries: {sum(deg)}")
        print(f"  mean partners: {sum(deg)/len(deg):.1f}")
        print(f"  max partners: {max(deg)}")
        print(f"  literals with ≥10 partners: {sum(1 for d in deg if d >= 10)}")
        print(f"  literals with ≥100 partners: {sum(1 for d in deg if d >= 100)}")

    # Sample lookup
    print(f"\nSample lookup: literal 1 = field={by_idx[1]['field']}, card={by_idx[1]['card']-1}, rot={by_idx[1]['rotation']-1}")
    forb = list(full_map.get(1, []))[:5]
    print(f"  forbidden partners (sample 5): {forb}")
    for f in forb:
        r = by_idx[f]
        print(f"    lit {f}: field={r['field']}, card={r['card']-1}, rot={r['rotation']-1}")


if __name__ == "__main__":
    main()
