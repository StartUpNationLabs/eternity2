"""Inference for the v2 edge-based transformer.

Two modes:
1. Single-shot: predict all masked cells' edges given a partial board.
2. Iterative: predict highest-confidence cells first, fill them, repeat.

Output: predicted edge colors. Downstream code maps these to actual
canonical E2 pieces via Hungarian assignment.
"""

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from model_v2 import EdgeBoardTransformer, N_CELLS, N_COLORS, EMPTY_COLOR
from data_edges import board_from_canonical_csv


REPO = Path(__file__).resolve().parents[2]
W = 16


def load_model(checkpoint_path: str, device: torch.device):
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    args = ckpt["args"]
    model = EdgeBoardTransformer(
        n_layers=args["layers"],
        n_heads=args["heads"],
        hidden_dim=args["hidden"],
    ).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model, args


def board_to_tensor(placements: dict, pieces: list) -> torch.Tensor:
    """Convert {pos: (piece_id, rotation)} → [256, 4] edge tensor.

    pieces: list of 256 piece tuples (N, E, S, W) by piece_id.
    """
    edges = torch.full((N_CELLS, 4), EMPTY_COLOR, dtype=torch.long)
    for pos, (pid, rot) in placements.items():
        N, E, S, Wc = pieces[pid]
        # Apply rotation
        if rot == 0: e = (N, E, S, Wc)
        elif rot == 1: e = (Wc, N, E, S)
        elif rot == 2: e = (S, Wc, N, E)
        elif rot == 3: e = (E, S, Wc, N)
        else: raise ValueError(rot)
        for i, c in enumerate(e):
            edges[pos, i] = c
    return edges


def predict(model, edges: torch.Tensor, device: torch.device) -> torch.Tensor:
    """Single-shot prediction. Returns logits [256, 4, N_COLORS]."""
    with torch.no_grad():
        x = edges.unsqueeze(0).to(device)  # [1, 256, 4]
        logits = model(x)
        return logits.squeeze(0).cpu()


def iterative_fill(model, edges: torch.Tensor, mask_set: set, device: torch.device,
                   confidence_threshold: float = 0.5) -> tuple[torch.Tensor, dict]:
    """Iteratively fill masked cells. At each step, predict all masked, pick
    the highest-confidence cell, fill its edges, repeat.

    Returns:
        filled_edges: [256, 4] with predicted edges at masked cells
        confidences: dict {pos: average confidence across the 4 edges}
    """
    current = edges.clone()
    remaining = set(mask_set)
    confidences = {}

    while remaining:
        logits = predict(model, current, device)  # [256, 4, N_COLORS]
        # Compute confidence per cell: max prob averaged over 4 edges.
        probs = F.softmax(logits, dim=-1)  # [256, 4, N_COLORS]
        max_probs = probs.max(dim=-1).values  # [256, 4]
        cell_confidence = max_probs.mean(dim=-1)  # [256]

        # Among remaining cells, pick highest confidence.
        best_pos = max(remaining, key=lambda p: cell_confidence[p].item())
        # Get predicted edges for that cell.
        preds = probs[best_pos].argmax(dim=-1)  # [4]
        current[best_pos] = preds
        confidences[best_pos] = cell_confidence[best_pos].item()
        remaining.discard(best_pos)

    return current, confidences


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=str, required=True)
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data" / "puzzles" / "size_16_official_eternity.csv"))
    ap.add_argument("--board", type=str,
                    help="JSON file with partial placement to complete (optional)")
    ap.add_argument("--mask-frac", type=float, default=0.25,
                    help="If no --board: mask this fraction of canonical board")
    ap.add_argument("--iterative", action="store_true")
    args = ap.parse_args()

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}", flush=True)
    model, train_args = load_model(args.checkpoint, device)
    print(f"Model: {train_args}", flush=True)

    # Load pieces from canonical CSV (or use synthetic).
    canonical_pieces = board_from_canonical_csv(args.puzzle)
    print(f"Loaded {len(canonical_pieces)} canonical pieces", flush=True)

    # Build a "perfect" canonical board as ground truth: piece i at position i, rotation 0.
    # This is the FULLY-ASSEMBLED canonical layout (since CSV is in canonical order).
    # NOTE: this is the GENERATOR's canonical solution; real canonical E2 has shuffled
    # piece order. For testing the model, we use the generator order.
    placements_full = {pos: (pos, 0) for pos in range(N_CELLS)}
    edges_full = board_to_tensor(placements_full, canonical_pieces)

    # Mask random cells.
    import random
    rng = random.Random(0)
    n_mask = int(N_CELLS * args.mask_frac)
    mask_positions = set(rng.sample(range(N_CELLS), n_mask))
    edges_masked = edges_full.clone()
    for pos in mask_positions:
        edges_masked[pos] = EMPTY_COLOR

    print(f"Masking {n_mask} cells, predicting...", flush=True)

    if args.iterative:
        filled, confidences = iterative_fill(model, edges_masked, mask_positions, device)
    else:
        logits = predict(model, edges_masked, device)
        preds = logits.argmax(dim=-1)
        filled = edges_masked.clone()
        for pos in mask_positions:
            filled[pos] = preds[pos]
        confidences = {}

    # Evaluate: count edges matched correctly.
    correct = 0
    total = 0
    for pos in mask_positions:
        for e in range(4):
            total += 1
            if filled[pos, e].item() == edges_full[pos, e].item():
                correct += 1
    print(f"Accuracy at masked cells: {correct}/{total} = {correct/max(total,1)*100:.1f}%", flush=True)

    # Adjacency-consistency: how often does the predicted edge MATCH its real neighbor?
    consistent = 0
    total_adj = 0
    for pos in mask_positions:
        r, c = pos // W, pos % W
        # E edge ↔ neighbor's W edge
        if c < 15:
            total_adj += 1
            if filled[pos, 1].item() == edges_full[pos + 1, 3].item():
                consistent += 1
        # S edge ↔ neighbor's N edge
        if r < 15:
            total_adj += 1
            if filled[pos, 2].item() == edges_full[pos + W, 0].item():
                consistent += 1
    print(f"Adjacency consistency: {consistent}/{total_adj} = {consistent/max(total_adj,1)*100:.1f}%", flush=True)


if __name__ == "__main__":
    main()
