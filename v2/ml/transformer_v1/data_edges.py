"""Edge-based synthetic data for the v2 transformer.

Each training sample:
- INPUT: 256 cells × 4 edges. Some cells masked (all 4 edges = EMPTY).
- TARGET: 256 cells × 4 edges with TRUE colors at masked positions.

The model predicts edge colors at masked cells given the partial board.
This is INDEPENDENT of piece identity — same architecture trained on
synthetic E2-family puzzles transfers to canonical E2.
"""

from __future__ import annotations
import random
import torch

N_CELLS = 256
W = 16
N_COLORS = 23
EMPTY_COLOR = N_COLORS  # = 23, sentinel


# Canonical E2 color rarity distribution (vol-125 measurement 2026-05-18):
#   - Colors 1-5 (5 rare): 24 piece-side occurrences each
#   - Colors 6-10 (5 medium): 48 each
#   - Colors 11-22 (12 common): 50 each
# Total interior occurrences = 5*24 + 5*48 + 12*50 = 960.
# Each interior EDGE is shared by 2 piece-sides, so n_interior_edges = 480.
# Edge color sampled with frequency proportional to (occurrences / 2).
CANONICAL_E2_COLOR_FREQ = (
    [24] * 5 + [48] * 5 + [50] * 12  # for colors 1..22
)  # = 22 entries, sums to 960


def generate_edge_board(n_colors: int, rng: random.Random,
                        canonical_dist: bool = True) -> list[tuple]:
    """Generate a 256-cell edge-matched board.

    If canonical_dist=True, sample edge colors per the canonical E2
    rarity distribution (rare 1-5 at 24/960, medium 6-10 at 48/960,
    common 11-22 at 50/960). This matches the structural asymmetry of
    Selby-Riordan E2 and should improve transfer to canonical inference.

    If canonical_dist=False, use uniform-random colors (old behavior).

    Returns: list of 256 cells, each a tuple (N, E, S, W) of colors.
    """
    n_horiz = W * (W - 1)  # 240
    n_vert = W * (W - 1)   # 240
    n_total = n_horiz + n_vert  # 480 interior edges

    if canonical_dist and n_colors == 22:
        # Build a target color-occurrence-list, shuffle, assign to edges.
        # Edges are shared by 2 piece-sides → each interior edge contributes
        # 2 occurrences. So total occurrences = 2 * n_total = 960.
        target_occs = []
        for c, n_occ in enumerate(CANONICAL_E2_COLOR_FREQ, start=1):
            target_occs.extend([c] * (n_occ // 2))  # n_occ/2 edges with color c
        # If imbalance, pad with random colors.
        while len(target_occs) < n_total:
            target_occs.append(rng.randint(1, n_colors))
        rng.shuffle(target_occs)
        target_occs = target_occs[:n_total]
        horiz_edges = target_occs[:n_horiz]
        vert_edges = target_occs[n_horiz:]
    else:
        horiz_edges = [rng.randint(1, n_colors) for _ in range(n_horiz)]
        vert_edges = [rng.randint(1, n_colors) for _ in range(n_vert)]

    # Ensure all colors appear at least once.
    all_edges = horiz_edges + vert_edges
    used = set(all_edges)
    missing = [c for c in range(1, n_colors + 1) if c not in used]
    if missing:
        positions = rng.sample(range(len(all_edges)), len(missing))
        for pos, color in zip(positions, missing):
            all_edges[pos] = color
        horiz_edges = all_edges[:n_horiz]
        vert_edges = all_edges[n_horiz:]

    cells = []
    BORDER = 0
    for r in range(W):
        for c in range(W):
            N = BORDER if r == 0 else horiz_edges[(r - 1) * W + c]
            S = BORDER if r == W - 1 else horiz_edges[r * W + c]
            W_ = BORDER if c == 0 else vert_edges[r * (W - 1) + (c - 1)]
            E = BORDER if c == W - 1 else vert_edges[r * (W - 1) + c]
            cells.append((N, E, S, W_))
    return cells


class EdgeBoardDataset(torch.utils.data.IterableDataset):
    """Stream synthetic edge-matched boards with random masking."""

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
        self._epoch = 0

    def __len__(self):
        return self.samples_per_epoch

    def __iter__(self):
        info = torch.utils.data.get_worker_info()
        wid = info.id if info else 0
        rng = random.Random(self.seed * 1_000_000 + wid * 1_000 + self._epoch)
        self._epoch += 1
        for _ in range(self.samples_per_epoch):
            yield self._gen_one(rng)

    def _gen_one(self, rng):
        cells = generate_edge_board(self.n_colors, rng)
        n_mask = rng.randint(self.mask_min, min(self.mask_max, N_CELLS - 1))
        masked_set = set(rng.sample(range(N_CELLS), n_mask))

        # Build input (with masks) and target.
        input_edges = torch.zeros((N_CELLS, 4), dtype=torch.long)
        target_edges = torch.zeros((N_CELLS, 4), dtype=torch.long)
        target_mask = torch.zeros(N_CELLS, dtype=torch.bool)
        for pos in range(N_CELLS):
            N, E, S, W_ = cells[pos]
            if pos in masked_set:
                input_edges[pos] = EMPTY_COLOR  # all 4 EMPTY
                target_edges[pos, 0] = N
                target_edges[pos, 1] = E
                target_edges[pos, 2] = S
                target_edges[pos, 3] = W_
                target_mask[pos] = True
            else:
                input_edges[pos, 0] = N
                input_edges[pos, 1] = E
                input_edges[pos, 2] = S
                input_edges[pos, 3] = W_

        return {
            "input_edges": input_edges,
            "target_edges": target_edges,
            "target_mask": target_mask,
        }


def board_from_canonical_csv(csv_path: str) -> list[tuple]:
    """Load canonical E2 puzzle CSV → 256 cells of (N, E, S, W) colors.

    BORDER (65535 in raw CSV) → 0.
    """
    import csv
    cells = []
    BORDER_RAW = 65535
    BORDER_OUT = 0
    with open(csv_path) as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            N, E, S, W_ = (int(row[i].strip(), 2) for i in range(4))
            N = BORDER_OUT if N == BORDER_RAW else N
            E = BORDER_OUT if E == BORDER_RAW else E
            S = BORDER_OUT if S == BORDER_RAW else S
            W_ = BORDER_OUT if W_ == BORDER_RAW else W_
            cells.append((N, E, S, W_))
    return cells
