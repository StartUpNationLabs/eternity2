"""Dataset for board-completion training.

Reads boards from database-400-480/ and produces (input, target) tensors:
- input: 256 cells, with random masks (replaced by EMPTY)
- target: original (piece, rotation) at masked cells

Score-weighted: higher-scoring boards have more weight in training.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import torch
from torch.utils.data import Dataset


REPO = Path(__file__).resolve().parents[2]
DB = REPO / "database-400-480"

N_PIECES = 256
N_ROTATIONS = 4
N_CELLS = 256
EMPTY_PIECE = N_PIECES
EMPTY_ROTATION = N_ROTATIONS


def load_boards(min_score: int = 440) -> list[tuple[int, list[tuple[int, int]]]]:
    """Return list of (score, [(piece_id, rotation) at each of 256 cells]).
    Filtered to min_score+ for quality.
    """
    boards = []
    for f in sorted(DB.glob("*.json")):
        if f.name == "README.md":
            continue
        try:
            with open(f) as fh:
                d = json.load(fh)
        except Exception:
            continue
        pl = d.get("placement", [])
        if not pl:
            continue
        # Build position -> (piece, rotation)
        cells = [None] * N_CELLS
        for i, p in enumerate(pl):
            if not isinstance(p, dict):
                continue
            pos = p.get("pos", i)
            if "piece_id" not in p or "rotation" not in p:
                continue
            try:
                cells[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
            except (ValueError, TypeError):
                continue
        if any(c is None for c in cells):
            continue  # incomplete board
        score = int(d.get("matched", 0))
        if score < min_score:
            continue
        boards.append((score, cells))
    return boards


class BoardMaskedDataset(Dataset):
    """Each __getitem__ returns one training sample with random masking."""

    def __init__(
        self,
        boards: list,
        mask_min: int = 8,
        mask_max: int = 64,
    ):
        self.boards = boards
        self.mask_min = mask_min
        self.mask_max = mask_max

    def __len__(self):
        return len(self.boards)

    def __getitem__(self, idx):
        score, cells = self.boards[idx]
        # Sample mask size.
        n_mask = random.randint(self.mask_min, min(self.mask_max, N_CELLS - 1))
        masked_positions = random.sample(range(N_CELLS), n_mask)
        masked_set = set(masked_positions)

        # Build input tensors.
        pieces = torch.zeros(N_CELLS, dtype=torch.long)
        rotations = torch.zeros(N_CELLS, dtype=torch.long)
        targets_piece = torch.full((N_CELLS,), -100, dtype=torch.long)
        targets_rot = torch.full((N_CELLS,), -100, dtype=torch.long)

        for pos in range(N_CELLS):
            true_piece, true_rot = cells[pos]
            if pos in masked_set:
                # masked input → empty sentinel
                pieces[pos] = EMPTY_PIECE
                rotations[pos] = EMPTY_ROTATION
                targets_piece[pos] = true_piece
                targets_rot[pos] = true_rot
            else:
                pieces[pos] = true_piece
                rotations[pos] = true_rot

        # Score weight: linear in (score - 440) / (480 - 440)
        weight = max(0.0, (score - 440) / 40.0) + 0.1  # min weight 0.1
        return {
            "pieces": pieces,
            "rotations": rotations,
            "targets_piece": targets_piece,
            "targets_rot": targets_rot,
            "weight": torch.tensor(weight, dtype=torch.float32),
            "score": torch.tensor(score, dtype=torch.long),
        }
