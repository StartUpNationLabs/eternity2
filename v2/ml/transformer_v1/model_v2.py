"""V2 board-completion transformer that uses PIECE EDGES as input, not piece IDs.

This is the right architecture for transferring synthetic E2-family training
to canonical E2 inference. Piece IDs are arbitrary labels; the actual
constraint structure is in the EDGE COLORS.

Architecture:
- Input per cell: 4 placed edges (N, E, S, W) — each is a color (0..C) or
  EMPTY (sentinel for unfilled cells).
- Embed: each color → color_emb_dim. Each cell = 4 color embs concatenated.
- Position embedding (256 positions).
- Transformer encoder.
- Output: predict the 4 EDGES of the cell (4 × C+1 logits).

Once we have predicted edges, downstream code finds the piece with the
closest edge tuple (Hungarian assignment).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


N_CELLS = 256
W = 16
N_COLORS = 23  # 0=border + 1..22 interior colors
EMPTY_COLOR = N_COLORS  # = 23, sentinel for "unfilled edge"


class EdgeBoardEmbedding(nn.Module):
    """Embed each cell from its 4 edge colors."""

    def __init__(self, color_emb_dim: int = 24, pos_emb_dim: int = 32):
        super().__init__()
        # +1 for EMPTY_COLOR sentinel
        self.color_emb = nn.Embedding(N_COLORS + 1, color_emb_dim)
        self.pos_emb = nn.Embedding(N_CELLS, pos_emb_dim)
        self.hidden_dim = 4 * color_emb_dim + pos_emb_dim

    def forward(self, edges: torch.Tensor) -> torch.Tensor:
        """
        Args:
            edges: [B, 256, 4] long, with values 0..N_COLORS (N_COLORS = EMPTY)
        Returns:
            [B, 256, hidden_dim]
        """
        B = edges.shape[0]
        positions = torch.arange(N_CELLS, device=edges.device).unsqueeze(0).expand(B, -1)
        # Embed each of the 4 edges per cell, then concat.
        # edges shape: [B, 256, 4] → [B, 256, 4, color_emb_dim]
        edge_emb = self.color_emb(edges)
        edge_emb_flat = edge_emb.reshape(B, N_CELLS, -1)  # [B, 256, 4*color_emb_dim]
        pos = self.pos_emb(positions)  # [B, 256, pos_emb_dim]
        return torch.cat([edge_emb_flat, pos], dim=-1)


class EdgeBoardTransformer(nn.Module):
    """Predict the 4 edge colors at each cell.

    Output: [B, 256, 4, N_COLORS] logits — for each cell, 4 edges, each a
    distribution over colors.
    """

    def __init__(self, n_layers: int = 4, n_heads: int = 4, hidden_dim: int = 128,
                 color_emb_dim: int = 24, pos_emb_dim: int = 32, dropout: float = 0.1):
        super().__init__()
        self.embed = EdgeBoardEmbedding(color_emb_dim=color_emb_dim, pos_emb_dim=pos_emb_dim)
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
        # 4 separate edge heads to predict (N, E, S, W) colors per cell.
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 4 * N_COLORS),
        )

    def forward(self, edges: torch.Tensor) -> torch.Tensor:
        """
        Args:
            edges: [B, 256, 4] cell edges with EMPTY=N_COLORS for empty cells
        Returns:
            [B, 256, 4, N_COLORS] logits over color per (cell, edge)
        """
        cell_emb = self.embed(edges)
        x = self.input_proj(cell_emb)
        x = self.transformer(x)
        logits = self.head(x)
        B = edges.shape[0]
        return logits.view(B, N_CELLS, 4, N_COLORS)
