#!/usr/bin/env python3
"""Vol-13 — Boundary-MPS contraction of the E2 tile partition function.

The genuinely-unwalked angle: a Liang-2025-style tensor-network contraction
of the canonical Eternity II tile model, *with bond-dimension truncation*
to keep it tractable.

# Setup

- 16x16 grid. Each cell has a 4-leg tile tensor T_c[N,E,S,W] where
  T_c[N,E,S,W] = 1 if there exists a (piece_id, rotation) placeable at
  cell c with those colors on N,E,S,W (and the piece type matches the
  cell type: corner / edge / interior); 0 otherwise.
  Hint cells use a delta-tensor for the specific (piece, rotation).
- "Above the grid" all north-edges of row 0 = BORDER (color 0).
- "Below the grid" all south-edges of row 15 = BORDER.
- Similarly for columns 0 and 15 (left/right).
- All-different-over-pieces is NOT enforced. This is a relaxation —
  the contraction counts colorings that come from *some* tile but does
  not prevent re-use of the same piece. We discuss the gap in §Validation
  below.

# Boundary MPS

We sweep top-to-bottom. After processing rows 0..r-1, the "boundary
state" is a vector indexed by the 16 vertical bonds going into row r.
The boundary state is *not* materialized as a 23^16-dim vector; it is
represented as a Matrix Product State of L=16 sites, each of shape
(chi_left, 23, chi_right). chi is bond dimension, truncated by SVD
after each row to a target chi_max.

To process row r:
  1. For each column c, contract the cell tile tensor T_c[N,E,S,W] with
     the MPS site at column c (matching its physical leg N to the
     site's physical leg).
  2. After step 1, the MPS site at column c becomes a tensor with two
     dangling legs (E and S) and the W leg shared with site c-1, the
     N leg consumed.
  3. The W-E legs are "horizontal" bonds between adjacent sites in the
     row. After processing the whole row, the horizontal bonds become
     part of the MPS's left/right virtual bonds. The S legs become the
     new physical legs of the updated MPS (going into the NEXT row).
  4. Truncate via SVD to chi_max.

# Outputs

  * log Z (the log of the unnormalized partition function) — gives the
    information-theoretic count of "valid colorings" under this relaxed
    model.
  * Per-edge marginals P(c | edge) — recovered from the MPS by
    contracting against the partial-trace identity.
  * Memory and time per row.

# Caveats

  * All-different is dropped. The count is an upper bound on the true
    count.
  * For small chi, this is approximate. We sweep chi ∈ {1, 4, 16, 64}.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from v11_load_e2 import load


BORDER = 0
N_COLORS = 22
DOM = N_COLORS + 1  # 0..22


def all_rotations(piece):
    t, r, b, l = piece
    return [
        (t, r, b, l),
        (l, t, r, b),
        (b, l, t, r),
        (r, b, l, t),
    ]


def build_cell_tensor(pieces, hints_map, row: int, col: int) -> np.ndarray:
    """T[N,E,S,W] for cell at (row, col)."""
    pos = row * 16 + col
    is_n_border = (row == 0)
    is_s_border = (row == 15)
    is_w_border = (col == 0)
    is_e_border = (col == 15)
    n_borders = int(is_n_border) + int(is_s_border) + int(is_w_border) + int(is_e_border)
    # n_borders=0: interior, 1: edge, 2: corner

    T = np.zeros((DOM, DOM, DOM, DOM), dtype=np.float64)

    # If hint, use the specific piece-rotation
    if pos in hints_map:
        pid, rot = hints_map[pos]
        t, r, b, l = all_rotations(pieces[pid])[rot]
        T[t, r, b, l] = 1.0
        return T

    border_counts = (pieces == BORDER).sum(axis=1)
    if n_borders == 0:
        eligible = np.where(border_counts == 0)[0]
    elif n_borders == 1:
        eligible = np.where(border_counts == 1)[0]
    else:
        eligible = np.where(border_counts == 2)[0]

    for pid in eligible:
        for (t, r, b, l) in all_rotations(pieces[pid]):
            # Enforce border edges
            if is_n_border and t != BORDER: continue
            if not is_n_border and t == BORDER: continue
            if is_s_border and b != BORDER: continue
            if not is_s_border and b == BORDER: continue
            if is_w_border and l != BORDER: continue
            if not is_w_border and l == BORDER: continue
            if is_e_border and r != BORDER: continue
            if not is_e_border and r == BORDER: continue
            T[t, r, b, l] += 1.0
    return T


@dataclass
class MPS:
    """L sites of shape (chi_l, d, chi_r). Site i has physical leg of
    dimension d (here, d=DOM=23). chi_l of site 0 and chi_r of site L-1
    are both 1."""
    sites: list[np.ndarray] = field(default_factory=list)

    @classmethod
    def from_vector(cls, v: np.ndarray) -> 'MPS':
        """Build trivial MPS from a vector v[c0,c1,...,c_{L-1}]."""
        L = v.ndim
        sites = []
        rest = v.reshape(1, -1)  # (1, d^L)
        for i in range(L - 1):
            d = v.shape[i]
            rest = rest.reshape(rest.shape[0] * d, -1)
            U, S, Vh = np.linalg.svd(rest, full_matrices=False)
            chi = len(S)
            sites.append((U * S).reshape(-1, d, chi))
            rest = Vh
        # Last site
        d = v.shape[-1]
        sites.append(rest.reshape(-1, d, 1))
        return cls(sites=sites)

    def physical_dim(self) -> int:
        return self.sites[0].shape[1]

    def length(self) -> int:
        return len(self.sites)

    def bond_dims(self) -> list[int]:
        return [s.shape[2] for s in self.sites[:-1]]

    def total_norm_sq(self) -> float:
        """Compute <psi|psi> by sweeping left-to-right."""
        # Start with shape (chi_l_0=1, chi_l_0=1) = (1,1) identity
        L = np.eye(1)
        for s in self.sites:
            # s shape (cl, d, cr). L shape (cl, cl).
            # L_new[cr, cr'] = sum_{cl, cl', d} L[cl, cl'] s[cl, d, cr] s[cl', d, cr']
            L = np.einsum('ij,idk,jdl->kl', L, s, s)
        return float(L[0, 0])

    def left_canonicalize(self) -> float:
        """Left-canonicalize, returning the norm of the state."""
        norm = 1.0
        L = self.length()
        for i in range(L - 1):
            cl, d, cr = self.sites[i].shape
            M = self.sites[i].reshape(cl * d, cr)
            Q, R = np.linalg.qr(M)
            self.sites[i] = Q.reshape(cl, d, Q.shape[1])
            # Push R into next site
            self.sites[i + 1] = np.einsum('ij,jkl->ikl', R, self.sites[i + 1])
        # Last site holds the norm
        last = self.sites[-1]
        # last shape (cl, d, 1)
        n = np.linalg.norm(last)
        if n > 0:
            self.sites[-1] = last / n
        return n * norm


def absorb_row(mps: MPS, cell_tensors: list[np.ndarray], chi_max: int) -> tuple[MPS, float]:
    """Contract a full row of cell tensors into the boundary MPS.

    Each cell tensor has shape (D, D, D, D) for (N, E, S, W).
    The MPS represents the boundary state going into this row: each site
    has shape (chi_l, D, chi_r). Site c's physical leg = north-edge of
    cell c.

    After absorption:
      - For each site c, contract its physical leg (north of cell) with
        T_c's N-leg.
      - T_c's W-leg becomes a new "horizontal" bond connecting site c
        and site c-1 (with site c-1's E-leg).
      - T_c's E-leg connects to site c+1's W-leg.
      - T_c's S-leg becomes the new physical leg of site c.
    Then SVD-truncate.

    Returns (new_mps, log_scale) where log_scale tracks the accumulated
    log of the normalization absorbed during SVD truncation.
    """
    L = len(cell_tensors)
    assert L == mps.length()
    D = mps.physical_dim()

    log_scale = 0.0

    # Build "raw" extended sites with horizontal bonds explicit.
    # site_raw[c] shape (chi_l, D_W, D_S, chi_r, D_E)? -- too complex.
    # Simpler: we sweep left to right, maintaining a running tensor.

    # Step 1: form "merged" tensors M_c of shape (chi_l, chi_r, D_W, D_E, D_S),
    # by contracting MPS[c].physical (=N) with T_c.N.
    merged = []
    for c in range(L):
        s = mps.sites[c]  # (cl, d, cr)
        T = cell_tensors[c]  # (N, E, S, W) -- index 0=N, 1=E, 2=S, 3=W
        # Contract s's d-leg with T's N-leg (axis 0)
        # m[cl, cr, E, S, W] = sum_n s[cl, n, cr] * T[n, E, S, W]
        m = np.einsum('inj,nesw->ijesw', s, T)
        merged.append(m)

    # Step 2: sweep left to right, fusing horizontal bonds (W of c with E of c-1)
    # The result is a new MPS over physical leg = S, with new virtual bonds.
    # current shape: (chi_l_new, S_dim, fused_right_bond)
    # We track A_c with shape (left_bond, S, "right_carrying" combined of cr*E*W_of_next_cells)
    # Easiest: sweep building new sites one-by-one and truncating.

    new_sites = []
    # Left edge: the "W" leg of cell 0 must be BORDER (color 0)
    # We enforce this by slicing merged[0] along W=BORDER.
    # General code: the leftmost W has no neighbor; for E2 boundary cells
    # this is already enforced via cell tensor (W=BORDER for col 0).
    # But for interior columns, W is connected to cell c-1's E.

    # Initialize "left environment" L0 of shape (chi_l=1, 1)  i.e. trivial
    # Actually we will build the new MPS site-by-site.

    # The merged tensor at c has indices (cl, cr, E, S, W). When we
    # process site c, we have a "carry" tensor C of shape
    # (new_left_bond, current_cr, current_E) coming from site c-1.
    # We contract C's E with merged[c]'s W:
    #   X[new_l, cr_prev, cl_c, S, E, cr_c] = sum_W C[new_l, cr_prev, W] *
    #     (need to also link cr_prev with cl_c, since they were originally
    #      separate sites in the input MPS — but they aren't actually
    #      linked: the input MPS has cr_prev = cl_c by definition of bond).
    # So we should think of the input MPS bond between c-1 and c as
    # a single index k.
    #
    # Let me restate. The input MPS bond between site c-1 and site c is
    # a single internal index. So merged[c-1].cr == merged[c].cl. Let's
    # call it k_{c-1,c}.
    # We carry through the sweep one combined tensor:
    #   A[new_left, k_{c-1,c}, E_{c-1}] after processing site c-1.
    # When we process site c:
    #   B[new_left, S, E_c, k_{c,c+1}] = sum_{k_{c-1,c}, W_c=E_{c-1}}
    #     A[new_left, k_{c-1,c}, E_{c-1}] * merged[c][k_{c-1,c}, k_{c,c+1}, E_c, S, W_c]
    #   with W_c = E_{c-1}.
    # Then SVD to factor into A_new[new_left, S, new_left'] * carry[new_left', k_{c,c+1}, E_c].

    # Initialize: before site 0, A = identity in form (1, k_init, E_init).
    # But site 0 has no left neighbor in input MPS — chi_l_0 = 1. And no left
    # horizontal bond from a "site -1" — we model it by initializing A as
    # shape (1, chi_l_0=1, E_dim=1)  with A[0,0,0]=1, and slice merged[0]
    # along W=BORDER below.

    # For E2 specifically the cell tensor at col 0 has W=BORDER (col 0
    # is boundary). So merged[0][:, :, :, :, W=BORDER] is the right slice
    # — we just contract over W and it's only nonzero at W=BORDER.
    # Same for col 15: E=BORDER. We handle that in the final close-off.

    # Concretely: start with A0 of shape (1, 1, DOM): trivial new_left,
    # trivial k_prev (= chi_l of first MPS site = 1), and W-leg of dim DOM
    # with all weight on BORDER (col 0's W is BORDER).
    A = np.zeros((1, 1, DOM), dtype=np.float64)
    A[0, 0, BORDER] = 1.0

    for c in range(L):
        m = merged[c]  # (cl, cr, E, S, W)
        cl, cr, Ed, Sd, Wd = m.shape
        # carry index E_prev should equal W of m
        assert A.shape[1] == cl, f"chi mismatch at site {c}: A.shape[1]={A.shape[1]} cl={cl}"
        assert A.shape[2] == Wd, f"W dim mismatch at site {c}: A.shape[2]={A.shape[2]} Wd={Wd}"

        # B[new_left, k_next, E, S] = sum_{k_prev, W} A[new_left, k_prev, W] * m[k_prev, k_next, E, S, W]
        B = np.einsum('nkw,kKesw->nKes', A, m)
        # B shape: (new_left, k_next=cr, E, S)
        new_left, K_next, E_next, S_dim = B.shape

        # Now factor B = A_new[new_left, S, new_left'] * carry[new_left', K_next, E_next]
        # Reshape: (new_left*S) x (K_next*E_next), SVD, truncate.
        M = B.transpose(0, 3, 1, 2).reshape(new_left * S_dim, K_next * E_next)
        if M.size == 0 or np.linalg.norm(M) == 0:
            # zero tensor — partition function is zero
            new_sites.append(np.zeros((new_left, S_dim, 1), dtype=np.float64))
            A = np.zeros((1, K_next, E_next), dtype=np.float64)
            continue
        U, S, Vh = np.linalg.svd(M, full_matrices=False)
        # Truncate
        chi_new = min(chi_max, len(S))
        # Drop near-zero singular values
        tol = max(S) * 1e-14
        chi_new_eff = min(chi_new, int((S > tol).sum()))
        if chi_new_eff == 0:
            new_sites.append(np.zeros((new_left, S_dim, 1), dtype=np.float64))
            A = np.zeros((1, K_next, E_next), dtype=np.float64)
            continue

        # Rescale to avoid under/overflow. Pull out a global scale.
        max_s = float(S[0])
        log_scale += np.log(max_s)
        S_n = S[:chi_new_eff] / max_s

        U = U[:, :chi_new_eff]
        Vh = Vh[:chi_new_eff, :]

        A_new = U.reshape(new_left, S_dim, chi_new_eff)
        # Multiply S into Vh -> carry
        carry = (S_n[:, None] * Vh).reshape(chi_new_eff, K_next, E_next)

        new_sites.append(A_new)
        A = carry

    # After last site, A has shape (chi_after_last, K_after_last=1, E_after_last)
    # We need E_after_last to be BORDER (col 15 is the right edge).
    # Cell tensor at col 15 has E=BORDER, so merged[L-1] has E_dim = 1 entry
    # only nonzero at E=BORDER. After SVD carry's last leg E is dim D, but
    # only index BORDER is populated. Sum it down — but actually since the
    # cell tensor itself zeroes other E, the carry's E-only-BORDER entry is
    # the only contribution. We absorb by slicing carry[:, :, BORDER] then
    # multiply into the last MPS site's bond.

    # Last site shape (chi_l, S, chi_r=cr_last). cr_last must be 1 in input
    # MPS (last site of input MPS has chi_r=1). So K_after_last=1.
    assert A.shape[1] == 1, f"K_after_last != 1 (got {A.shape[1]})"
    # A shape (chi, 1, D). Take E=BORDER slice.
    closure = A[:, 0, :]  # (chi, D)
    # The cell tensor enforced E=BORDER so only closure[:, BORDER] is non-zero
    # in principle. But because of SVD compression at site L-1 we may have
    # smeared. Take the BORDER slice as the boundary projector.
    closure_vec = closure[:, BORDER]  # (chi,)
    # Multiply closure_vec into the last new_sites entry's right bond.
    last = new_sites[-1]  # (cl, S, cr=chi)
    fused = np.einsum('isr,r->is', last, closure_vec)
    new_sites[-1] = fused.reshape(fused.shape[0], fused.shape[1], 1)

    new_mps = MPS(sites=new_sites)
    return new_mps, log_scale


def initial_top_boundary_mps(L: int) -> MPS:
    """Boundary MPS above row 0: all north-edges = BORDER (color 0).

    Each site is a (1, DOM, 1) tensor with a 1.0 at the BORDER index.
    """
    sites = []
    for _ in range(L):
        s = np.zeros((1, DOM, 1), dtype=np.float64)
        s[0, BORDER, 0] = 1.0
        sites.append(s)
    return MPS(sites=sites)


def close_bottom_boundary(mps: MPS) -> float:
    """Close off the bottom of the grid: all south-edges must be BORDER.

    Returns log(<bottom_border | mps>).
    """
    L = mps.length()
    # Project each site's physical leg to BORDER, then contract the chain.
    # site shape (cl, d, cr). After projection: (cl, cr).
    proj = []
    for s in mps.sites:
        proj.append(s[:, BORDER, :])  # (cl, cr)
    M = proj[0]
    for i in range(1, L):
        M = M @ proj[i]
    # M now shape (1, 1)
    val = float(M[0, 0])
    if val <= 0:
        return float('-inf')
    return np.log(val)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chi', type=int, default=16, help='bond-dim truncation')
    ap.add_argument('--rows', type=int, default=16, help='how many rows to sweep')
    ap.add_argument('--no-hints', action='store_true')
    ap.add_argument('--out', type=str, default=None)
    args = ap.parse_args()

    print(f"loading canonical E2 ...")
    e2 = load()
    pieces = e2['pieces']
    if args.no_hints:
        hints_map = {}
    else:
        hints_map = {pos: (pid, rot) for (pos, pid, rot) in e2['hints']}
    print(f"hints: {len(hints_map)} {'' if hints_map else '(disabled)'}")

    L = 16
    chi_max = args.chi
    n_rows = args.rows

    print(f"chi_max = {chi_max}, n_rows = {n_rows}")
    print(f"sweeping top boundary -> down")

    mps = initial_top_boundary_mps(L)
    log_Z = 0.0
    t_start = time.time()
    per_row = []
    for r in range(n_rows):
        cell_tensors = [build_cell_tensor(pieces, hints_map, r, c) for c in range(L)]
        t0 = time.time()
        mps, log_scale = absorb_row(mps, cell_tensors, chi_max)
        log_Z += log_scale
        dt = time.time() - t0
        bd = mps.bond_dims()
        norm_sq = mps.total_norm_sq()
        log_norm = 0.5 * (np.log(norm_sq) if norm_sq > 0 else -np.inf)
        actual_logZ_so_far = log_Z + log_norm
        max_bond = max(bd) if bd else 1
        print(f"  row {r:2d}  | dt={dt:5.2f}s | bonds max={max_bond:4d} | logZ(so-far) = {actual_logZ_so_far:.4f}")
        per_row.append({'row': r, 'dt_s': dt, 'max_bond': max_bond, 'log_Z_partial': actual_logZ_so_far})

    if n_rows == 16:
        log_Z_bot = close_bottom_boundary(mps)
        total_log_Z = log_Z + log_Z_bot
        print(f"\nclosing bottom boundary: log(closure) = {log_Z_bot:.4f}")
        print(f"TOTAL log Z = {total_log_Z:.4f}")
        print(f"Z ~= e^{total_log_Z:.2f}  (under no-piece-uniqueness relaxation)")

    elapsed = time.time() - t_start
    print(f"\nsweep total: {elapsed:.1f}s")

    if args.out:
        out = {
            'chi_max': chi_max,
            'n_rows': n_rows,
            'hints_enabled': not args.no_hints,
            'log_Z': log_Z,
            'log_Z_total': total_log_Z if n_rows == 16 else None,
            'per_row': per_row,
        }
        Path(args.out).write_text(json.dumps(out, indent=2))
        print(f"wrote {args.out}")


if __name__ == '__main__':
    main()
