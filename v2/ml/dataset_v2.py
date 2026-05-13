"""Vol-28 position-relative dataset.

Each training sample yields:
  cell_feats: (n_cells, 13) raw board features
  target_pos: int            the cell the expert placed at
  cand_edges: (C, 4)         C candidates' edges (color ids)
  target_idx: int            which candidate index is the expert's choice

Candidates: always include the expert's true candidate; fill the rest
with N-1 negatives sampled from pieces' rotations that match the
border-mask at the target cell.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

import numpy as np
import torch
from torch.utils.data import Dataset

from dataset import PuzzleRecord, _rotate, load_jsonl


BORDER = 0


def piece_rotations(edges: List[int]) -> List[List[int]]:
    return [_rotate(edges, r) for r in range(4)]


def fits_border(rotated_edges: List[int], border_mask: List[bool]) -> bool:
    for i in range(4):
        is_border = rotated_edges[i] == BORDER
        if is_border != border_mask[i]:
            return False
    return True


def border_mask_for(pos: int, width: int, height: int) -> List[bool]:
    y, x = divmod(pos, width)
    return [y == 0, x == width - 1, y == height - 1, x == 0]


@dataclass
class _SampleIndex:
    rec_idx: int
    depth: int


class TrajectoryDatasetV2(Dataset):
    def __init__(self, records: List[PuzzleRecord], n_candidates: int = 16, seed: int = 42):
        self.records = records
        self.n_candidates = n_candidates
        self.rng = random.Random(seed)
        self.index: List[_SampleIndex] = []
        self._piece_rot_cache: List[List[List[List[int]]]] = []
        for r_idx, rec in enumerate(records):
            rotations = [piece_rotations(p["edges"]) for p in rec.pieces]
            self._piece_rot_cache.append(rotations)
            for d in range(len(rec.expert_trajectory)):
                self.index.append(_SampleIndex(r_idx, d))

    def __len__(self) -> int:
        return len(self.index)

    def _build_state(self, rec: PuzzleRecord, depth: int):
        size = rec.size
        n_cells = size * size
        piece_edges = {p["id"]: p["edges"] for p in rec.pieces}
        placed_edges = np.zeros((n_cells, 4), dtype=np.int64)
        placed_flag = np.zeros(n_cells, dtype=np.int64)
        for step in rec.expert_trajectory[:depth]:
            pos = step["position"]
            pid = step["piece_id"]
            rot = step["rotation"]
            placed_flag[pos] = 1
            placed_edges[pos] = _rotate(piece_edges[pid], rot)
        used = {step["piece_id"] for step in rec.expert_trajectory[:depth]}
        return placed_edges, placed_flag, used

    def __getitem__(self, i: int):
        idx = self.index[i]
        rec = self.records[idx.rec_idx]
        depth = idx.depth
        size = rec.size
        n_cells = size * size

        placed_edges, placed_flag, used = self._build_state(rec, depth)
        target = rec.expert_trajectory[depth]
        target_pos = int(target["position"])
        target_pid = int(target["piece_id"])
        target_rot = int(target["rotation"])

        nb_known = np.zeros((n_cells, 4), dtype=np.int64)
        border_mask = np.zeros((n_cells, 4), dtype=np.int64)
        for y in range(size):
            for x in range(size):
                pos = y * size + x
                if y == 0:
                    border_mask[pos, 0] = 1
                    nb_known[pos, 0] = 1
                elif placed_flag[(y - 1) * size + x] == 1:
                    nb_known[pos, 0] = 1
                if x == size - 1:
                    border_mask[pos, 1] = 1
                    nb_known[pos, 1] = 1
                elif placed_flag[y * size + (x + 1)] == 1:
                    nb_known[pos, 1] = 1
                if y == size - 1:
                    border_mask[pos, 2] = 1
                    nb_known[pos, 2] = 1
                elif placed_flag[(y + 1) * size + x] == 1:
                    nb_known[pos, 2] = 1
                if x == 0:
                    border_mask[pos, 3] = 1
                    nb_known[pos, 3] = 1
                elif placed_flag[y * size + (x - 1)] == 1:
                    nb_known[pos, 3] = 1
        feats = np.concatenate([
            placed_edges, nb_known, placed_flag[:, None], border_mask,
        ], axis=1).astype(np.float32)

        rotations = self._piece_rot_cache[idx.rec_idx]
        expert_edges = rotations[target_pid][target_rot]
        bm = border_mask_for(target_pos, size, size)
        candidates: List[List[int]] = [expert_edges]
        seen = {(target_pid, target_rot)}
        attempts = 0
        while len(candidates) < self.n_candidates and attempts < 200:
            attempts += 1
            pid = self.rng.randrange(len(rec.pieces))
            rot = self.rng.randrange(4)
            if (pid, rot) in seen or pid in used:
                continue
            ce = rotations[pid][rot]
            if not fits_border(ce, bm):
                continue
            seen.add((pid, rot))
            candidates.append(ce)
        while len(candidates) < self.n_candidates:
            candidates.append(expert_edges)

        order = list(range(self.n_candidates))
        self.rng.shuffle(order)
        cand_arr = np.array([candidates[k] for k in order], dtype=np.int64)
        target_idx = order.index(0)

        return (
            torch.from_numpy(feats),
            torch.tensor(target_pos, dtype=torch.long),
            torch.from_numpy(cand_arr),
            torch.tensor(target_idx, dtype=torch.long),
        )


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "data/train_6x6_5c.jsonl"
    recs = load_jsonl(path)
    print(f"loaded {len(recs)} puzzles")
    ds = TrajectoryDatasetV2(recs[:50], n_candidates=12)
    print(f"{len(ds)} samples")
    feats, tp, cand, tidx = ds[0]
    print(f"feats shape: {tuple(feats.shape)} target_pos={tp.item()}")
    print(f"cand_edges shape: {tuple(cand.shape)} target_idx={tidx.item()}")
    print(f"expert edges: {cand[tidx].tolist()}")
