"""JSONL puzzle/trajectory loader for vol-26 learned-value-order training.

Each line in the JSONL produced by `cargo run -p eternity2-ml-export --bin
gen-export` is one puzzle record with:
  - seed, size, color_count
  - pieces: [{id, edges=[t,r,b,l]}] (length size*size)
  - canonical_solution: list of {position, piece_id, rotation}
  - expert_trajectory: list of {depth, position, piece_id, rotation}

A training sample is one (partial_board, chosen_placement) pair, derived by
unrolling the expert trajectory: at depth d, the partial holds steps 0..d-1
and the target is step d's (piece_id, rotation).

We encode the partial as a per-cell feature tensor and label the target as
the index into the full action space (piece_id * 4 + rotation). Since the
target lives at depth d's position (already known via the trajectory), the
model is asked to predict only the piece_id+rotation given the position.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset


@dataclass
class PuzzleRecord:
    seed: int
    size: int
    color_count: int
    pieces: list[dict]
    canonical_solution: list[dict]
    expert_trajectory: list[dict]


def load_jsonl(path: str | Path) -> list[PuzzleRecord]:
    out: list[PuzzleRecord] = []
    with open(path, "r") as f:
        for line in f:
            row = json.loads(line)
            out.append(PuzzleRecord(**row))
    return out


# Action space: piece_id ∈ [0, n_pieces), rotation ∈ [0, 4). One flat index.
def action_index(piece_id: int, rotation: int) -> int:
    return piece_id * 4 + rotation


def action_count(n_pieces: int) -> int:
    return n_pieces * 4


class TrajectoryDataset(Dataset):
    """Yields (state, target_position, target_action) tuples.

    state shape: (n_cells, FEAT_DIM) where FEAT_DIM = 4 (placed-piece edges,
        BORDER=0) + 4 (placed-flag per side, 1=placed neighbour known) + 1
        (is-placed flag) + 4 (border-mask per side). Total = 13 features
        per cell.

    target_position: int (the cell the engine placed at this step).

    target_action: int (piece_id * 4 + rotation that the engine placed).
    """

    FEAT_DIM = 13

    def __init__(self, records: list[PuzzleRecord]):
        self.records = records
        # Pre-compute (record_idx, depth) flat index. Drop depth=0 only if
        # we want to skip empty-board states; we keep them — predicting the
        # first placement is part of the task.
        self.index: list[tuple[int, int]] = []
        for r_idx, rec in enumerate(records):
            for d in range(len(rec.expert_trajectory)):
                self.index.append((r_idx, d))

    def __len__(self) -> int:
        return len(self.index)

    def __getitem__(self, i: int):
        r_idx, depth = self.index[i]
        rec = self.records[r_idx]
        size = rec.size
        n_cells = size * size

        # Build piece lookup: id -> edges array (length 4).
        piece_edges: dict[int, list[int]] = {p["id"]: p["edges"] for p in rec.pieces}

        # Apply rotations from steps 0..depth-1 to build the partial.
        placed_edges = np.zeros((n_cells, 4), dtype=np.int64)
        placed_flag = np.zeros((n_cells,), dtype=np.int64)
        for step in rec.expert_trajectory[:depth]:
            pos = step["position"]
            pid = step["piece_id"]
            rot = step["rotation"]
            placed_flag[pos] = 1
            placed_edges[pos] = _rotate(piece_edges[pid], rot)

        # Per-side neighbour-known flag: for each cell, is the neighbour on
        # this side a placed cell (or the gray border)?
        nb_known = np.zeros((n_cells, 4), dtype=np.int64)
        # Border mask: 1 if this side touches gray border.
        border_mask = np.zeros((n_cells, 4), dtype=np.int64)
        for y in range(size):
            for x in range(size):
                pos = y * size + x
                # top
                if y == 0:
                    border_mask[pos, 0] = 1
                    nb_known[pos, 0] = 1
                elif placed_flag[(y - 1) * size + x] == 1:
                    nb_known[pos, 0] = 1
                # right
                if x == size - 1:
                    border_mask[pos, 1] = 1
                    nb_known[pos, 1] = 1
                elif placed_flag[y * size + (x + 1)] == 1:
                    nb_known[pos, 1] = 1
                # bottom
                if y == size - 1:
                    border_mask[pos, 2] = 1
                    nb_known[pos, 2] = 1
                elif placed_flag[(y + 1) * size + x] == 1:
                    nb_known[pos, 2] = 1
                # left
                if x == 0:
                    border_mask[pos, 3] = 1
                    nb_known[pos, 3] = 1
                elif placed_flag[y * size + (x - 1)] == 1:
                    nb_known[pos, 3] = 1

        # FEAT_DIM=13 layout: edges (4) + nb_known (4) + placed (1) + border_mask (4)
        feats = np.concatenate([
            placed_edges,
            nb_known,
            placed_flag[:, None],
            border_mask,
        ], axis=1).astype(np.float32)

        target = rec.expert_trajectory[depth]
        target_pos = int(target["position"])
        target_action = action_index(int(target["piece_id"]), int(target["rotation"]))

        return (
            torch.from_numpy(feats),
            torch.tensor(target_pos, dtype=torch.long),
            torch.tensor(target_action, dtype=torch.long),
        )


def _rotate(edges: list[int], r: int) -> list[int]:
    """Rotate [t, r, b, l] by `r` quarter-turns clockwise."""
    # R90 sends (t, r, b, l) -> (l, t, r, b) — matches Rust core::Edges::rotated.
    t, ri, b, l = edges
    if r == 0:
        return [t, ri, b, l]
    if r == 1:
        return [l, t, ri, b]
    if r == 2:
        return [b, l, t, ri]
    return [ri, b, l, t]


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/train_6x6_5c.jsonl"
    recs = load_jsonl(path)
    print(f"loaded {len(recs)} puzzles from {path}")
    ds = TrajectoryDataset(recs)
    print(f"{len(ds)} (state, target) samples")
    feats, pos, action = ds[0]
    print(f"feat shape: {tuple(feats.shape)} target_pos={pos.item()} target_action={action.item()}")
