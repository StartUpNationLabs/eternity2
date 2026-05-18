"""Synthetic E2-family board generator for transformer training.

Generate random 16×16 puzzles with C colors that have a known canonical
solution (Selby-Riordan style: pick interior colors, build pieces, shuffle).

Each board sample:
1. Generate random 16×16 layout with random colors (1..C interior, 0 border)
2. Extract 256 pieces from this layout (each cell becomes a piece)
3. Shuffle pieces (randomly assign piece IDs)
4. The canonical solution is: "which piece goes where" in the original layout

Training target: predict (piece_id, rotation) at masked cells given context.

This is structurally identical to canonical E2 — same dimensions, same color
count (we use C=22), same edge-matching constraints. The MODEL learns the
edge-matching structure, transfers to canonical E2 at inference.
"""

from __future__ import annotations

import random
from typing import Optional

import torch
import numpy as np


N_PIECES = 256
N_ROTATIONS = 4
N_CELLS = 256
EMPTY_PIECE = N_PIECES
EMPTY_ROTATION = N_ROTATIONS
W = 16
BORDER_COLOR = 0  # 0 = border (gray)


def generate_synthetic_board(n_colors: int, rng: Optional[random.Random] = None) -> tuple[list, list]:
    """Generate one synthetic E2-family board.

    Returns:
        pieces: 256 piece-tuples (top, right, bottom, left), pieces are in
                "shuffled" order — piece_id = i is at position labels[i] in canonical.
        canonical_placement: 256 (piece_id, rotation) pairs, indexed by
                             grid position (0..255 row-major).

    The piece set:
    - Interior cells in a 16×16 grid generate pieces whose 4 sides are
      colors of adjacent horizontal/vertical edges.
    - Border cells have BORDER_COLOR on the outward-facing side.
    """
    if rng is None:
        rng = random.Random()

    # Step 1: assign random colors to interior horizontal/vertical edges.
    # Horizontal edges: W*(W-1) horizontal between rows; same for vertical.
    n_horiz = W * (W - 1)
    n_vert = W * (W - 1)
    horiz_edges = [rng.randint(1, n_colors) for _ in range(n_horiz)]
    vert_edges = [rng.randint(1, n_colors) for _ in range(n_vert)]

    # Ensure every color appears at least once: replace some random edges
    # with each unused color. This matches the Selby-Riordan generator.
    all_edges = horiz_edges + vert_edges
    used_colors = set(all_edges)
    missing = [c for c in range(1, n_colors + 1) if c not in used_colors]
    if missing:
        positions_to_replace = rng.sample(range(len(all_edges)), len(missing))
        for pos, color in zip(positions_to_replace, missing):
            all_edges[pos] = color
        horiz_edges = all_edges[:n_horiz]
        vert_edges = all_edges[n_horiz:]

    # Step 2: build per-cell pieces with edges in (N, E, S, W) order.
    canonical_pieces = []  # canonical_pieces[pos] = (N, E, S, W)
    for r in range(W):
        for c in range(W):
            N = BORDER_COLOR if r == 0 else horiz_edges[(r - 1) * W + c]
            S = BORDER_COLOR if r == W - 1 else horiz_edges[r * W + c]
            W_ = BORDER_COLOR if c == 0 else vert_edges[r * (W - 1) + (c - 1)]
            E = BORDER_COLOR if c == W - 1 else vert_edges[r * (W - 1) + c]
            canonical_pieces.append((N, E, S, W_))

    # Step 3: shuffle: piece_id i → original cell labels[i].
    # And rotation: apply random rotation to each piece.
    perm = list(range(N_CELLS))
    rng.shuffle(perm)
    # piece_id i corresponds to position perm[i] in the canonical solution.
    # Apply random rotation per piece.
    rotations_applied = [rng.randint(0, 3) for _ in range(N_CELLS)]

    # Build "pieces" list in piece_id order (i.e., shuffled).
    # pieces[piece_id] = the rotated piece tuple.
    pieces = [None] * N_CELLS
    for pid in range(N_CELLS):
        canonical_pos = perm[pid]
        rot = rotations_applied[pid]
        original = canonical_pieces[canonical_pos]
        rotated = rotate_piece(original, rot)
        pieces[pid] = rotated

    # Step 4: canonical placement: cell `canonical_pos` should hold piece
    # `pid` with rotation = -rot mod 4 (to undo the applied rotation).
    canonical_placement = [None] * N_CELLS
    for pid in range(N_CELLS):
        canonical_pos = perm[pid]
        rot_applied = rotations_applied[pid]
        # To match the original edges, the placement rotation must be
        # (4 - rot_applied) % 4 (since piece is already rotated by rot_applied)
        placement_rot = (4 - rot_applied) % 4
        canonical_placement[canonical_pos] = (pid, placement_rot)

    return pieces, canonical_placement


def rotate_piece(piece: tuple, r: int) -> tuple:
    """Rotate piece by r * 90° clockwise. piece = (N, E, S, W)."""
    N, E, S, W_ = piece
    if r == 0: return (N, E, S, W_)
    if r == 1: return (W_, N, E, S)
    if r == 2: return (S, W_, N, E)
    if r == 3: return (E, S, W_, N)
    raise ValueError(r)


class SyntheticBoardDataset(torch.utils.data.IterableDataset):
    """Infinite stream of synthetic boards with random masking.

    Each __iter__ yields one training sample. Use __len__ for pseudo-epoch
    sizing.
    """

    def __init__(
        self,
        n_colors: int = 22,
        mask_min: int = 8,
        mask_max: int = 64,
        samples_per_epoch: int = 1000,
        seed: int = 0,
    ):
        self.n_colors = n_colors
        self.mask_min = mask_min
        self.mask_max = mask_max
        self.samples_per_epoch = samples_per_epoch
        self.seed = seed

    def __len__(self):
        return self.samples_per_epoch

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        worker_id = worker_info.id if worker_info else 0
        # Each worker uses a different seed stream.
        rng = random.Random(self.seed * 1_000_000 + worker_id * 1_000 + 0)
        for _ in range(self.samples_per_epoch):
            yield self._gen_one(rng)

    def _gen_one(self, rng):
        pieces, canonical = generate_synthetic_board(self.n_colors, rng)
        n_mask = rng.randint(self.mask_min, min(self.mask_max, N_CELLS - 1))
        masked_positions = rng.sample(range(N_CELLS), n_mask)
        masked_set = set(masked_positions)

        pieces_t = torch.zeros(N_CELLS, dtype=torch.long)
        rotations_t = torch.zeros(N_CELLS, dtype=torch.long)
        targets_piece = torch.full((N_CELLS,), -100, dtype=torch.long)
        targets_rot = torch.full((N_CELLS,), -100, dtype=torch.long)

        for pos in range(N_CELLS):
            true_piece, true_rot = canonical[pos]
            if pos in masked_set:
                pieces_t[pos] = EMPTY_PIECE
                rotations_t[pos] = EMPTY_ROTATION
                targets_piece[pos] = true_piece
                targets_rot[pos] = true_rot
            else:
                pieces_t[pos] = true_piece
                rotations_t[pos] = true_rot

        return {
            "pieces": pieces_t,
            "rotations": rotations_t,
            "targets_piece": targets_piece,
            "targets_rot": targets_rot,
            "weight": torch.tensor(1.0, dtype=torch.float32),
            "score": torch.tensor(480, dtype=torch.long),  # synthetic always perfect
        }
