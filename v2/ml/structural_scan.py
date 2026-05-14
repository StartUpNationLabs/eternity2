#!/usr/bin/env python3
"""
Structural invariant scanner across verified records.

Goal: find patterns NEVER documented. Mine records for:
1. Position-locked pieces: positions where one piece is fixed across all records.
2. Position-flexible-but-rotation-locked: same piece at varying positions but
   always same rotation.
3. Forbidden adjacencies: piece-pair (P1, P2) on direction d that never appear.
4. Rare-cell statistics: positions where domain converges across records.

Records (post pin-hints retraction):
- vol-32 458 (3/5 hints)
- vol-32 blackwood_mrv ×3 (all 5/5 hints)
- vol-35 deep458 458 (byte-identical to vol-32 458)
- vol-35 deep458 full/diverse (3/5 hints)
- vol-36 canonical 454 (5/5 hints) — new

Discoveries should produce candidates for:
- New propagator (forbidden-pair pruning)
- New value-order (high-frequency placements first)
- Pre-commitment via "frozen across all records" cells
"""
import json
import sys
import collections
from collections import defaultdict, Counter
from pathlib import Path

RECORDS = [
    "output/vol-32/RECORD_BREAK_458_vanilla_fast_alns.json",
    "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json",
    "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed10.json",
    "output/vol-32/RECORD_TIE_457_blackwood_mrv_30min_seed4.json",
    "output/vol-35/records/RECORD_TIE_458_vol35_deep458_winning5_seed5.json",
    "output/vol-35/records/RECORD_TIE_457_vol35_deep458_full_seed5_3hints.json",
    "output/vol-35/records/RECORD_TIE_457_vol35_deep458_diverse_seed5_3hints.json",
    "output/vol-36/records/RECORD_CANONICAL_454_vol36_seed5.json",
]

N = 16


def load_board(path):
    d = json.load(open(path))
    pl = d["placement"]
    result = {}
    for p in pl:
        if p is None:
            continue
        if "pos" in p:
            result[p["pos"]] = (p["piece_id"], p["rotation"])
    return result


