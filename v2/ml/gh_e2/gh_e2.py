#!/usr/bin/env python3
"""
GH-E2: Gradient + Hungarian projection for Eternity II.

Relax each cell's piece+rotation assignment to a categorical distribution.
Gradient-ascend on the EXPECTED matched-edge score with soft uniqueness
penalty. Final projection via Hungarian.

NEW algorithm class — vol-13 OT (R3) repaired existing boards via Kuhn-Munkres
on distances; this relaxes the ENTIRE assignment to continuous and gradient-
walks the relaxed score landscape, then projects.

Usage:
    python gh_e2.py --start CANONICAL_BOARD.json --steps 1000 --out OUT.json
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from scipy.optimize import linear_sum_assignment

# ============================================================================
# Constants
# ============================================================================

N = 16  # board side
N_POS = N * N  # 256
N_PIECES = 256
N_ROT = 4
N_VARIANTS = N_PIECES * N_ROT  # 1024 (piece, rot) combinations
N_COLORS = 23  # 0=border + 1..22
BORDER = 0

CANONICAL_HINTS = {
    34: (207, 1),
    45: (254, 1),
    135: (138, 0),
    210: (180, 1),
    221: (248, 2),
}

# ============================================================================
# Puzzle loading
# ============================================================================

def load_puzzle_edges(path: str) -> torch.Tensor:
    """Load puzzle pieces from CSV. Each row is one piece with edges:
    [top, right, bottom, left] (4 binary masks of length N_COLORS).
    Returns tensor of shape (N_PIECES, N_ROT, 4) with rotation expanded.
    """
    raw = open(path).read().strip().split("\n")
    n = int(raw[0])
    assert n == N, f"expected N={N}, got {n}"
    pieces = []
    for i, line in enumerate(raw[1:], 1):
        # Each row has 4 binary VALUES (top, right, bottom, left).
        # The string is parsed as binary; 65535 = BORDER (=0); else u8 cast.
        parts = line.split(",")
        edges = []
        for j in range(4):
            mask = parts[j]
            v = int(mask, 2)
            if v == 65535:
                color = BORDER
            else:
                assert 0 <= v <= 255, f"color value {v} out of range"
                color = v
            edges.append(color)
        pieces.append(edges)
    pieces = np.array(pieces, dtype=np.int64)  # (N_PIECES, 4)
    # For each piece, compute 4 rotations.
    # Rotation r: edges[i] = base[(i + 4 - r) % 4]  (matches the Rust code)
    rotated = np.zeros((N_PIECES, N_ROT, 4), dtype=np.int64)
    for pid in range(N_PIECES):
        base = pieces[pid]
        for r in range(N_ROT):
            for i in range(4):
                rotated[pid, r, i] = base[(i + 4 - r) % 4]
    return torch.from_numpy(rotated)  # (N_PIECES, N_ROT, 4) — N E S W


def load_board(path: str) -> dict[int, tuple[int, int]]:
    """Load a sparse [{pos, piece_id, rotation}] board. Returns pos→(pid, rot)."""
    d = json.load(open(path))
    pl = d["placement"]
    result = {}
    for p in pl:
        if p is None:
            continue
        # Support both sparse (with pos) and dense (indexed) formats
        if "pos" in p:
            result[p["pos"]] = (p["piece_id"], p["rotation"])
    return result


# ============================================================================
# Adjacency and edge-matching tables
# ============================================================================

def build_adjacencies() -> list[tuple[int, int, int]]:
    """List of (c1, c2, side1, side2) for each undirected adjacent pair.
    side encoding: 0=N, 1=E, 2=S, 3=W. side1 is direction from c1 to c2;
    side2 is direction from c2 to c1.
    """
    adj = []
    for c in range(N_POS):
        x, y = c % N, c // N
        # Right neighbour: c → c+1, side1=E (1), side2=W (3)
        if x + 1 < N:
            adj.append((c, c + 1, 1, 3))
        # Bottom neighbour: c → c+N, side1=S (2), side2=N (0)
        if y + 1 < N:
            adj.append((c, c + N, 2, 0))
    return adj


def cell_border_needs(c: int) -> tuple[bool, bool, bool, bool]:
    """Returns (need_n_border, need_e_border, need_s_border, need_w_border)."""
    x, y = c % N, c // N
    return (y == 0, x == N - 1, y == N - 1, x == 0)


def build_variant_mask(edges: torch.Tensor) -> torch.Tensor:
    """For each cell c, mask of (pid, rot) variants that satisfy border constraints.
    Returns shape (N_POS, N_VARIANTS) of {0, 1}.
    """
    mask = torch.zeros((N_POS, N_VARIANTS), dtype=torch.float32)
    for c in range(N_POS):
        n_b, e_b, s_b, w_b = cell_border_needs(c)
        for pid in range(N_PIECES):
            for r in range(N_ROT):
                e_n, e_e, e_s, e_w = edges[pid, r]
                e_n_b = e_n.item() == BORDER
                e_e_b = e_e.item() == BORDER
                e_s_b = e_s.item() == BORDER
                e_w_b = e_w.item() == BORDER
                if (e_n_b == n_b) and (e_e_b == e_b) and (e_s_b == s_b) and (e_w_b == w_b):
                    mask[c, pid * N_ROT + r] = 1.0
    return mask


def build_edge_color_tensor(edges: torch.Tensor) -> torch.Tensor:
    """Returns (N_VARIANTS, 4) tensor: color on each side of each (pid, rot) variant."""
    return edges.view(N_VARIANTS, 4)  # already in N_E_S_W order


# ============================================================================
# Expected matched-edge score (differentiable)
# ============================================================================

class ScoreModel(torch.nn.Module):
    """Soft-assignment scoring.

    State: logits z of shape (N_POS, N_VARIANTS).
    For each cell c, x[c] = softmax(z[c]) * variant_mask[c] / normalizer
      (only valid variants get probability).
    Score = Σ_{(c1, c2, s1, s2) ∈ adj} Σ_{v1, v2} x[c1, v1] * x[c2, v2] * [color(v1, s1) == color(v2, s2)]

    The match indicator [c1.s1 == c2.s2] only counts if BOTH sides are interior
    (non-border colors match). Border-to-border is already constrained by the mask.
    """
    def __init__(self, edges: torch.Tensor, device: str = "cpu"):
        super().__init__()
        self.device = device
        self.edge_color = build_edge_color_tensor(edges).to(device)  # (V, 4)
        self.variant_mask = build_variant_mask(edges).to(device)  # (P, V)
        self.adj = build_adjacencies()  # list

        # Precompute the "match" tensors per adjacency:
        # For each (c1, c2, s1, s2), build M_{v1, v2} = [color(v1, s1) == color(v2, s2)] in {0, 1}.
        # Memory: |adj| * V * V * float32 = 480 * 1024 * 1024 * 4 = 2.0 GB — too big.
        # Instead, for each adjacency we'll compute on-the-fly via outer product of color slices.
        # We index by side: for each side s ∈ {0..3}, edge_color[:, s] gives (V,) color.

        # Initialize logits
        self.z = torch.nn.Parameter(torch.zeros(N_POS, N_VARIANTS, device=device))

    def get_soft_assignment(self) -> torch.Tensor:
        """Compute x = masked-softmax of z."""
        # Mask invalid variants: set logits to -inf for masked-out variants.
        z_masked = self.z.masked_fill(self.variant_mask == 0, float("-inf"))
        # Softmax over variants for each cell.
        x = F.softmax(z_masked, dim=1)
        return x  # (P, V)

    def score_relaxed(self, x: torch.Tensor) -> torch.Tensor:
        """Compute expected matched-edge score.

        For each adjacency (c1, c2, s1, s2):
          score_adj = Σ_{v1, v2} x[c1, v1] * x[c2, v2] * [color(v1, s1) == color(v2, s2)]
                    = Σ_{c ∈ N_COLORS} (Σ_{v1: color(v1,s1)==c} x[c1, v1]) * (Σ_{v2: color(v2,s2)==c} x[c2, v2])
        This is O(N_COLORS) per adjacency — fast.
        """
        total = torch.zeros((), device=self.device)
        for c1, c2, s1, s2 in self.adj:
            # For each color value, sum probabilities of variants with that color on side s1
            x_c1 = x[c1]  # (V,)
            x_c2 = x[c2]  # (V,)
            color_s1 = self.edge_color[:, s1]  # (V,)
            color_s2 = self.edge_color[:, s2]  # (V,)
            # Aggregate by color
            p1 = torch.zeros(N_COLORS, device=self.device).scatter_add(0, color_s1, x_c1)
            p2 = torch.zeros(N_COLORS, device=self.device).scatter_add(0, color_s2, x_c2)
            # Match score is Σ over interior colors (skip BORDER as borders already constrained)
            # Border-to-border matches are 0-edges (no real adjacency), so subtract border-border product.
            total = total + (p1 * p2).sum() - p1[BORDER] * p2[BORDER]
        return total

    def uniqueness_penalty(self, x: torch.Tensor) -> torch.Tensor:
        """L2 penalty on (Σ_c x[c, p_*] - 1)² for each piece p."""
        # Sum over rotations: x_by_piece[c, p] = Σ_r x[c, p*N_ROT + r]
        x_by_piece = x.view(N_POS, N_PIECES, N_ROT).sum(dim=2)  # (P, N_PIECES)
        piece_total = x_by_piece.sum(dim=0)  # (N_PIECES,)
        return ((piece_total - 1.0) ** 2).sum()

    def pin_hints(self):
        """Force canonical hint positions to one-hot via huge negative logits everywhere else."""
        with torch.no_grad():
            for pos, (pid, rot) in CANONICAL_HINTS.items():
                v_idx = pid * N_ROT + rot
                self.z[pos] = -1e6
                self.z[pos, v_idx] = 0.0


def init_logits_from_board(model: ScoreModel, board: dict[int, tuple[int, int]],
                            noise_scale: float = 0.5):
    """Initialize logits to favor the placement from a given board (with noise)."""
    with torch.no_grad():
        for pos, (pid, rot) in board.items():
            v_idx = pid * N_ROT + rot
            # Boost the chosen variant's logit
            model.z[pos] *= 0
            model.z[pos] += torch.randn_like(model.z[pos]) * noise_scale
            model.z[pos, v_idx] = 5.0  # strong preference
    model.pin_hints()


# ============================================================================
# Hungarian projection: from soft x to discrete (pid, rot) per cell
# ============================================================================

def hungarian_project(x: torch.Tensor) -> dict[int, tuple[int, int]]:
    """Project soft assignment x ∈ (N_POS, N_VARIANTS) to a feasible discrete
    assignment via Hungarian on the bipartite graph (cells × pieces).

    Cost matrix C[c, p] = -max_r x[c, p, r]  (so min-cost = max-prob).
    For each cell c we also need to know which rotation, given the chosen piece.

    NaN values (from softmax over all-masked logits) are replaced with cost 0
    so Hungarian still finds an assignment, though it may be poor.

    Returns dict pos→(pid, rot).
    """
    # Reshape x to (cells, pieces, rotations)
    x_view = x.view(N_POS, N_PIECES, N_ROT).cpu().detach().numpy()
    # Replace NaN/Inf with 0
    x_view = np.nan_to_num(x_view, nan=0.0, posinf=0.0, neginf=0.0)
    # For each (cell, piece), best rotation:
    best_rot_per_pp = x_view.argmax(axis=2)  # (N_POS, N_PIECES)
    # Cost = -max_r x[c, p, r]; clip to finite range
    cost = -x_view.max(axis=2)  # (N_POS, N_PIECES)
    cost = np.nan_to_num(cost, nan=1e9, posinf=1e9, neginf=-1e9)
    # Hungarian: find assignment cell→piece minimizing total cost.
    row_ind, col_ind = linear_sum_assignment(cost)
    # row_ind = 0..255 in order, col_ind = chosen piece per cell.
    result = {}
    for c, p in zip(row_ind.tolist(), col_ind.tolist()):
        r = int(best_rot_per_pp[c, p])
        result[c] = (p, r)
    return result


def score_discrete(placement: dict[int, tuple[int, int]], edges: torch.Tensor) -> int:
    """Compute integer matched-edge score for a discrete placement.
    Matches the official score_board: only counts INTERNAL adjacencies
    (between two placed pieces); BORDER never equals interior so border
    cells contribute 0. Max = 480 = 240 horizontal + 240 vertical.
    """
    score = 0
    edges_np = edges.cpu().numpy()
    adj = build_adjacencies()
    for c1, c2, s1, s2 in adj:
        p1 = placement.get(c1)
        p2 = placement.get(c2)
        if p1 is None or p2 is None:
            continue
        pid1, rot1 = p1
        pid2, rot2 = p2
        e1 = edges_np[pid1, rot1, s1]
        e2 = edges_np[pid2, rot2, s2]
        if e1 == e2 and e1 != BORDER:
            score += 1
    return score


def check_canonical_hints(placement: dict[int, tuple[int, int]]) -> int:
    """Returns count of canonical hints honored (0..5)."""
    n = 0
    for pos, (pid, rot) in CANONICAL_HINTS.items():
        actual = placement.get(pos)
        if actual is not None and actual == (pid, rot):
            n += 1
    return n


# ============================================================================
# Main optimization loop
# ============================================================================

def optimize(
    edges: torch.Tensor,
    init_board: dict[int, tuple[int, int]] | None,
    steps: int = 1000,
    lr: float = 0.5,
    lambda_init: float = 0.01,
    lambda_growth: float = 1.005,
    device: str = "cpu",
    verbose: bool = True,
) -> tuple[dict[int, tuple[int, int]], dict]:
    model = ScoreModel(edges, device=device).to(device)
    if init_board is not None:
        init_logits_from_board(model, init_board)
    else:
        # Just pin hints
        model.pin_hints()

    optimizer = torch.optim.Adam([model.z], lr=lr)
    lambda_ = lambda_init

    history = []
    best_score = -1
    best_placement = None
    best_hints_ok = 0

    t0 = time.time()

    for step in range(steps):
        optimizer.zero_grad()
        x = model.get_soft_assignment()
        score = model.score_relaxed(x)
        penalty = model.uniqueness_penalty(x)
        loss = -score + lambda_ * penalty

        loss.backward()
        # Mask hint gradients (don't update pinned logits)
        with torch.no_grad():
            for pos in CANONICAL_HINTS:
                if model.z.grad is not None:
                    model.z.grad[pos] = 0
        optimizer.step()
        lambda_ *= lambda_growth

        if step % 50 == 0 or step == steps - 1:
            # Project to integer assignment and measure
            with torch.no_grad():
                x_eval = model.get_soft_assignment()
                placement = hungarian_project(x_eval)
                discrete_score = score_discrete(placement, edges)
                hints_ok = check_canonical_hints(placement)
                history.append({
                    "step": step,
                    "soft_score": float(score.item()),
                    "soft_penalty": float(penalty.item()),
                    "discrete_score": discrete_score,
                    "hints_ok": hints_ok,
                    "lambda": lambda_,
                    "elapsed_s": time.time() - t0,
                })
                if discrete_score > best_score:
                    best_score = discrete_score
                    best_placement = placement
                    best_hints_ok = hints_ok
                if verbose:
                    print(f"  step {step:5d}  soft={score.item():7.2f}  pen={penalty.item():7.2f}  "
                          f"discrete={discrete_score}/480  hints={hints_ok}/5  λ={lambda_:.3f}  "
                          f"({time.time() - t0:.1f}s)")

    return best_placement, {
        "history": history,
        "best_score": best_score,
        "best_hints_ok": best_hints_ok,
        "elapsed_s": time.time() - t0,
    }


# ============================================================================
# CLI
# ============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puzzle", default="../../../data/puzzles/size_16_official_eternity.csv")
    ap.add_argument("--start", default=None, help="JSON board to initialize from")
    ap.add_argument("--steps", type=int, default=500)
    ap.add_argument("--lr", type=float, default=0.5)
    ap.add_argument("--lambda-init", type=float, default=0.01)
    ap.add_argument("--lambda-growth", type=float, default=1.005)
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps"])
    ap.add_argument("--out", default="output/vol-37_revised/gh_e2/result.json")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    print(f"[gh_e2] loading puzzle: {args.puzzle}", file=sys.stderr)
    edges = load_puzzle_edges(args.puzzle)

    init_board = None
    if args.start:
        print(f"[gh_e2] loading start board: {args.start}", file=sys.stderr)
        init_board = load_board(args.start)
        print(f"  loaded {len(init_board)} placements", file=sys.stderr)
        # Initial score
        s = score_discrete(init_board, edges)
        h = check_canonical_hints(init_board)
        print(f"  initial discrete score: {s}/480  hints: {h}/5", file=sys.stderr)

    print(f"[gh_e2] optimizing: steps={args.steps} lr={args.lr} λ_init={args.lambda_init} "
          f"λ_growth={args.lambda_growth} device={args.device}",
          file=sys.stderr)
    best, stats = optimize(
        edges, init_board, args.steps, args.lr, args.lambda_init, args.lambda_growth,
        args.device, verbose=True,
    )
    print(f"\n[gh_e2] DONE: best score = {stats['best_score']}/480, hints = {stats['best_hints_ok']}/5",
          file=sys.stderr)

    # Save
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    placement_sparse = [{"pos": pos, "piece_id": pid, "rotation": rot}
                        for pos, (pid, rot) in sorted(best.items())]
    with open(out_path, "w") as f:
        json.dump({"placement": placement_sparse, "score": stats["best_score"],
                   "hints_ok": stats["best_hints_ok"], "stats": stats}, f, indent=2)
    print(f"[gh_e2] saved: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
