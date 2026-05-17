"""W1 v2 — PEPS contraction with Lagrangian piece-uniqueness for E2.

Same encoding as v1, but with ANALYTIC gradients for the Lagrangian dual:
  ⟨q_p⟩ = E[number of times piece p is used]
        = sum_i E[ 1[piece at cell i = p] ]
        = sum_i P_i(piece = p)

P_i(piece = p) is computed from the per-cell signature marginal P_i(cN, cE, cS, cW)
which is obtained via a single full-PEPS contraction with cell i's tensor opened.

Efficient implementation:
  - Compute full Z with all cells closed → Z_full.
  - For each cell i, compute Z_i_open by opening cell i's tensor (keep its 4 axes).
    This gives Z_i_open shape (K, K, K, K) — the unnormalized signature marginal.
  - Normalize: P_i(cN,cE,cS,cW) = Z_i_open[cN,cE,cS,cW] * cell_i_tensor[...] / Z_full
    Actually: Z_full = sum over all (cN,cE,cS,cW) of Z_i_open[cN,cE,cS,cW] * cell_i_tensor[cN,cE,cS,cW]
    P_i(sig) = (Z_i_open[sig] * cell_i_weight[sig]) / Z_full
    where cell_i_weight[sig] = sum_{pid,rot at sig} e^{-mu[pid]}
  - For each (pid, rot) at signature sig, conditional probability that piece pid is at cell i:
      P_i(pid) = sum_{rot} sum_{sig such that piece pid at rot has signature sig}
                 [ P_i(sig) * w(pid|sig) ]
    where w(pid|sig) is the conditional probability that, given signature sig at cell i,
    the placed piece is pid. Specifically:
      w(pid|sig) = e^{-mu[pid]} / sum_{pid',rot' at sig} e^{-mu[pid']}
    Thus piece marginal at cell i for piece pid:
      P_i(pid) = sum_{rot} P_i(sig(pid,rot)) * e^{-mu[pid]} / cell_i_weight[sig(pid,rot)]
    But cell_i_weight[sig] = sum_{(pid',rot') at sig} e^{-mu[pid']}, so:
      P_i(pid) = sum_{rot} Z_i_open[sig(pid,rot)] * e^{-mu[pid]} / Z_full

This gives EXACT analytic gradients in 1 + n_cells contractions per iteration
(vs n_pieces contractions for finite-diff). For 6x6: 36 contractions vs 256.
For 16x16: 256 vs 256 — same count but smaller constants because no eps.

Even better: we can compute all n_cells opened contractions in a single
"differentiated" contraction via opt_einsum's "contract with multiple outputs",
but that's an optimization for later. For now, one open contraction per cell.

Usage:
  python3 peps_lagrangian_v2.py <puzzle.csv> [--beta 1.0] [--eta 0.5] [--max-iter 100]
"""

from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import opt_einsum as oe

sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, load_puzzle, BORDER


def build_piece_signature_lookup(puzzle: Puzzle) -> dict[tuple[int, int, int, int], list[tuple[int, int]]]:
    """For each (N, E, S, W) color tuple, list of (piece_id, rotation) producing it."""
    lookup: dict[tuple[int, int, int, int], list[tuple[int, int]]] = {}
    for pid in range(puzzle.n_pieces):
        for rot in range(4):
            sig = puzzle.piece_edges(pid, rot)
            lookup.setdefault(sig, []).append((pid, rot))
    return lookup


def build_cell_tensor(
    puzzle: Puzzle,
    pos: int,
    lookup: dict,
    mu: np.ndarray,
) -> np.ndarray:
    """Build the cell tensor at pos. Shape (K, K, K, K) over (cN, cE, cS, cW)."""
    K = puzzle.n_colors
    size = puzzle.size
    y, x = pos // size, pos % size
    n_border = y == 0
    s_border = y == size - 1
    w_border = x == 0
    e_border = x == size - 1

    T = np.zeros((K, K, K, K), dtype=np.float64)
    for sig, placements in lookup.items():
        cN, cE, cS, cW = sig
        if n_border and cN != BORDER: continue
        if s_border and cS != BORDER: continue
        if w_border and cW != BORDER: continue
        if e_border and cE != BORDER: continue
        if not n_border and cN == BORDER: continue
        if not s_border and cS == BORDER: continue
        if not w_border and cW == BORDER: continue
        if not e_border and cE == BORDER: continue

        w = 0.0
        for pid, rot in placements:
            w += np.exp(-mu[pid])
        T[cN, cE, cS, cW] += w
    return T