def main():
    boards = []
    for path in RECORDS:
        if not Path(path).exists():
            print(f"MISSING: {path}", file=sys.stderr)
            continue
        b = load_board(path)
        if len(b) != 256:
            print(f"INCOMPLETE: {path} has {len(b)}", file=sys.stderr)
            continue
        boards.append((path, b))
    print(f"Loaded {len(boards)} complete records")

    # Skip vol-35 byte-identical duplicate of vol-32 458 (same board)
    # (Find duplicates by board hash)
    seen_hashes = {}
    dedup = []
    for path, b in boards:
        h = hash(tuple(sorted(b.items())))
        if h in seen_hashes:
            print(f"  DUP: {path} = {seen_hashes[h]}")
            continue
        seen_hashes[h] = path
        dedup.append((path, b))
    print(f"After dedup: {len(dedup)} distinct records")
    boards = dedup

    # 1. Position-locked pieces
    print()
    print("=== 1. POSITION-LOCKED CELLS (same pid across all records) ===")
    locked = []
    for pos in range(256):
        pids = set(b.get(pos, (None,))[0] for _, b in boards)
        pids.discard(None)
        if len(pids) == 1:
            (pid,) = pids
            rots = set(b.get(pos, (None, None))[1] for _, b in boards)
            rots.discard(None)
            rot_str = f"rot=ALL_{list(rots)[0]}" if len(rots) == 1 else f"rot={sorted(rots)}"
            x, y = pos % N, pos // N
            locked.append((pos, pid, list(rots)[0] if len(rots) == 1 else None))
            print(f"  pos {pos:3d} (x={x:2d},y={y:2d}): pid={pid:3d}  {rot_str}")
    print(f"\nTotal position-locked cells: {len(locked)}")
    print(f"  (Canonical hints = 5; new structural-backbone cells = {len(locked) - 5})")

    # 2. Position-flexible piece-rotation locked (per piece, rot is always same when it appears)
    print()
    print("=== 2. PIECE-ROTATION INVARIANT (each piece always at same rotation) ===")
    piece_rots = defaultdict(set)
    piece_positions = defaultdict(set)
    for _, b in boards:
        for pos, (pid, rot) in b.items():
            piece_rots[pid].add(rot)
            piece_positions[pid].add(pos)
    fixed_rot_pieces = [pid for pid, rs in piece_rots.items() if len(rs) == 1]
    print(f"Pieces with fixed rotation across all records: {len(fixed_rot_pieces)}/256")
    # Top 10 most-flexible pieces
    flex = sorted(piece_rots.items(), key=lambda x: -len(x[1]))[:10]
    print("Most-flexible pieces (used in many different rotations):")
    for pid, rs in flex:
        positions = piece_positions[pid]
        print(f"  pid {pid:3d}: {len(rs)} rotations, {len(positions)} distinct positions")

    # 3. Forbidden adjacencies: which (pid1, pid2, direction) NEVER appear across records?
    # Direction: 0=horizontal (right of pid1), 1=vertical (below pid1)
    print()
    print("=== 3. ADJACENCY STATISTICS ===")
    h_adj = defaultdict(int)  # (pid1, pid2) → count of records with pid1.right == pid2
    v_adj = defaultdict(int)
    for _, b in boards:
        for pos, (pid, rot) in b.items():
            x, y = pos % N, pos // N
            if x + 1 < N and (pos + 1) in b:
                npid, _ = b[pos + 1]
                h_adj[(pid, npid)] += 1
            if y + 1 < N and (pos + N) in b:
                npid, _ = b[pos + N]
                v_adj[(pid, npid)] += 1
    print(f"Distinct horizontal piece-pairs observed: {len(h_adj)}")
    print(f"Distinct vertical piece-pairs observed: {len(v_adj)}")
    print(f"Distinct pairs total: {len(h_adj) + len(v_adj)}")
    # Pairs that appear in ALL records (likely structural)
    all_h_pairs = [k for k, v in h_adj.items() if v == len(boards)]
    all_v_pairs = [k for k, v in v_adj.items() if v == len(boards)]
    print(f"Horizontal pairs in ALL {len(boards)} records: {len(all_h_pairs)}")
    print(f"Vertical pairs in ALL {len(boards)} records: {len(all_v_pairs)}")

    # 4. Cell statistics: at each cell, how many distinct (pid, rot) values appeared?
    print()
    print("=== 4. CELL DIVERSITY (variant count per position) ===")
    cell_diversity = []
    for pos in range(256):
        prs = set((b.get(pos, (None, None))) for _, b in boards)
        prs.discard((None, None))
        cell_diversity.append((pos, len(prs)))
    diversity_counts = Counter(d for _, d in cell_diversity)
    print(f"Cell diversity distribution (distinct (pid,rot) seen at each cell):")
    for k in sorted(diversity_counts.keys()):
        print(f"  diversity={k}: {diversity_counts[k]} cells")

    # 5. Print all-records distinct piece-rot pairs (= "vocabulary" of solutions)
    print()
    print("=== 5. VOCABULARY (distinct (pid, rot) pairs across records) ===")
    all_pairs = set()
    for _, b in boards:
        for pid, rot in b.values():
            all_pairs.add((pid, rot))
    print(f"Total distinct (pid, rot) across records: {len(all_pairs)}")
    print(f"Total possible: 256*4 = 1024")
    # 256 unique pieces × 4 rotations = 1024 possible; how many appear?
    pids_appearing = set(p for p, _ in all_pairs)
    print(f"Distinct pieces appearing: {len(pids_appearing)}/256")
    rare_pieces = [pid for pid in range(256) if pid not in pids_appearing]
    if rare_pieces:
        print(f"Pieces NEVER seen at non-hint position: {rare_pieces[:20]}...")

    # 6. Discoveries: candidates for propagator (positions with low diversity = strong prior)
    print()
    print("=== 6. STRUCTURAL BACKBONE CANDIDATES ===")
    print("(positions where ALL records agree on the same (pid, rot) — beyond hints)")
    canonical_hint_positions = {34, 45, 135, 210, 221}
    backbone = []
    for pos in range(256):
        prs = set((b.get(pos, (None, None))) for _, b in boards)
        prs.discard((None, None))
        if len(prs) == 1:
            (pid, rot) = next(iter(prs))
            if pos not in canonical_hint_positions:
                backbone.append((pos, pid, rot))
    if backbone:
        print(f"NEW backbone cells: {len(backbone)}")
        for pos, pid, rot in backbone[:30]:
            x, y = pos % N, pos // N
            print(f"  pos {pos:3d} (x={x:2d},y={y:2d}): pid={pid:3d}, rot={rot}")
        if len(backbone) > 30:
            print(f"  ... and {len(backbone) - 30} more")
    else:
        print("No backbone cells beyond canonical hints.")

    # 7. Near-invariant cells (diversity=2): could be SOFT hints
    print()
    print("=== 7. NEAR-INVARIANT (diversity=2) candidates ===")
    near = []
    for pos in range(256):
        prs_with_path = [(b.get(pos, (None, None))) for _, b in boards]
        prs = [p for p in prs_with_path if p != (None, None)]
        unique_prs = set(prs)
        if len(unique_prs) == 2 and pos not in canonical_hint_positions:
            # Show frequency
            c = Counter(prs)
            top, top_n = c.most_common(1)[0]
            near.append((pos, top, top_n, sum(c.values())))
    print(f"Diversity=2 cells (NEW soft-hint candidates): {len(near)}")
    for pos, (pid, rot), n, total in near[:30]:
        x, y = pos % N, pos // N
        print(f"  pos {pos:3d} (x={x:2d},y={y:2d}): top=pid{pid:3d}/rot{rot} ({n}/{total} records)")
    if len(near) > 30:
        print(f"  ... and {len(near) - 30} more")

    # 8. Most-frequent (pid, rot) per position (value-order signal)
    # For each position, sort variants by frequency
    print()
    print("=== 8. CELL-LEVEL VALUE-ORDER (top variant per position) ===")
    # Useful for engine integration: pre-sort candidate list at each position
    # by frequency across records.
    cell_top_variants = {}
    for pos in range(256):
        prs = [b.get(pos, (None, None)) for _, b in boards]
        prs = [p for p in prs if p != (None, None)]
        c = Counter(prs)
        sorted_variants = c.most_common()
        cell_top_variants[pos] = sorted_variants
    # Dump to JSON for use in engine
    out_path = Path("output/vol-37_revised/cell_value_order.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_safe = {
        str(pos): [{"piece_id": pr[0], "rotation": pr[1], "count": cnt}
                   for pr, cnt in variants]
        for pos, variants in cell_top_variants.items()
    }
    with open(out_path, "w") as f:
        json.dump({"n_records": len(boards), "value_order": json_safe}, f, indent=2)
    print(f"Cell-level value-order dumped to {out_path}")
    # Show summary of variant counts
    total_variants_per_cell = [len(v) for v in cell_top_variants.values()]
    avg_variants = sum(total_variants_per_cell) / len(total_variants_per_cell)
    print(f"  avg distinct (pid, rot) per cell: {avg_variants:.2f}")
    print(f"  cells with 1 variant: {sum(1 for v in total_variants_per_cell if v == 1)}")
    print(f"  cells with ≤2 variants: {sum(1 for v in total_variants_per_cell if v <= 2)}")
    print(f"  cells with ≤3 variants: {sum(1 for v in total_variants_per_cell if v <= 3)}")


if __name__ == "__main__":
    main()
