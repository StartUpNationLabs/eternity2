"""Board-completion transformer for canonical Eternity II.

Given a partial board (some cells empty), predict (piece_id, rotation) at
each empty cell. Trained on database-400-480 by masked-cell prediction.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


N_PIECES = 256        # canonical E2
N_ROTATIONS = 4
N_CELLS = 256         # 16x16
EMPTY_PIECE = N_PIECES  # sentinel = 256
EMPTY_ROTATION = N_ROTATIONS  # sentinel = 4


class BoardEmbedding(nn.Module):
    """Embed each of 256 cells as (piece_id, rotation, position).

    - piece_id ∈ {0..255, EMPTY=256} → piece_emb_dim
    - rotation ∈ {0..3, NONE=4} → rot_emb_dim
    - position ∈ {0..255} → pos_emb_dim
    Total per cell = piece_emb_dim + rot_emb_dim + pos_emb_dim.
    """

    def __init__(self, piece_emb_dim: int = 64, rot_emb_dim: int = 16, pos_emb_dim: int = 32):
        super().__init__()
        self.piece_emb = nn.Embedding(N_PIECES + 1, piece_emb_dim)
        self.rot_emb = nn.Embedding(N_ROTATIONS + 1, rot_emb_dim)
        self.pos_emb = nn.Embedding(N_CELLS, pos_emb_dim)
        self.hidden_dim = piece_emb_dim + rot_emb_dim + pos_emb_dim

    def forward(self, pieces: torch.Tensor, rotations: torch.Tensor) -> torch.Tensor:
        """
        Args:
            pieces: [B, 256] long, with values 0..256 (256=empty)
            rotations: [B, 256] long, with values 0..4 (4=empty)
        Returns:
            [B, 256, hidden_dim] cell embeddings
        """
        B = pieces.shape[0]
        positions = torch.arange(N_CELLS, device=pieces.device).unsqueeze(0).expand(B, -1)
        p_emb = self.piece_emb(pieces)
        r_emb = self.rot_emb(rotations)
        pos = self.pos_emb(positions)
        return torch.cat([p_emb, r_emb, pos], dim=-1)


class BoardTransformer(nn.Module):
    """4-layer transformer encoder + per-cell (piece × rotation) head.

    For each cell in the output, predict (piece, rotation) jointly via a
    1024-class logit (N_PIECES × N_ROTATIONS = 1024).
    """

    def __init__(self, n_layers: int = 4, n_heads: int = 4, hidden_dim: int = 128, dropout: float = 0.1):
        super().__init__()
        self.embed = BoardEmbedding()
        self.input_proj = nn.Linear(self.embed.hidden_dim, hidden_dim)
        layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=n_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, N_PIECES * N_ROTATIONS),
        )

    def forward(self, pieces: torch.Tensor, rotations: torch.Tensor) -> torch.Tensor:
        """
        Args:
            pieces: [B, 256]
            rotations: [B, 256]
        Returns:
            [B, 256, N_PIECES * N_ROTATIONS] logits
        """
        cell_emb = self.embed(pieces, rotations)
        x = self.input_proj(cell_emb)
        x = self.transformer(x)
        return self.head(x)