def build_cell_tensor_per_piece(
    puzzle: Puzzle,
    pos: int,
    lookup: dict,
    mu: np.ndarray,
    target_pid: int,
) -> np.ndarray:
    """Same as build_cell_tensor but only count contribution from target_pid (any rotation)."""
    K = puzzle.n_colors
    size = puzzle.size
    y, x = pos // size, pos % size
    n_border = y == 0
    s_border = y == size - 1
    w_border = x == 0
    e_border = x == size - 1

    T = np.zeros((K, K, K, K), dtype=np.float64)
    for sig, placements in lookup.items():
        cN, cE, cS, cW = sig
        if n_border and cN != BORDER: continue
        if s_border and cS != BORDER: continue
        if w_border and cW != BORDER: continue
        if e_border and cE != BORDER: continue
        if not n_border and cN == BORDER: continue
        if not s_border and cS == BORDER: continue
        if not w_border and cW == BORDER: continue
        if not e_border and cE == BORDER: continue

        w = 0.0
        for pid, _rot in placements:
            if pid == target_pid:
                w += np.exp(-mu[pid])
        if w > 0:
            T[cN, cE, cS, cW] += w
    return T


def slice_border(T: np.ndarray, pos: int, size: int) -> np.ndarray:
    """Slice border-fixed axes (set to BORDER=0) and return reduced tensor."""
    y, x = pos // size, pos % size
    sl: list = [slice(None)] * 4
    if y == 0: sl[0] = BORDER
    if x == size - 1: sl[1] = BORDER
    if y == size - 1: sl[2] = BORDER
    if x == 0: sl[3] = BORDER
    return T[tuple(sl)]


def build_einsum_for_contraction(
    puzzle: Puzzle,
    open_cell: int | None = None,
) -> tuple[list, list, dict]:
    """
    Build the einsum specification for full PEPS contraction.

    Args:
      open_cell: if not None, leave this cell's 4 axes as output indices (after
                 border-slicing). Otherwise full contraction → scalar.

    Returns:
      cell_label_lists: list[size*size] of axis-label lists (after slicing)
      output_labels: list of axis labels for the result
      meta: dict with bond->axis mapping etc.
    """
    size = puzzle.size

    bond_id = 0
    bond_labels: dict[tuple[str, int, int], int] = {}

    def get_h_bond(y, x) -> int:
        nonlocal bond_id
        key = ('h', y, x)
        if key not in bond_labels:
            bond_labels[key] = bond_id
            bond_id += 1
        return bond_labels[key]

    def get_v_bond(y, x) -> int:
        nonlocal bond_id
        key = ('v', y, x)
        if key not in bond_labels:
            bond_labels[key] = bond_id
            bond_id += 1
        return bond_labels[key]

    cell_label_lists = []
    output_labels: list[int] = []

    for pos in range(size * size):
        y, x = pos // size, pos % size
        labels = []

        # Axis order is (N, E, S, W). We must preserve this order
        # so that the sliced tensor (when target is open_cell) keeps
        # axes in (cN, cE, cS, cW) order.
        if pos == open_cell:
            # We want the open cell's axes to remain in the output.
            # Surviving axes (those that aren't border-sliced) get fresh labels.
            # CRITICAL: We must NOT use a shared bond label, because for the
            # open cell, the neighboring cells should still have their bonds
            # contracted with the neighbor... wait, actually, the open cell
            # IS connected to neighbors via bonds, so if we want to keep
            # its 4 axes open, we must duplicate the bond labels: neighbor
            # uses bond label, open cell uses a fresh open label. Then we
            # add a delta tensor to enforce the bond.
            # Simpler approach: open the cell's INTERNAL axes (a separate
            # set), then connect via a 1-d identity tensor that has both the
            # open label and the bond label. This is more work.
            #
            # Cleanest approach: just don't use open_cell mode here, instead
            # compute marginals using a DIFFERENT method (see compute_marginals).
            raise NotImplementedError("open_cell handled separately")

        # Standard closed-cell: use bond labels for surviving axes.
        if y > 0:
            labels.append(get_v_bond(y - 1, x))  # N axis
        if x < size - 1:
            labels.append(get_h_bond(y, x))  # E axis
        if y < size - 1:
            labels.append(get_v_bond(y, x))  # S axis
        if x > 0:
            labels.append(get_h_bond(y, x - 1))  # W axis
        cell_label_lists.append(labels)

    return cell_label_lists, output_labels, {'bond_labels': bond_labels, 'next_bond_id': bond_id}


