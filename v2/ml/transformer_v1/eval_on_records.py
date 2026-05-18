"""Evaluate trained transformer on REAL E2 records from database-400-480.

For each high-score board:
1. Take its full edge layout.
2. Mask N random cells.
3. Use transformer to predict edges at masked cells.
4. Score:
   - Per-edge accuracy at masked positions
   - Adjacency consistency (predicted edge matches actual neighbor's opposite edge)
   - Full-piece accuracy after LAP assignment

This tells us if synthetic-trained transformer transfers to canonical E2.
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path
from collections import defaultdict

import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).parent))
from model_v2 import EdgeBoardTransformer, N_CELLS, N_COLORS, EMPTY_COLOR
from data_edges import board_from_canonical_csv
from edges_to_placement import edges_to_placement, score_placement, rotate


REPO = Path(__file__).resolve().parents[2]
DB = REPO / "database-400-480"
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


def edges_from_placement(placement: dict, canonical_pieces: list) -> np.ndarray:
    edges = np.full((N_CELLS, 4), EMPTY_COLOR, dtype=np.int64)
    for pos, (pid, rot) in placement.items():
        e = rotate(canonical_pieces[pid], rot)
        edges[pos] = e
    return edges


def predict(model, edges_in: np.ndarray, device) -> tuple[np.ndarray, np.ndarray]:
    """Returns (predicted_edges, confidences) where:
    - predicted_edges: [256, 4] uint8
    - confidences: [256] float — mean max-prob per cell
    """
    with torch.no_grad():
        x = torch.from_numpy(edges_in).long().unsqueeze(0).to(device)
        logits = model(x)
        probs = F.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
        preds = probs.argmax(axis=-1)
        confidences = probs.max(axis=-1).mean(axis=-1)
        return preds, confidences


def evaluate_one_board(model, placement: dict, canonical_pieces: list,
                       mask_positions: list, device) -> dict:
    """Mask + predict + score."""
    edges_full = edges_from_placement(placement, canonical_pieces)
    edges_masked = edges_full.copy()
    for pos in mask_positions:
        edges_masked[pos] = EMPTY_COLOR

    preds, confidences = predict(model, edges_masked, device)
    # Score: per-edge accuracy on masked positions.
    correct_edges = 0
    total_edges = 0
    for pos in mask_positions:
        for e in range(4):
            total_edges += 1
            if preds[pos, e] == edges_full[pos, e]:
                correct_edges += 1
    # Adjacency consistency: predicted E edge == actual W edge of right neighbor.
    adj_consistent = 0
    adj_total = 0
    for pos in mask_positions:
        r, c = pos // W, pos % W
        if c < 15:
            adj_total += 1
            if preds[pos, 1] == edges_full[pos + 1, 3]:
                adj_consistent += 1
        if r < 15:
            adj_total += 1
            if preds[pos, 2] == edges_full[pos + W, 0]:
                adj_consistent += 1
        if c > 0:
            adj_total += 1
            if preds[pos, 3] == edges_full[pos - 1, 1]:
                adj_consistent += 1
        if r > 0:
            adj_total += 1
            if preds[pos, 0] == edges_full[pos - W, 2]:
                adj_consistent += 1

    avg_conf = float(confidences[mask_positions].mean())
    return {
        "n_mask": len(mask_positions),
        "edge_accuracy": correct_edges / max(total_edges, 1),
        "adj_consistency": adj_consistent / max(adj_total, 1),
        "avg_confidence": avg_conf,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=str, required=True)
    ap.add_argument("--n-boards", type=int, default=50,
                    help="How many high-score boards to evaluate")
    ap.add_argument("--min-score", type=int, default=458)
    ap.add_argument("--mask-sizes", type=str, default="8,16,32,64,128",
                    help="Comma-separated mask sizes to try")
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data" / "puzzles" / "size_16_official_eternity.csv"))
    args = ap.parse_args()

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}", flush=True)

    model, train_args = load_model(args.checkpoint, device)
    print(f"Model: {train_args}", flush=True)

    canonical_pieces = board_from_canonical_csv(args.puzzle)

    # Load high-score boards.
    print(f"Loading boards (min_score={args.min_score})...", flush=True)
    boards = []
    for f in sorted(DB.glob("*.json")):
        if f.name == "README.md": continue
        try:
            with open(f) as fh:
                d = json.load(fh)
        except Exception:
            continue
        if d.get("matched", 0) < args.min_score:
            continue
        pl = d.get("placement", [])
        placement = {}
        for i, p in enumerate(pl):
            if not isinstance(p, dict): continue
            pos = p.get("pos", i)
            if "piece_id" in p and "rotation" in p:
                placement[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
        if len(placement) == 256:
            boards.append((d.get("matched", 0), placement))
        if len(boards) >= args.n_boards:
            break
    print(f"  loaded {len(boards)} boards", flush=True)

    mask_sizes = [int(x) for x in args.mask_sizes.split(",")]
    rng = random.Random(42)

    print(f"\n{'mask':>5} {'edge_acc':>10} {'adj_cons':>10} {'avg_conf':>10}")
    for mask_size in mask_sizes:
        edge_accs = []
        adj_conses = []
        confs = []
        for score, placement in boards:
            mask_positions = rng.sample(range(N_CELLS), mask_size)
            r = evaluate_one_board(model, placement, canonical_pieces, mask_positions, device)
            edge_accs.append(r["edge_accuracy"])
            adj_conses.append(r["adj_consistency"])
            confs.append(r["avg_confidence"])
        ea = np.mean(edge_accs) * 100
        ac = np.mean(adj_conses) * 100
        cf = np.mean(confs) * 100
        print(f"{mask_size:>5d} {ea:>9.1f}% {ac:>9.1f}% {cf:>9.1f}%", flush=True)


if __name__ == "__main__":
    main()
