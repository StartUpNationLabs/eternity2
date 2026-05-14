#!/usr/bin/env python3
"""Find the consensus 'core' of piece placements across 5 distinct 457 clusters.

A cell is in the consensus core if N of M clusters agree on
(piece_id, rotation) at that position.
"""
import json
from collections import Counter
from pathlib import Path

# One representative per cluster (vol-32 s7 + s4 are different clusters,
# vol-34 t1 + t3, vol-35 f255).
CLUSTERS = {
    "A_blackwood_s7": "output/vol-32/RECORD_TIE_457_blackwood_mrv_5min_seed7.json",
    "B_blackwood_s4": "output/vol-32/RECORD_TIE_457_blackwood_mrv_30min_seed4.json",
    "C_vol34_t1": "output/vol-34/t3_signal/REAL_RECORD_TIE_457_vol34_t1signal_seed1.json",
    "D_vol34_t3": "output/vol-34/t3_signal/RECORD_TIE_457_vol34_t3_t01_seed1.json",
    "E_vol35_f255": "output/vol-35/records/RECORD_TIE_457_vol35_family255_seed1.json",
}


def load_grid(p):
    b = json.load(open(p))
    return {c["pos"]: (c["piece_id"], c["rotation"]) for c in b["placement"]}


def main():
    grids = {k: load_grid(v) for k, v in CLUSTERS.items()}
    M = len(grids)
    N = 16

    cell_consensus = {}
    for pos in range(N * N):
        votes = Counter(g[pos] for g in grids.values() if pos in g)
        if not votes:
            cell_consensus[pos] = (0, None)
            continue
        top, count = votes.most_common(1)[0]
        cell_consensus[pos] = (count, top)

    print(f"=== Consensus across {M} clusters (16x16) ===")
    print("Grid (each cell shows # clusters agreeing on piece+rotation):")
    for row in range(N):
        line = []
        for col in range(N):
            pos = row * N + col
            count = cell_consensus[pos][0]
            line.append(str(count) if count > 0 else ".")
        print("  " + " ".join(line))

    print()
    by_count = Counter(c[0] for c in cell_consensus.values())
    print(f"Cells with N-cluster agreement:")
    for n in range(M, -1, -1):
        cells = by_count.get(n, 0)
        pct = 100 * cells / (N * N)
        print(f"  {n}/{M}: {cells:3d} cells ({pct:.1f}%)")

    print()
    print("=== Piece-only consensus (ignore rotation) ===")
    piece_consensus = {}
    for pos in range(N * N):
        votes = Counter((g[pos][0],) for g in grids.values() if pos in g)
        top, count = votes.most_common(1)[0]
        piece_consensus[pos] = (count, top[0])

    by_count = Counter(c[0] for c in piece_consensus.values())
    print(f"Cells with N-cluster agreement on PIECE-only:")
    for n in range(M, -1, -1):
        cells = by_count.get(n, 0)
        pct = 100 * cells / (N * N)
        print(f"  {n}/{M}: {cells:3d} cells ({pct:.1f}%)")

    print()
    print("=== Piece-only consensus map ===")
    for row in range(N):
        line = []
        for col in range(N):
            pos = row * N + col
            count = piece_consensus[pos][0]
            line.append(str(count) if count > 0 else ".")
        print("  " + " ".join(line))

    # Output: cells where ALL clusters agree
    print()
    full_agree = [pos for pos, (c, _) in cell_consensus.items() if c == M]
    full_agree_piece = [pos for pos, (c, _) in piece_consensus.items() if c == M]
    print(f"\nFull agreement (piece+rotation): {len(full_agree)} cells")
    print(f"  {full_agree}")
    print(f"\nFull agreement (piece only):     {len(full_agree_piece)} cells")
    print(f"  {full_agree_piece}")

    # Save consensus hints
    consensus_hints = []
    for pos, (count, val) in cell_consensus.items():
        if count == M and val is not None:
            consensus_hints.append({
                "pos": pos,
                "piece_id": val[0],
                "rotation": val[1],
            })
    out_path = Path("output/vol-35/457_consensus_hints.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"hints": consensus_hints, "n_clusters": M}, f, indent=2)
    print(f"\nSaved {len(consensus_hints)} consensus hints to {out_path}")


if __name__ == "__main__":
    main()