def compute_log_Z(
    puzzle: Puzzle,
    cell_tensors_sliced: list[np.ndarray],
    cell_label_lists: list[list[int]],
) -> tuple[float, float]:
    """Compute log Z by full contraction. Returns (log_Z, Z)."""
    operands = []
    for pos in range(puzzle.size * puzzle.size):
        operands.append(cell_tensors_sliced[pos])
        operands.append(cell_label_lists[pos])
    operands.append([])  # no output → scalar

    Z = float(oe.contract(*operands))
    if Z <= 0:
        return -np.inf, 0.0
    return float(np.log(Z)), Z


def compute_piece_marginals_analytic(
    puzzle: Puzzle,
    mu: np.ndarray,
) -> tuple[float, np.ndarray]:
    """
    Compute (log_Z, ⟨q_p⟩ for all p) using analytic gradient.

    Strategy:
      For each (cell i, piece p), we want P_i(piece = p, anything else).
      This equals (1/Z) * sum over configurations consistent with placing piece p at cell i.

      Replace cell i's tensor T_i with T_i^{(p)} (cell tensor counting only piece p);
      contract → Z_i^{(p)}.
      Then P_i(piece=p) = Z_i^{(p)} / Z_full.
      Sum over i: ⟨q_p⟩ = sum_i Z_i^{(p)} / Z_full.

      Total contractions: 1 (for Z) + n_cells * n_pieces (for all i,p pairs).
      = 1 + 256*256 = 65k for canonical → too many.

    Better strategy:
      For each piece p, build a "p-restricted" copy of every cell tensor:
        T_i^{(p)}(cN,cE,cS,cW) = sum over (pid=p, rot) such that piece p at rot has sig (cN,cE,cS,cW)
                                 weighted by e^{-mu[p]}.
      Then for each piece p, compute:
        ⟨q_p⟩ = (1/Z_full) * sum_i Z_i^{(p)}
              = (1/Z_full) * sum_i Contraction(replace cell i with T_i^{(p)})

      This is still n_pieces * n_cells contractions. Still 65k.

    BEST strategy (single pass):
      Compute Z_full with one contraction.
      For each cell i, compute Z_i^open = full contraction with cell i's tensor opened.
        This is a single contraction per cell → n_cells contractions total.
        Z_i^open[cN,cE,cS,cW] = unnormalized signature distribution at cell i, after
                                marginalizing over all other cells.
      Then P_i(cN,cE,cS,cW) = (Z_i^open[cN,cE,cS,cW] * cell_i_weight[cN,cE,cS,cW]) / Z_full
                            = T_i[cN,cE,cS,cW] * Z_i^open[cN,cE,cS,cW] / Z_full
      where T_i is cell i's tensor.

      Then P_i(piece=p) = sum_{rot} sum_{sig such that piece p at rot has sig}
                          [ P_i(sig) * (e^{-mu[p]} / T_i[sig]) ]
      Simplify: if (pid, rot) at sig contributes w(pid,rot)/T_i[sig] of P_i(sig),
                and T_i[sig] = sum_{(pid',rot') at sig} e^{-mu[pid']},
                then P_i(piece=p) = sum_{rot} P_i(sig(p,rot)) * e^{-mu[p]} / T_i[sig(p,rot)]
                                  = sum_{rot} (T_i[sig] * Z_i^open[sig] / Z_full) * e^{-mu[p]} / T_i[sig]
                                  = sum_{rot} Z_i^open[sig(p,rot)] * e^{-mu[p]} / Z_full

      So: P_i(piece=p) = e^{-mu[p]} / Z_full * sum_{rot} Z_i^open[sig(p,rot)]
      And ⟨q_p⟩ = sum_i P_i(piece=p)

      Total contractions: 1 + n_cells = 1 + 256 = 257 for canonical scale.
      This is MUCH better than n_pieces * n_cells.

    Implementation:
      For each cell i, do a contraction with cell i's tensor opened (4 free axes
      sized [K x K x K x K], minus any sliced border axes).
    """
    K = puzzle.n_colors
    size = puzzle.size
    lookup = build_piece_signature_lookup(puzzle)

    # Build all cell tensors (closed; full 4-axis, dim K each)
    cell_tensors_full = [build_cell_tensor(puzzle, pos, lookup, mu) for pos in range(size * size)]
    # Sliced versions (border axes sliced to BORDER=0)
    cell_tensors_sliced = [slice_border(cell_tensors_full[pos], pos, size) for pos in range(size * size)]

    # Build closed contraction spec
    bond_id = 0
    bond_labels: dict[tuple[str, int, int], int] = {}
    def gh(y, x):
        nonlocal bond_id
        k = ('h', y, x)
        if k not in bond_labels:
            bond_labels[k] = bond_id; bond_id += 1
        return bond_labels[k]
    def gv(y, x):
        nonlocal bond_id
        k = ('v', y, x)
        if k not in bond_labels:
            bond_labels[k] = bond_id; bond_id += 1
        return bond_labels[k]

    cell_label_lists = []
    for pos in range(size * size):
        y, x = pos // size, pos % size
        labels = []
        if y > 0: labels.append(gv(y - 1, x))
        if x < size - 1: labels.append(gh(y, x))
        if y < size - 1: labels.append(gv(y, x))
        if x > 0: labels.append(gh(y, x - 1))
        cell_label_lists.append(labels)

    # Compute Z_full
    operands = []
    for pos in range(size * size):
        operands.append(cell_tensors_sliced[pos])
        operands.append(cell_label_lists[pos])
    operands.append([])
    Z_full = float(oe.contract(*operands))
    if Z_full <= 0:
        return -np.inf, np.zeros(puzzle.n_pieces)
    log_Z = float(np.log(Z_full))

    # For each cell, compute Z_i^open by REMOVING cell i's tensor and exposing
    # its 4 bond axes as output. We use the closed tensors of OTHER cells.
    # The output axes correspond to the bonds at cell i that ARE interior.
    # The border-fixed axes don't need to be output (they're fixed).
    #
    # Specifically: cell i has 4 axes (N, E, S, W). After border-slicing, some
    # subset remains. The Z_i^open will have those axes as outputs.
    # Then P_i(sig) = T_i_sliced[sig_indices] * Z_i^open[sig_indices] / Z_full.

    # We need to use a fresh set of labels for the open axes (so they're not
    # contracted away). Use negative labels for clarity (opt_einsum supports
    # any hashable). Actually opt_einsum needs int or str. Use big ints.

    q = np.zeros(puzzle.n_pieces, dtype=np.float64)

    OPEN_LABEL_BASE = 10000
    for i in range(size * size):
        # Construct operands list: include all cells EXCEPT cell i's tensor.
        # Cell i's bond axes (post-slicing) become output axes.
        operands_i = []
        for pos in range(size * size):
            if pos == i: continue
            operands_i.append(cell_tensors_sliced[pos])
            operands_i.append(cell_label_lists[pos])
        # Output axes = cell i's surviving labels (in their order)
        out_labels = cell_label_lists[i]
        operands_i.append(out_labels)

        Z_i_open = oe.contract(*operands_i)
        # Z_i_open is now a tensor with shape matching cell_tensors_sliced[i]
        # Its values are the partial Z when cell i's signature is the index.

        # Now: P_i(piece=p) = e^{-mu[p]} / Z_full * sum_{rot} Z_i_open[sig(p,rot)]
        # We iterate over all (p, rot) with sig(p, rot) compatible with cell i's border constraints.
        y, x = i // size, i % size
        n_border = y == 0
        s_border = y == size - 1
        w_border = x == 0
        e_border = x == size - 1

        for pid in range(puzzle.n_pieces):
            for rot in range(4):
                sig = puzzle.piece_edges(pid, rot)  # (cN, cE, cS, cW)
                cN, cE, cS, cW = sig
                # Check border consistency
                if n_border and cN != BORDER: continue
                if s_border and cS != BORDER: continue
                if w_border and cW != BORDER: continue
                if e_border and cE != BORDER: continue
                if not n_border and cN == BORDER: continue
                if not s_border and cS == BORDER: continue
                if not w_border and cW == BORDER: continue
                if not e_border and cE == BORDER: continue

                # Index Z_i_open using the surviving axes
                idx = []
                if not n_border: idx.append(cN)
                if not e_border: idx.append(cE)
                if not s_border: idx.append(cS)
                if not w_border: idx.append(cW)
                # Z_i_open shape matches: N (only if y>0), E (only if x<size-1),
                # S (only if y<size-1), W (only if x>0)
                # Wait — the surviving axes in the SLICED tensor are determined
                # by NOT being border. Let me re-check.
                # In build_cell_tensor, the full tensor is (K,K,K,K) in (N,E,S,W).
                # In slice_border, we set border axes to BORDER. So sliced tensor's
                # shape removes those axes:
                #   if y==0: N is sliced (axis 0 removed)
                #   if x==size-1: E is sliced (axis 1 removed, originally)
                #   if y==size-1: S removed
                #   if x==0: W removed
                # The output of slice_border preserves the order of non-removed axes.
                # So the surviving axes (in order) are: N (if not n_border),
                # E (if not e_border), S (if not s_border), W (if not w_border).
                # Hmm, careful: my cell_label_lists adds labels in this order:
                #   if y > 0: N
                #   if x < size-1: E
                #   if y < size-1: S
                #   if x > 0: W
                # which matches "if not n_border", "if not e_border", etc. ✓

                # The signature constraints are: if border, sig[k] must be BORDER (we checked).
                # The non-border parts of sig are: (cN if not n_border, cE if not e_border, ...).

                if len(idx) == 0:
                    Z_open_val = float(Z_i_open)
                else:
                    Z_open_val = float(Z_i_open[tuple(idx)])

                contrib = np.exp(-mu[pid]) * Z_open_val / Z_full
                q[pid] += contrib

    return log_Z, q


