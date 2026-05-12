#!/usr/bin/env python3
"""Vol-13 — per-cell color marginals via two-sided boundary-MPS sweep.

Builds the top-MPS for rows 0..r-1 and the bottom-MPS for rows r+1..15,
then at each row r computes the marginal P(north-color = c | rest of
the grid summed out) for every interior bond.

This is the *information-theoretic value-ordering signal* we need. It
extends what BP (χ=1) produced (commit 8d35677 — paramagnetic). Even if
marginals stay near-uniform, the *deviations from uniform* are a new
signal because they incorporate per-row piece multiplicity that BP does
not.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from v11_load_e2 import load
from v13_boundary_mps import (
    BORDER, DOM, MPS, absorb_row, build_cell_tensor, close_bottom_boundary,
    initial_top_boundary_mps,
)


def initial_bottom_boundary_mps(L: int) -> MPS:
    """Boundary MPS below row 15: all south-edges = BORDER.

    Same structure as the top boundary; we sweep upward.
    """
    return initial_top_boundary_mps(L)  # symmetric


def flip_cell_tensor_vertically(T: np.ndarray) -> np.ndarray:
    """Swap N <-> S in a cell tensor for upward sweeping."""
    # T axes: (N, E, S, W). Swap N and S => transpose (2,1,0,3).
    return T.transpose(2, 1, 0, 3).copy()


def horizontal_marginals(top_mps: MPS, bot_mps: MPS, cell_tensors_row: list[np.ndarray]):
    """Compute marginals at each cell in a given row.

    top_mps: MPS over north-edges of this row.
    bot_mps: MPS over south-edges of this row (built from below).
    cell_tensors_row: the L cell tensors for this row.

    Returns dict with:
      - 'north_marginals': list of L probability vectors (each of size DOM),
        marginal of north-edge of cell c when summing over all other vars.
      - 'south_marginals': same but for south-edges.
      - 'log_Z_row': log of partition function restricted to this row's plate.

    Implementation: form, for each column c, the contracted tensor
      M_c[north_c, south_c, east_left, east_right]
    by absorbing top_mps[c] and bot_mps[c] but leaving the physical
    legs and horizontal bonds for the row free. Then sweep horizontally
    to compute Z and marginals.
    """
    L = len(cell_tensors_row)
    assert L == top_mps.length() == bot_mps.length()

    # Step 1: contract each top_mps site with bot_mps site & cell tensor
    # to form a "site superoperator" indexed by (chi_t_l, chi_t_r,
    # chi_b_l, chi_b_r, W, E).
    # site_t shape (cl_t, d=N, cr_t).
    # site_b shape (cl_b, d=S, cr_b).
    # T shape (N, E, S, W).
    # Result M_c[ctl, ctr, cbl, cbr, E, W] = sum_{N, S} site_t[ctl, N, ctr] *
    #     site_b[cbl, S, cbr] * T[N, E, S, W].
    Ms = []
    for c in range(L):
        st = top_mps.sites[c]
        sb = bot_mps.sites[c]
        T = cell_tensors_row[c]
        M = np.einsum('inj,ksl,nesw->ijklew', st, sb, T)
        # Indices: i=ctl, j=ctr, k=cbl, l=cbr, e=E, w=W
        Ms.append(M)

    # Step 2: contract horizontally. Left edge boundary: W of cell 0 = BORDER.
    # Right edge boundary: E of cell L-1 = BORDER.
    # Carry: L_env[ctl, cbl, W=BORDER (or current_E)].
    # For col 0, slice M_0 along W=BORDER.
    # Z = sum over all bonds of [L_env after last cell, evaluated at E=BORDER].

    # We'll do this in two passes to get marginals:
    #  Pass 1: left environments L_env[c] for c = 0..L-1
    #  Pass 2: right environments R_env[c] for c = L-1..0
    #  Marginal at cell c: contract L_env[c-1], M_c with N/S left free, R_env[c+1].

    # Build left envs.
    # L_env[c] has shape (ctr, cbr, E) — the environment after summing
    # cells 0..c.
    # Initial L_env (before any cell): scalar 1.0 with ctr=1 (input MPS
    # left), cbr=1, W slot dim 1 (we'll inject the boundary at W=BORDER
    # via a delta).
    # Easier: pre-slice M_0 along W=BORDER.

    # Pre-slice cell 0 along W=BORDER, cell L-1 along E=BORDER.
    Ms_proc = []
    for c, M in enumerate(Ms):
        Mc = M
        if c == 0:
            # W is the last index. M shape (ctl=1, ctr, cbl=1, cbr, E, W).
            Mc = Mc[:, :, :, :, :, BORDER]  # drop W axis (E2 col 0 -> W=BORDER)
            # New shape (ctl, ctr, cbl, cbr, E)
        else:
            # Keep W axis
            pass
        Ms_proc.append(Mc)

    # Build left envs cleanly.
    # M shape labels: M[ctl, ctr, cbl, cbr, X=E, e=W]
    # L_env labels:   L_env[ctr_prev=ctl, cbr_prev=cbl, e_prev=W]
    # einsum: 'ace,abcdXe->bdX'
    # where a=ctl, b=ctr, c=cbl, d=cbr, X=E, e=W
    left_envs = []
    M0 = Ms_proc[0]  # already W-sliced; shape (ctl=1, ctr, cbl=1, cbr, X=E)
    L_env = M0[0, :, 0, :, :]  # (ctr, cbr, X)
    left_envs.append(L_env)
    for c in range(1, L):
        M = Ms_proc[c]  # shape (ctl, ctr, cbl, cbr, X, e=W)
        L_env = np.einsum('ace,abcdXe->bdX', L_env, M)
        left_envs.append(L_env)

    # Right envs: same idea but starting from the right edge.
    # Cell L-1 is E-sliced: M[ctl, ctr=1, cbl, cbr=1, W].
    # R_env[c] has shape (ctl, cbl, W) and represents cells c..L-1 contracted.
    right_envs = [None] * L
    M_last = Ms[L - 1][:, :, :, :, BORDER, :]  # slice E=BORDER, keep W
    # shape (ctl, ctr=1, cbl, cbr=1, W)
    R_env = M_last[:, 0, :, 0, :]  # (ctl, cbl, W)
    right_envs[L - 1] = R_env
    for c in range(L - 2, -1, -1):
        M = Ms[c]  # (ctl, ctr, cbl, cbr, E=X, W=e)
        # R_env_new[ctl_new=ctl, cbl_new=cbl, W_new=e] =
        #   sum_{ctr, cbr, X=E}  M[ctl, ctr, cbl, cbr, X, e] * R_env_prev[ctr, cbr, X]
        R_env = np.einsum('abcdXe,bdX->ace', M, R_env)
        right_envs[c] = R_env

    # Partition function: contract left_env[L-1] with the right-edge closure.
    # left_envs[L-1] has shape (ctr=1, cbr=1, X=E). E should be BORDER for last col.
    # Z = left_envs[L-1][0, 0, BORDER]
    Z_left = float(left_envs[L - 1][0, 0, BORDER])

    # Also: Z = right_envs[0][0, 0, BORDER]  (consistency check)
    Z_right = float(right_envs[0][0, 0, BORDER])

    # Marginals at cell c: for each (N, S, E, W) the partial trace.
    # The full tensor at cell c, before slicing N/S, is:
    #   F_c[N, S] = sum_{E, W, ctl, ctr, cbl, cbr}
    #       site_t[ctl, N, ctr] * site_b[cbl, S, cbr] *
    #       T[N, E, S, W] *
    #       L_env_prev[ctl, cbl, W] * R_env_next[ctr, cbr, E]
    # where L_env_prev is the env before cell c (left_envs[c-1] or initial)
    # and R_env_next is the env after cell c (right_envs[c+1] or initial).

    # For the initial left env (before cell 0): L_init[ctl=1, cbl=1, W=BORDER] = 1.
    L_init = np.zeros((1, 1, DOM))
    L_init[0, 0, BORDER] = 1.0
    R_init = np.zeros((1, 1, DOM))
    R_init[0, 0, BORDER] = 1.0

    north_marginals = []
    south_marginals = []

    for c in range(L):
        st = top_mps.sites[c]  # (ctl, N, ctr)
        sb = bot_mps.sites[c]  # (cbl, S, cbr)
        T = cell_tensors_row[c]  # (N, E, S, W)

        L_prev = left_envs[c - 1] if c > 0 else L_init  # (ctl, cbl, W)
        R_next = right_envs[c + 1] if c < L - 1 else R_init  # (ctr, cbr, E)

        # Compute F[N, S, E, W]
        # F[N, S, E, W] = sum_{ctl, ctr, cbl, cbr}
        #   st[ctl, N, ctr] sb[cbl, S, cbr] T[N, E, S, W]
        #   L_prev[ctl, cbl, W] R_next[ctr, cbr, E]
        # Pre-contract st, sb against environments:
        # G[N, S, W, E] = sum_{ctl, ctr, cbl, cbr}
        #     st[ctl, N, ctr] * sb[cbl, S, cbr] * L_prev[ctl, cbl, W] * R_next[ctr, cbr, E]
        G = np.einsum('iNj,kSl,ikW,jlE->NSWE', st, sb, L_prev, R_next)
        # F = G * T (elementwise on N, E, S, W)
        F = np.einsum('NSWE,NESW->NSEW', G, T)

        # Z check (should equal Z_left)
        Z_c = float(F.sum())

        # Marginal of N at this cell (sum over S, E, W)
        p_N = F.sum(axis=(1, 2, 3))
        p_S = F.sum(axis=(0, 2, 3))
        # Normalize
        if p_N.sum() > 0:
            p_N = p_N / p_N.sum()
        if p_S.sum() > 0:
            p_S = p_S / p_S.sum()
        north_marginals.append(p_N)
        south_marginals.append(p_S)

    return {
        'Z_left': Z_left,
        'Z_right': Z_right,
        'north_marginals': north_marginals,
        'south_marginals': south_marginals,
    }


def compute_all_marginals(pieces, hints_map, chi_max: int):
    """Run forward and backward sweeps, then extract per-row marginals."""
    L = 16
    # Forward: store the boundary MPSes at each row (after absorbing 0..r-1).
    # mps_top[r] = MPS over north-edges of row r (BEFORE row r is absorbed).
    mps_top = [initial_top_boundary_mps(L)]
    for r in range(L):
        cells = [build_cell_tensor(pieces, hints_map, r, c) for c in range(L)]
        new_mps, _ = absorb_row(mps_top[-1], cells, chi_max)
        mps_top.append(new_mps)
    # mps_top[L] is the final MPS, which should project to BORDER everywhere.

    # Backward: build MPS sweeping bottom-to-top.
    # mps_bot[r] = MPS over south-edges of row r (BEFORE row r is absorbed
    # from below, i.e. after processing rows r+1..L-1).
    mps_bot = [initial_top_boundary_mps(L)]  # MPS below row L-1
    for r in range(L - 1, -1, -1):
        cells = [build_cell_tensor(pieces, hints_map, r, c) for c in range(L)]
        # Flip cell tensors vertically for the upward sweep
        cells_flipped = [flip_cell_tensor_vertically(T) for T in cells]
        new_mps, _ = absorb_row(mps_bot[-1], cells_flipped, chi_max)
        mps_bot.append(new_mps)
    # mps_bot is in reverse order: mps_bot[0] is below row 15, mps_bot[L]
    # is the final (above row 0).
    # We want mps_bot[r] = MPS over south-edges of row r.
    # mps_bot[r] in current indexing: after processing rows L-1..r, so it
    # represents the boundary above row r, which is the *south-edges of row r*.
    # Index: mps_bot_for_row[r] = mps_bot[L - r]
    # (mps_bot[0] is south-edges of row L-1, ...)
    mps_bot_for_row = {}
    for k, mps in enumerate(mps_bot):
        # mps_bot[k] represents the boundary after processing rows L-1, L-2, ..., L-k.
        # So it's the boundary ABOVE row L-k = the south-edges of row L-k-1.
        if 0 <= L - k - 1 < L:
            mps_bot_for_row[L - k - 1] = mps  # i.e., the MPS sitting just below row L-k-1
    # And we also need "below the entire grid" = mps_bot[0].

    # For row r marginals: top_mps = mps_top[r], bot_mps = mps_bot_for_row[r].
    # Wait: mps_bot[k] for k=0 is "MPS below row 15" = south_of_row_15.
    # If we want south-edges of row r as bot_mps, we need mps_bot[L-1-r].
    # Let me redo cleanly.

    # Cleaner indexing: produce mps_bot_after[r] = "MPS sitting on top of row r,
    # representing the contraction of rows r+1..L-1 viewed from above".
    # We start with mps_bot_initial below row L-1, then absorb row L-1 to get
    # mps "above row L-2" = mps_bot_after[L-2]. Etc.
    bot_initial = initial_top_boundary_mps(L)
    mps_bot_after = {L - 1: bot_initial}  # mps_bot_after[r] sits above row r? No.
    # Reset: define cleanly.

    # Re-implement from scratch for clarity.
    # bot[r] = MPS representing the contraction of rows r, r+1, ..., L-1
    #          from below upward, leaving the north-edges of row r free.
    # We want, for row r marginal computation: top_mps = mps_top[r] (with
    # north-edges of row r free), bot_mps = bot[r+1] (with south-edges of
    # row r free <=> north-edges of row r+1 free, which is what bot[r+1]
    # exposes).

    # Sweep upward.
    bot = {}
    bot[L] = initial_top_boundary_mps(L)  # empty product above row L-1: trivial
    for r in range(L - 1, -1, -1):
        cells = [build_cell_tensor(pieces, hints_map, r, c) for c in range(L)]
        cells_flipped = [flip_cell_tensor_vertically(T) for T in cells]
        new_mps, _ = absorb_row(bot[r + 1], cells_flipped, chi_max)
        bot[r] = new_mps

    # Per-row marginal extraction.
    all_north_marginals = {}  # all_north_marginals[r] = list of L color distributions
    all_south_marginals = {}
    for r in range(L):
        cells = [build_cell_tensor(pieces, hints_map, r, c) for c in range(L)]
        top_mps = mps_top[r]
        bot_mps_for_this_row = bot[r + 1] if r + 1 <= L - 1 else initial_top_boundary_mps(L)
        # Wait, for r = L-1, bot[L] = initial_top_boundary_mps which is
        # "below row L-1" — exactly south-edges = BORDER. Use bot[r+1] which
        # is bot[L] in that case. OK.
        bot_mps = bot[r + 1]
        res = horizontal_marginals(top_mps, bot_mps, cells)
        all_north_marginals[r] = [p.tolist() for p in res['north_marginals']]
        all_south_marginals[r] = [p.tolist() for p in res['south_marginals']]

    return all_north_marginals, all_south_marginals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chi', type=int, default=16)
    ap.add_argument('--no-hints', action='store_true')
    ap.add_argument('--out', default='output/v13_marginals.json')
    args = ap.parse_args()

    e2 = load()
    pieces = e2['pieces']
    hints_map = {} if args.no_hints else {pos: (pid, rot) for (pos, pid, rot) in e2['hints']}

    t0 = time.time()
    nm, sm = compute_all_marginals(pieces, hints_map, args.chi)
    dt = time.time() - t0
    print(f"computed marginals in {dt:.1f}s")

    # Summary: entropy distribution per edge.
    entropies = []
    L = 16
    DOM_local = DOM
    for r in range(L):
        for c in range(L):
            for which, marg in [('N', nm[r][c]), ('S', sm[r][c])]:
                m = np.array(marg)
                p = m[m > 0]
                if len(p) > 0:
                    h = -(p * np.log2(p)).sum()
                else:
                    h = 0.0
                entropies.append({'row': r, 'col': c, 'edge': which, 'entropy_bits': float(h),
                                  'max_prob': float(m.max()), 'support': int((m > 1e-9).sum())})

    e_arr = np.array([e['entropy_bits'] for e in entropies])
    p_arr = np.array([e['max_prob'] for e in entropies])
    s_arr = np.array([e['support'] for e in entropies])

    print(f"\nMarginal-entropy summary (N+S edges, all rows/cols):")
    print(f"  num edges            : {len(entropies)}")
    print(f"  median entropy       : {np.median(e_arr):.3f} bits")
    print(f"  mean entropy         : {e_arr.mean():.3f} bits")
    print(f"  min/max entropy      : {e_arr.min():.3f} / {e_arr.max():.3f} bits")
    print(f"  frozen edges (H<0.01) : {int((e_arr < 0.01).sum())}")
    print(f"  near-frozen (H<0.5)   : {int((e_arr < 0.5).sum())}")
    print(f"  uniform-ish (H>4.0)   : {int((e_arr > 4.0).sum())}")
    print()
    print(f"  median max_prob      : {np.median(p_arr):.3f}")
    print(f"  edges with max_prob > 0.5 : {int((p_arr > 0.5).sum())}")
    print(f"  edges with max_prob > 0.9 : {int((p_arr > 0.9).sum())}")
    print(f"  edges with max_prob > 0.99: {int((p_arr > 0.99).sum())}")
    print()
    print(f"  median support       : {np.median(s_arr):.1f} colors")

    Path(args.out).write_text(json.dumps({
        'chi': args.chi,
        'hints_enabled': not args.no_hints,
        'north_marginals': nm,
        'south_marginals': sm,
        'summary': {
            'median_entropy_bits': float(np.median(e_arr)),
            'frozen_edges': int((e_arr < 0.01).sum()),
            'near_frozen': int((e_arr < 0.5).sum()),
        }
    }))
    print(f"wrote {args.out}")


if __name__ == '__main__':
    main()
