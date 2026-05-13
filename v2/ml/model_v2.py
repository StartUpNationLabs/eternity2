"""Vol-28 — position-relative learned scorer.

Key differences from `model.py` (vol-26/27):
- **Size-agnostic.** Neighbour indices are passed as a runtime tensor
  argument, not a registered buffer. The model works on any (W, H).
- **Piece-count-agnostic.** No piece-id one-hot anywhere. The model
  scores a *candidate placement* given its 4 placed edges and the
  surrounding target-cell context. So the same model trained at 6x6/5c
  can in principle run at 16x16/22c.
- **Per-candidate scoring head.** Forward emits one scalar per
  candidate, not logits over a fixed action space.

Architecture sketch:
  1. Encode each cell's 13-D feature with a Linear -> hidden.
  2. Two rounds of grid GNN message-passing (uses runtime nb_idx tensor).
  3. Pool the target cell's hidden + the surrounding cells' edges.
  4. For each candidate: concatenate its 4 edges (one-hot to a small
     embedding to be color-count-agnostic) + the target-cell context,
     pass through MLP -> scalar score.

Color encoding: we map raw color id to a fixed-size embedding (24-dim).
This caps the supported color count at 24 — fine for canonical E2 (22
colors + BORDER) and our synthetic 6x6/5c (5 colors + BORDER).
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


# Vol-28 — max distinct edge colors the model knows. 24 covers BORDER (0)
# + canonical E2's 22 interior colors + 1 spare. Color indices >= this
# value get mapped to 0 (BORDER), which is safe but a silent regression
# on out-of-vocabulary inputs.
MAX_COLOR = 24

CELL_RAW_FEAT_DIM = 13


def build_neighbour_indices(width: int, height: int) -> torch.Tensor:
    """Return (n_cells, 4) of neighbour cell-indices [top, right, bot, left].
    Off-board slots are set to n_cells (a safe pad row index)."""
    n = width * height
    out = torch.full((n, 4), n, dtype=torch.long)
    for y in range(height):
        for x in range(width):
            pos = y * width + x
            if y > 0:
                out[pos, 0] = (y - 1) * width + x
            if x < width - 1:
                out[pos, 1] = y * width + (x + 1)
            if y < height - 1:
                out[pos, 2] = (y + 1) * width + x
            if x > 0:
                out[pos, 3] = y * width + (x - 1)
    return out


def build_valid_mask(width: int, height: int) -> torch.Tensor:
    """Return (n_cells, 4) float, 1.0 where neighbour is on-board, 0.0 off."""
    n = width * height
    out = torch.zeros((n, 4), dtype=torch.float32)
    for y in range(height):
        for x in range(width):
            pos = y * width + x
            if y > 0:
                out[pos, 0] = 1.0
            if x < width - 1:
                out[pos, 1] = 1.0
            if y < height - 1:
                out[pos, 2] = 1.0
            if x > 0:
                out[pos, 3] = 1.0
    return out


def encode_cell_features(raw: torch.Tensor, color_embed: nn.Embedding) -> torch.Tensor:
    """Map (B, N, 13) raw cell features -> (B, N, 4*D_emb + 9)."""
    B, N, _ = raw.shape
    color_ids = raw[..., :4].long().clamp(min=0, max=MAX_COLOR - 1)
    colors = color_embed(color_ids).reshape(B, N, -1)
    flags = raw[..., 4:].float()
    return torch.cat([colors, flags], dim=-1)


class GridConvDynamic(nn.Module):
    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        self.proj = nn.Linear(in_dim * 5, out_dim)

    def forward(self, x, nb_idx, valid_mask):
        B, N, D = x.shape
        zero_row = x.new_zeros(B, 1, D)
        padded = torch.cat([x, zero_row], dim=1)
        flat = nb_idx.reshape(-1).unsqueeze(0).expand(B, -1)
        flat_idx = flat.unsqueeze(-1).expand(-1, -1, D)
        gathered = torch.gather(padded, dim=1, index=flat_idx)
        nb_feats = gathered.view(B, N, 4, D)
        nb_feats = nb_feats * valid_mask.unsqueeze(0).unsqueeze(-1)
        cat = torch.cat([x.unsqueeze(2), nb_feats], dim=2).flatten(2)
        return F.relu(self.proj(cat))


class PositionRelativeModel(nn.Module):
    def __init__(self, hidden: int = 64, color_emb: int = 16):
        super().__init__()
        self.hidden = hidden
        self.color_emb_dim = color_emb
        self.color_embed = nn.Embedding(MAX_COLOR, color_emb)
        cell_in = 4 * color_emb + 9
        self.cell_proj = nn.Linear(cell_in, hidden)
        self.conv1 = GridConvDynamic(hidden, hidden)
        self.conv2 = GridConvDynamic(hidden, hidden)
        cand_in = 4 * color_emb + hidden
        self.score_head = nn.Sequential(
            nn.Linear(cand_in, hidden * 2),
            nn.ReLU(),
            nn.Linear(hidden * 2, 1),
        )

    def encode_board(self, cell_feats, nb_idx, valid_mask):
        x = encode_cell_features(cell_feats, self.color_embed)
        x = F.relu(self.cell_proj(x))
        x = self.conv1(x, nb_idx, valid_mask)
        x = self.conv2(x, nb_idx, valid_mask)
        return x

    def forward(self, cell_feats, nb_idx, valid_mask, target_pos, cand_edges):
        B, C, _ = cand_edges.shape
        board_h = self.encode_board(cell_feats, nb_idx, valid_mask)
        D = board_h.size(-1)
        idx = target_pos.view(B, 1, 1).expand(-1, 1, D)
        target_h = torch.gather(board_h, dim=1, index=idx).squeeze(1)
        cand_ids = cand_edges.long().clamp(min=0, max=MAX_COLOR - 1)
        cand_e = self.color_embed(cand_ids).reshape(B, C, -1)
        target_h_b = target_h.unsqueeze(1).expand(-1, C, -1)
        cand_in = torch.cat([cand_e, target_h_b], dim=-1)
        scores = self.score_head(cand_in).squeeze(-1)
        return scores


def param_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    m = PositionRelativeModel(hidden=64, color_emb=16)
    print(f"params: {param_count(m):,}")
    for W in (6, 16):
        N = W * W
        nb = build_neighbour_indices(W, W)
        vm = build_valid_mask(W, W)
        feats = torch.randn(2, N, 13)
        feats[..., 0:4] = feats[..., 0:4].abs().clamp(0, MAX_COLOR - 1)
        tp = torch.zeros(2, dtype=torch.long)
        cand = torch.zeros(2, 8, 4, dtype=torch.long)
        out = m(feats, nb, vm, tp, cand)
        print(f"{W}x{W} out: {tuple(out.shape)} (expected (2, 8))")
