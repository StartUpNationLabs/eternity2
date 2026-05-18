"""End-to-end pipeline: trained transformer → canonical-E2 placement → ALNS.

Workflow:
1. Load trained transformer checkpoint.
2. Either:
   (a) Start from canonical EMPTY board + 5 hint cells → predict all 256
       edge tuples → LAP-assign canonical pieces → score, save board.
   (b) Start from a 459/460/461 partial → mask N cells → predict edges
       → LAP-assign → score, save board.
3. Save output JSON in canonical placement format.
4. Optionally feed to alns_only as `--cp-board` for further polishing.

This is the FULL pipeline that lets us use the neural net as a starting
point for ALNS.
"""

import argparse
import json
import random
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from model_v2 import EdgeBoardTransformer, N_CELLS, N_COLORS, EMPTY_COLOR
from data_edges import board_from_canonical_csv
from edges_to_placement import edges_to_placement, score_placement, rotate


REPO = Path(__file__).resolve().parents[2]
W = 16

# Canonical 5-hint puzzle constants.
CANONICAL_HINTS = {
    34: (207, 1),
    45: (254, 1),
    135: (138, 0),
    210: (180, 1),
    221: (248, 2),
}


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
    """Convert {pos: (piece_id, rot)} → [256, 4] edge array."""
    edges = np.full((N_CELLS, 4), EMPTY_COLOR, dtype=np.int64)
    for pos, (pid, rot) in placement.items():
        e = rotate(canonical_pieces[pid], rot)
        edges[pos] = e
    return edges


def predict_edges(model, edges_in: np.ndarray, device: torch.device) -> np.ndarray:
    """Single-shot edge prediction. edges_in: [256, 4]. Returns [256, 4]."""
    with torch.no_grad():
        x = torch.from_numpy(edges_in).long().unsqueeze(0).to(device)
        logits = model(x)
        preds = logits.argmax(dim=-1)
        return preds.squeeze(0).cpu().numpy()


def predict_iterative(model, edges_in: np.ndarray, target_cells: set,
                       device: torch.device) -> np.ndarray:
    """Iterative-fill prediction. At each step, find highest-confidence target
    cell, fill it, repeat until all targets filled."""
    current = edges_in.copy()
    remaining = set(target_cells)

    while remaining:
        with torch.no_grad():
            x = torch.from_numpy(current).long().unsqueeze(0).to(device)
            logits = model(x)
            probs = F.softmax(logits, dim=-1).squeeze(0).cpu().numpy()  # [256, 4, N_COLORS]
        # Confidence per cell = mean of max-prob across 4 edges.
        max_probs = probs.max(axis=-1)  # [256, 4]
        cell_confidence = max_probs.mean(axis=-1)  # [256]
        # Pick highest-confidence remaining cell.
        best_pos = max(remaining, key=lambda p: cell_confidence[p])
        # Fill it.
        preds = probs[best_pos].argmax(axis=-1)
        current[best_pos] = preds
        remaining.discard(best_pos)
    return current


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=str, required=True)
    ap.add_argument("--puzzle", type=str,
                    default=str(REPO.parent / "data" / "puzzles" / "size_16_official_eternity.csv"))
    ap.add_argument("--input-board", type=str,
                    help="JSON board to warm-start from (default: hint-only)")
    ap.add_argument("--mask-frac", type=float, default=1.0,
                    help="If --input-board is full: mask this fraction first")
    ap.add_argument("--iterative", action="store_true")
    ap.add_argument("--out", type=str, default=None,
                    help="Output JSON path (default: print only)")
    ap.add_argument("--strict-hints", action="store_true",
                    help="Force canonical hints during LAP assignment")
    args = ap.parse_args()

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}", flush=True)

    model, train_args = load_model(args.checkpoint, device)
    print(f"Model: {train_args}", flush=True)

    canonical_pieces = board_from_canonical_csv(args.puzzle)
    print(f"Loaded {len(canonical_pieces)} canonical pieces", flush=True)

    # Build initial placement.
    if args.input_board:
        with open(args.input_board) as f:
            d = json.load(f)
        initial_placement = {}
        for i, p in enumerate(d.get("placement", [])):
            if not isinstance(p, dict): continue
            pos = p.get("pos", i)
            if "piece_id" in p and "rotation" in p:
                initial_placement[int(pos)] = (int(p["piece_id"]), int(p["rotation"]))
        # Optionally mask some cells.
        if args.mask_frac < 1.0:
            random.seed(0)
            n_mask = int(N_CELLS * args.mask_frac)
            mask_positions = random.sample(list(initial_placement.keys()), n_mask)
            for pos in mask_positions:
                del initial_placement[pos]
        target_cells = set(range(N_CELLS)) - set(initial_placement.keys())
    else:
        # Hint-only warm start.
        initial_placement = dict(CANONICAL_HINTS)
        target_cells = set(range(N_CELLS)) - set(CANONICAL_HINTS.keys())

    print(f"Initial placed cells: {len(initial_placement)}, target cells: {len(target_cells)}",
          flush=True)

    # Encode partial board.
    edges_in = edges_from_placement(initial_placement, canonical_pieces)

    # Predict.
    print(f"Predicting ({'iterative' if args.iterative else 'single-shot'})...", flush=True)
    if args.iterative:
        predicted_edges = predict_iterative(model, edges_in, target_cells, device)
    else:
        predicted_edges = predict_edges(model, edges_in, device)
        # Keep input edges fixed at non-target cells.
        for pos in range(N_CELLS):
            if pos not in target_cells:
                predicted_edges[pos] = edges_in[pos]

    # Convert predicted edges to canonical placement via LAP.
    print(f"Solving LAP (256-cell assignment)...", flush=True)
    fix_hints = CANONICAL_HINTS if args.strict_hints else None
    placement = edges_to_placement(predicted_edges, canonical_pieces, fix_hints=fix_hints)

    # Score.
    score = score_placement(placement, canonical_pieces)
    n_pieces_unique = len(set(p for p, _ in placement.values()))
    print(f"  matched edges: {score}/480", flush=True)
    print(f"  piece uniqueness: {n_pieces_unique}/256", flush=True)

    # Check hint compliance.
    n_hints_obeyed = 0
    for pos, (exp_pid, exp_rot) in CANONICAL_HINTS.items():
        if placement.get(pos) == (exp_pid, exp_rot):
            n_hints_obeyed += 1
    print(f"  hints obeyed: {n_hints_obeyed}/5", flush=True)

    # Save.
    if args.out:
        out_data = {
            "matched": score,
            "source": "transformer_v2",
            "placement": [
                {"pos": pos, "piece_id": pid, "rotation": rot}
                for pos, (pid, rot) in sorted(placement.items())
            ],
            "hints_obeyed": f"{n_hints_obeyed}/5",
            "strict_hints_applied": args.strict_hints,
            "iterative": args.iterative,
        }
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(out_data, f, indent=2)
        print(f"  saved to {args.out}", flush=True)


if __name__ == "__main__":
    main()
