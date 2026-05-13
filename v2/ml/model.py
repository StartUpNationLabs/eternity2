"""Small imitation model for vol-26 learned value-order gate.

Architecture: per-cell 13-D features → 2 graph-conv layers over the 6×6
grid → mean-pool a 5-cell L-stencil (target + 4 neighbours) → MLP → logits
over the full (piece_id × rotation) action space.

Not a fancy GNN — explicit message-passing on the grid is enough at this
size. The plan calls for ~200k params; this hits that on the nose with
hidden=64, two conv layers, and an action-head over n_pieces*4 = 144 (at
6×6/5c).
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


def neighbour_indices(size: int) -> torch.Tensor:
    """Return a (n_cells, 4) tensor of neighbour indices. -1 = no neighbour
    (off-board). Order: top, right, bottom, left — matches engine
    convention."""
    n = size * size
    out = torch.full((n, 4), -1, dtype=torch.long)
    for y in range(size):
        for x in range(size):
            pos = y * size + x
            if y > 0:
                out[pos, 0] = (y - 1) * size + x
            if x < size - 1:
                out[pos, 1] = y * size + (x + 1)
            if y < size - 1:
                out[pos, 2] = (y + 1) * size + x
            if x > 0:
                out[pos, 3] = y * size + (x - 1)
    return out


class GridConv(nn.Module):
    """One round of message-passing on the 4-neighbour grid.

    For each cell, gather features from up to 4 neighbours (padding with
    zeros where the neighbour is off-board), concatenate with self
    features, project to `out_dim`.
    """

    def __init__(self, in_dim: int, out_dim: int, size: int):
        super().__init__()
        self.size = size
        self.proj = nn.Linear(in_dim * 5, out_dim)
        # Pre-bake the off-board mask + the "clamped" neighbour indices so
        # we do NOT do any int->int .where() at runtime — MPS has known
        # issues with composed int64 .where() that produce garbage indices
        # in async kernels. Store two clean tensors.
        nb = neighbour_indices(size)               # (N, 4), -1 marks off-board
        valid_mask = (nb >= 0).to(torch.float32)   # (N, 4) — 1.0 where valid, 0.0 off-board
        nb_clamped = nb.clamp(min=0)               # (N, 4) — safe indices (off-board -> 0)
        self.register_buffer("nb_clamped", nb_clamped)
        self.register_buffer("valid_mask", valid_mask)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, n_cells, in_dim)
        B, N, D = x.shape
        idx = self.nb_clamped              # (N, 4)
        # Flat (B, N*4) index into the cell dim of x (always 0..N-1, safe).
        flat = idx.reshape(-1).unsqueeze(0).expand(B, -1)
        flat_idx = flat.unsqueeze(-1).expand(-1, -1, D)
        gathered = torch.gather(x, dim=1, index=flat_idx)  # (B, N*4, D)
        nb_feats = gathered.view(B, N, 4, D)
        # Zero out the off-board slots (would otherwise carry data from
        # cell 0). Multiplying by the float mask is differentiable + cheap.
        nb_feats = nb_feats * self.valid_mask.unsqueeze(0).unsqueeze(-1)
        cat = torch.cat([x.unsqueeze(2), nb_feats], dim=2).flatten(2)  # (B, N, 5*D)
        return F.relu(self.proj(cat))


class PlacementModel(nn.Module):
    """Predict (piece_id, rotation) at a given target_position.

    Forward: feats (B, N, 13), target_pos (B,) -> logits (B, n_actions).
    """

    def __init__(self, size: int, n_pieces: int, hidden: int = 64):
        super().__init__()
        self.size = size
        self.n_pieces = n_pieces
        self.n_actions = n_pieces * 4
        feat_dim = 13
        self.conv1 = GridConv(feat_dim, hidden, size)
        self.conv2 = GridConv(hidden, hidden, size)
        self.head = nn.Sequential(
            nn.Linear(hidden + feat_dim, hidden * 2),
            nn.ReLU(),
            nn.Linear(hidden * 2, self.n_actions),
        )

    def forward(self, feats: torch.Tensor, target_pos: torch.Tensor) -> torch.Tensor:
        h = self.conv1(feats)
        h = self.conv2(h)
        # Pick the target cell's hidden vector + raw features at that cell.
        # Use torch.gather to dodge an MPS issue with multi-tensor fancy
        # indexing producing OOB cell-dim indices.
        B = feats.size(0)
        # target_pos: (B,) -> (B, 1, D_h) for gather along dim=1.
        D_h = h.size(-1)
        D_x = feats.size(-1)
        idx_h = target_pos.view(B, 1, 1).expand(-1, 1, D_h)
        idx_x = target_pos.view(B, 1, 1).expand(-1, 1, D_x)
        target_h = torch.gather(h, dim=1, index=idx_h).squeeze(1)         # (B, D_h)
        target_x = torch.gather(feats, dim=1, index=idx_x).squeeze(1)     # (B, D_x)
        return self.head(torch.cat([target_h, target_x], dim=1))


def param_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    m = PlacementModel(size=6, n_pieces=36, hidden=64)
    print(f"params: {param_count(m):,}")
    feats = torch.randn(8, 36, 13)
    tp = torch.zeros(8, dtype=torch.long)
    out = m(feats, tp)
    print(f"forward out shape: {tuple(out.shape)}  (expected (8, 144))")