def lagrangian_dual_loop(
    puzzle: Puzzle,
    eta: float = 0.5,
    max_iter: int = 100,
    tol: float = 1e-3,
    verbose: bool = True,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    Run Lagrangian dual loop. Returns (final mu, final q, final log_Z).
    """
    mu = np.zeros(puzzle.n_pieces, dtype=np.float64)
    log_Z = -np.inf
    q = np.zeros(puzzle.n_pieces)

    t0 = time.time()
    for it in range(max_iter):
        log_Z, q = compute_piece_marginals_analytic(puzzle, mu)
        gap = q - 1.0
        gap_inf = float(np.max(np.abs(gap)))

        if verbose and (it < 10 or it % 10 == 0):
            elapsed = time.time() - t0
            print(f"  iter {it:3d}: log_Z={log_Z:.4f} |⟨q⟩-1|_∞={gap_inf:.5f} "
                  f"max⟨q⟩={q.max():.3f} min⟨q⟩={q.min():.3f} t={elapsed:.1f}s")

        if gap_inf < tol:
            print(f"  Lagrangian dual converged at iter {it}")
            break
        mu = mu + eta * gap

    return mu, q, log_Z


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("puzzle", help="path to puzzle CSV")
    ap.add_argument("--eta", type=float, default=0.5)
    ap.add_argument("--max-iter", type=int, default=100)
    ap.add_argument("--tol", type=float, default=1e-3)
    args = ap.parse_args()

    p = load_puzzle(args.puzzle)
    print(f"Loaded: size={p.size} pieces={p.n_pieces} interior_colors={p.n_interior_colors}")

    lookup = build_piece_signature_lookup(p)
    print(f"unique signatures: {len(lookup)} total placements: {sum(len(v) for v in lookup.values())}")

    t0 = time.time()
    print(f"\nLagrangian dual loop (eta={args.eta}, max_iter={args.max_iter}):")
    mu_final, q_final, log_Z_final = lagrangian_dual_loop(
        p, args.eta, args.max_iter, args.tol
    )
    elapsed = time.time() - t0
    print(f"\nFinal: log_Z={log_Z_final:.4f} max⟨q⟩={q_final.max():.4f} min⟨q⟩={q_final.min():.4f}")
    print(f"Time: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
