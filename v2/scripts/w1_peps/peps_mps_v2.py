"""W1 — Clean boundary-MPS contraction (chi-truncated) for E2 PEPS.

Key design choice: PAD cell tensors to UNIFORM 4-axis (N, E, S, W) shape.
This way every cell has shape (K, K, K, K) and the border cells have a dummy
slot at the border axis. This avoids all the axis-order bookkeeping that
made v1 broken.

To represent "cell has border on side X", we set BORDER=0 to be the only
non-zero entry on that axis. That is: any cell tensor entry T[cN, cE, cS, cW]
is zero unless each border-side has color BORDER, and each non-border-side
does NOT have color BORDER. This is exactly what build_cell_tensor produces!

So we don't need to slice at all. Just use the full (K, K, K, K) tensor.
The "boundary" of the puzzle is implicit in the cell tensors having
zeros except on the BORDER axis at the appropriate side.

Then boundary-MPS contraction is uniform:
  - Initial MPS: an array of "virtual top neighbors" each contributing a delta
    on color BORDER. shape (K,) with value 1 at BORDER, 0 elsewhere.
  - For each row, contract along the N axis of each cell with the boundary
    MPS, retaining the S axis as new boundary MPS physical.
  - The E-W bonds of the row form the left-right bonds of the new MPS.
  - SVD-truncate to chi.
  - At the final row, contract the bottom-row S axes into BORDER deltas.

This is much cleaner. Let's implement it.
"""

from __future__ import annotations
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from puzzle_loader import Puzzle, BORDER


def build_full_cell_tensor(
    puzzle: Puzzle,
    pos: int,
    lookup: dict,
    mu: np.ndarray,
) -> np.ndarray:
    """Build the FULL (K, K, K, K) cell tensor in (cN, cE, cS, cW) order.

    Border sides are encoded by zero everywhere except color BORDER on that side.
    """
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
            w += np.exp(-mu[pid])
        T[cN, cE, cS, cW] += w
    return T


def initial_top_mps(K: int, size: int) -> list[np.ndarray]:
    """Build the initial boundary MPS = a row of "north of cell" deltas,
    each = 1 at BORDER color, 0 elsewhere.

    MPS tensor at column x has shape (bond_left, physical=N, bond_right).
    bond_left = bond_right = 1 (initially no horizontal correlations).
    physical = K (= colors).

    Initial values: M[0, BORDER, 0] = 1, all else 0.
    """
    mps = []
    for x in range(size):
        M = np.zeros((1, K, 1), dtype=np.float64)
        M[0, BORDER, 0] = 1.0
        mps.append(M)
    return mps


def initial_bottom_terminator(K: int, size: int) -> list[np.ndarray]:
    """Bottom "terminator" MPS = also row of BORDER deltas.
    Used to close the contraction after absorbing the last row.
    """
    return initial_top_mps(K, size)


def absorb_row_v2(
    mps: list[np.ndarray],
    row_cells: list[np.ndarray],
    chi: int,
) -> list[np.ndarray]:
    """
    Absorb one row of cells (each (K,K,K,K) in NESW) into the boundary MPS.

    Pre: mps[x] has shape (bl, K, br) where physical=N color at column x.
    Post: new_mps[x] has shape (new_bl, K, new_br) where physical=S color.

    Steps:
      1. For each cell, contract M[x] (axes bl, n_phys, br) with cell[x]
         (axes N, E, S, W):
           result[bl, e, s, w, br] = sum_n M[bl, n, br] * cell[n, e, s, w]
      2. Merge bl+w → new_bl, br+e → new_br (after handling adjacency):
         Actually the merging happens via SVD across adjacent columns.

    Approach: build a row of "merged" tensors with axes:
      (bl, E, S, W, br) per cell.
    Then sweep left-to-right, treating each adjacent E-W pair as a bond
    to be contracted, with SVD truncation.

    Concretely:
      - new_row[x].shape = (bl_x, E_x, S_x, W_x, br_x)
      - sweep: contract new_row[x].E_x with new_row[x+1].W_{x+1} via einsum.
      - this produces a merged tensor for the pair: (bl_x, S_x, [internal], S_{x+1}, br_{x+1})
      - reshape/SVD to split back into (bl_x, S_x, new_bond, S_{x+1}, br_{x+1})
      - this is essentially building the new MPS via a sequential left-canonical
        construction.

    Alternative cleaner approach: build the whole "row supertensor" as a chain,
    then convert chain → MPS via successive SVDs.
    """
    K_check = row_cells[0].shape[0]  # K
    K = K_check
    size = len(row_cells)

    # Step 1: contract M[x] with cell[x] for each x.
    # Result: row_merged[x] with shape (bl, E, S, W, br) = 5 axes.
    row_merged = []
    for x in range(size):
        M = mps[x]  # (bl, n_phys=K, br)
        C = row_cells[x]  # (N, E, S, W) = (K,K,K,K)
        # Einsum: 'lnr,nesw->lwsr...' wait, let me be careful
        # Contract M's n_phys axis (axis 1) with C's N axis (axis 0):
        # result[l, e, s, w, r] = sum_n M[l,n,r] * C[n,e,s,w]
        merged = np.einsum('lnr,nesw->leswr', M, C)
        # Reorder to (l, e, s, w, r) — same.
        row_merged.append(merged)

    # Step 2: now we have a chain of size tensors, each with 5 axes.
    # We need to:
    #   - Contract E_x with W_{x+1} (horizontal bond).
    #   - Build a new MPS with physical = S, left = (l_old), right = (r_old after merge).
    # The chain has 5 axes per cell: (l, E, S, W, r).
    # Combine into a single linear chain of MPS tensors with bonds:
    #   - vertical "old" bonds (l, r): preserved, get merged with horizontal bonds.
    # Actually the cleanest way is to merge each (l, W) into a new "left bond" and
    # each (E, r) into a new "right bond" of the new MPS tensor. But W of cell x
    # is bonded with E of cell x-1. So:
    #   new_left_bond[x] = previous_right_bond[x-1] horizontally bonded.
    # This collapses naturally if we view the row as a series of MPS tensors with:
    #   new_left = (l, W) tensor product
    #   new_right = (r, E) tensor product
    # but then we still need to contract W of cell x with E of cell x-1.

    # Let me explicitly build it via SVD sweep.
    # Treat the row as a chain MPS. After step 1, each tensor has shape
    # (l_x, E_x, S_x, W_x, r_x) = 5 axes.
    # Define MPS-canonical: at each position x, an MPS tensor T_x with axes
    # (left_bond, physical, right_bond), where:
    #   physical = S_x  (the new "boundary physical")
    #   left_bond starts as W_x * l_x (combined), right_bond as E_x * r_x.
    #   Adjacent T_x.right_bond bonds with T_{x+1}.left_bond, with the constraint
    #   that the E component of T_x.right_bond = W component of T_{x+1}.left_bond.
    # The way to enforce this is via SVD compression which automatically handles it.

    # Strategy: reshape each tensor and run a left-to-right SVD sweep.
    # T_x shape: (l_x, E_x, S_x, W_x, r_x).
    # Pack as: (l_x * W_x, S_x, E_x * r_x).
    # No wait — this would lose the E-W bond information. Instead:

    # Use the "canonical MPS via SVD" approach: stitch the chain into one big
    # tensor (size axes), then sequentially SVD-decompose. But that explodes
    # memory at large size.

    # Better: build it via successive contractions + SVD.
    # Initialize: M' = row_merged[0]. Shape (l_0, E_0, S_0, W_0, r_0).
    #   At x=0, W_0 should be BORDER-fixed (=BORDER index in the W axis).
    #   The l_0 bond should have dim 1 (no left neighbor before).
    # The MPS tensor T_0 should have shape (1, S_0, new_right_0). new_right_0
    # combines (E_0, r_0). To do this:
    #   reshape M' to (1 * W_0, S_0, E_0 * r_0). But W_0 is K-dim; that increases
    #   left bond from 1 to W_0=K. That's wrong unless we slice W_0 to its
    #   BORDER-fixed value.
    # Actually, the cell tensor at x=0 already has zeros except at W_0=BORDER.
    # So we can slice W_0=BORDER. Let me restructure:

    # Pre-step: for x=0, slice W_0 to BORDER. For x=size-1, slice E_x to BORDER.
    # After this:
    #   x=0: shape (l_0, E_0, S_0, r_0) = 4 axes (W removed).
    #   x=size-1: shape (l_x, S_x, W_x, r_x) = 4 axes (E removed).
    #   else: shape (l_x, E_x, S_x, W_x, r_x) = 5 axes.
    # Also, l_0=1, l_x = (input MPS's right bond at x-1+1, hmm)
    # Wait — l_x and r_x are bonds INHERITED from the input MPS. After step 1:
    #   row_merged[x].l = input_mps[x].bl
    #   row_merged[x].r = input_mps[x].br
    # And input_mps[x] is connected to input_mps[x+1] via shared bond br_x = bl_{x+1}.
    # Wait no, the MPS bonds are between adjacent MPS tensors, so input_mps[x].br is
    # already paired with input_mps[x+1].bl. But after we contract step 1, those
    # bonds are still independent because each row cell only touched its own M[x].
    # The MPS-input bond structure means input_mps[x].br IS the SAME index as
    # input_mps[x+1].bl. So row_merged[x].r == row_merged[x+1].l. We need to
    # contract them!

    # OK so actually the MPS-bond structure: bl_x = br_{x-1} (shared). After step 1
    # each row_merged[x] has both bl_x and br_x as axes but bl_x is THE SAME bond
    # as br_{x-1}. Need to contract those.

    # Let me redo step 1 properly via the input MPS structure.

    # Actually, my step 1 already used local matmul (lnr*nesw->leswr). The shared
    # bond r_x = l_{x+1} was preserved. So to contract the chain, I need to
    # contract row_merged[x].r with row_merged[x+1].l.

    # So the chain has, at each position x, a 5-axis tensor with axes
    # (l_x, E_x, S_x, W_x, r_x), and the bonds are:
    #   r_x ↔ l_{x+1} (vertical-direction bond inherited from input MPS)
    #   E_x ↔ W_{x+1} (horizontal-direction bond from cell-row)

    # So between consecutive merged tensors there are TWO bonds. After contracting
    # both, the combined tensor has axes (l_x, E_old—wait nothing, S_x, W_x, S_{x+1}, E_{x+1}, r_{x+1}).
    # So contracting two cells gives a 6-axis tensor (l_x, S_x, W_x, S_{x+1}, E_{x+1}, r_{x+1}).
    # And we lose 4 dims (r_x, l_{x+1}, E_x, W_{x+1}).

    # For boundary cells:
    #   x=0: W_0 is sliced to BORDER (or we keep the (K,) axis and use that BORDER component only).
    #   x=size-1: E_{size-1} similar.
    # For l_0 and r_{size-1}: input MPS has bl_0 = br_{size-1} = 1 (boundary).

    # Algorithm:
    # 1) Start with new_T = row_merged[0] with axes (l_0, E_0, S_0, W_0, r_0).
    #    Apply BORDER slicing on W_0 (since x=0): drop W_0 to single index BORDER.
    #    Reshape to MPS form (new_left, phys=S_0, new_right) where:
    #      new_left = l_0 (dim 1)
    #      new_right = combined (E_0, r_0)
    #    Wait we haven't contracted with cell 1 yet, so we can't combine E_0 with r_0
    #    quite yet. We need to keep them separate so we can contract them with their
    #    respective bonds when cell 1 comes.
    #
    # Cleanest implementation: use a "left-canonical sweep" with explicit
    # contraction of two bonds at a time.

    # Let's just do it carefully:
    # State: "accumulator" tensor A with axes (l_x, S_0..S_x, E_x, r_x).
    # At each step x: contract A.E_x and A.r_x with row_merged[x+1].W_{x+1} and l_{x+1}.
    # Then we get (l_x, S_0..S_{x+1}, E_{x+1}, r_{x+1}). After full sweep at x=size-1:
    # (l_0, S_0..S_{size-1}, E_{size-1}, r_{size-1}).
    # Slice E_{size-1}=BORDER (since x=size-1 has border on E).
    # Final shape: (1, S_0..S_{size-1}, 1). The new MPS has size physical axes
    # (one per column), each of dim K.

    # BUT this would yield a "monolithic" tensor with K^size entries.
    # For chi-truncation we want this reshaped as an MPS with bond dim chi.

    # So: after building the monolithic tensor, run a left-to-right SVD sweep
    # to convert to MPS form with bond dim ≤ chi.

    # Monolithic shape: (1, K, K, ..., K, 1) = K^size entries (after sl E_end).
    # For 4×4 K=8: K^4 = 4096. Manageable.
    # For 6×6 K=8: K^6 = 262144. Still OK.
    # For 8×8 K=8: K^8 = 16M. Borderline.
    # For 16×16 K=23: K^16 = 4e21. Need streaming truncation.

    # OK first cut: build monolithic, then SVD-MPS-truncate. Improve later
    # with streaming.

    # Now build monolithic.
    # First, slice boundaries:
    #   row_merged[0]: shape (l, E, S, W=K, r). Take W=BORDER => shape (l, E, S, r).
    #   row_merged[size-1]: shape (l, E=K, S, W, r). Take E=BORDER => shape (l, S, W, r).
    # If size==1 then x=0 and x=size-1 both apply.

    # Edge case size=1: row_merged[0] shape (l=1, E=K, S, W=K, r=1). Slice both W and E.
    # → shape (1, S, 1). Already MPS form.

    if size == 1:
        T = row_merged[0]  # (1, K, K, K, 1)
        T = T[:, BORDER, :, BORDER, :]  # (1, K, 1)
        return compress_mps([T], chi)

    # Build chain
    # First tensor: slice W_0=BORDER → (l_0, E_0, S_0, r_0)
    A = row_merged[0][:, :, :, BORDER, :]  # shape (l_0, E_0, S_0, r_0)
    # Note: input mps[0] has l_0=1 always (left boundary of MPS).
    # We don't slice l yet because it's already small.

    for x in range(1, size):
        Bm = row_merged[x]  # (l_x, E_x, S_x, W_x, r_x)
        # Contract A.E_{x-1} (axis ?) with B.W_x (axis 3), and A.r_{x-1} with B.l_x (axis 0).
        # A's axes so far: (l_0, S_0, S_1, ..., S_{x-1}, E_{x-1}, r_{x-1})
        # — after the first iter: A is (l_0, S_0, E_0, r_0); after second: (l_0, S_0, S_1, E_1, r_1); etc.

        # einsum: A_indices = '0,1,2,...,x-1,e,r' where '0'=l_0, '1'..'x-1'=S_0..S_{x-2}, 'e'=E_{x-1}, 'r'=r_{x-1}
        # Wait my A so far has S_0..S_{x-1} as axes 1..x. Plus E_{x-1} as axis x+1, r_{x-1} as axis x+2.
        # Total ndim of A: 1 (l_0) + x (S_0..S_{x-1}) + 1 (E_{x-1}) + 1 (r_{x-1}) = x+3.

        # B's axes: (l_x, E_x, S_x, W_x, r_x) = 5 axes.
        # Bond mapping: A.E_{x-1} (axis x+1) <-> B.W_x (axis 3)
        #               A.r_{x-1} (axis x+2) <-> B.l_x (axis 0)

        # After contraction: result has axes (l_0, S_0..S_{x-1}, E_x, S_x, r_x).
        # That's 1 + x + 1 + 1 + 1 = x+4 axes — one more S axis, E_{x-1} replaced by E_x, r updated.

        # Use letter-based einsum for clarity:
        # A indices: 'l' + ''.join(chr(ord('a')+i) for i in range(x)) + 'er'
        # B indices: 'rfgwq'  (l=r, e=f, s=g, w=w, r=q)
        # Wait the variable names collide. Let me reassign.

        a_indices = ['L'] + [f's{i}' for i in range(x)] + ['E_prev', 'R_prev']
        b_indices = ['R_prev', 'E_new', f's{x}', 'E_prev', 'R_new']
        # Wait, B.l_x is bonded with A.r_{x-1}, both should be R_prev.
        # B.W_x is bonded with A.E_{x-1}, both should be E_prev.
        b_indices = ['R_prev', 'E_new', f's{x}', 'E_prev', 'R_new']
        out_indices = ['L'] + [f's{i}' for i in range(x + 1)] + ['E_new', 'R_new']

        # Convert to einsum string. opt_einsum supports string labels via subscripts API but
        # numpy.einsum needs single chars. Map labels to letters.
        all_labels = list(set(a_indices + b_indices + out_indices))
        if len(all_labels) > 52:
            # Use opt_einsum which supports tuple indices for >52 unique
            import opt_einsum as oe
            out = oe.contract(A, a_indices, Bm, b_indices, out_indices)
        else:
            label_map = {lbl: chr(ord('a') + i) for i, lbl in enumerate(all_labels)}
            a_str = ''.join(label_map[l] for l in a_indices)
            b_str = ''.join(label_map[l] for l in b_indices)
            out_str = ''.join(label_map[l] for l in out_indices)
            out = np.einsum(f'{a_str},{b_str}->{out_str}', A, Bm)

        A = out

    # After loop: A has shape (l_0, S_0, S_1, ..., S_{size-1}, E_{size-1}, r_{size-1})
    # Slice E_{size-1}=BORDER (right border).
    # A has ndim = size + 3. The E_{size-1} axis is at position size+1 (after L, S_0..S_{size-1}).
    A = np.take(A, BORDER, axis=size + 1)  # remove E_{size-1} axis
    # New shape: (l_0=1, S_0, ..., S_{size-1}, r_{size-1}=1)

    # Now decompose into an MPS via SVD sweep.
    # A has shape (1, K, K, ..., K, 1) = size + 2 axes.
    new_mps = []
    leftover = A.reshape(1, -1)  # shape (1, K^size)
    bond_left = 1
    for x in range(size):
        # Reshape leftover to (bond_left, K, rest)
        leftover_mat = leftover.reshape(bond_left * K_check, -1)
        U, S, Vt = np.linalg.svd(leftover_mat, full_matrices=False)
        keep = min(chi, len(S))
        U = U[:, :keep]
        S = S[:keep]
        Vt = Vt[:keep, :]
        # MPS tensor: shape (bond_left, K, keep)
        new_mps.append(U.reshape(bond_left, K_check, keep))
        # Update leftover: S * Vt, then prepend new bond
        leftover = (S[:, None] * Vt)  # shape (keep, ...)
        bond_left = keep

    # leftover should now be (bond_left, 1) which we discard (= right boundary = 1)
    # We've absorbed (S, Vt) into the last MPS tensor's right bond already.
    # Wait actually after the SVD sweep we've split off each S axis sequentially.
    # The leftover at the end should be (bond_left_final, ?). Let me trace:
    # Start: leftover shape (1, K^size).
    # x=0: reshape to (1*K, K^{size-1}); SVD; keep ≤ chi.
    #      U: (1*K, keep). leftover: (keep, K^{size-1}).
    #      new_mps[0]: U.reshape(1, K, keep).
    # x=1: reshape leftover (keep, K^{size-1}) → (keep*K, K^{size-2}).
    #      SVD; U: (keep*K, keep1); leftover: (keep1, K^{size-2}).
    #      new_mps[1]: U.reshape(keep, K, keep1).
    # ...
    # x=size-1: leftover (some_bond, K). Reshape to (some_bond*K, 1). SVD.
    #      U: (some_bond*K, 1). leftover: (1, 1).
    #      new_mps[size-1]: U.reshape(some_bond, K, 1).
    # OK so after the loop, leftover is (1, 1) = scalar near 1. Absorb it.

    # Actually we already did keep=min(chi, len(S)) which truncates. The last
    # tensor's right bond is keep, and we should absorb any final scalar of S*Vt.

    # Hmm the issue is we discarded leftover after the loop. Let me check if
    # it's a scalar close to 1 (which means we've split everything off).

    # For correctness, multiply the last MPS tensor by the scalar leftover.
    # leftover shape is (bond_final, num_remaining_columns_squared_or_so).
    # After x=size-1, leftover is (chi_keep_size, 1). If chi_keep_size != 1...

    # The issue: when we SVD, the resulting U has shape (bond_left*K, keep), and
    # S*Vt has shape (keep, ...). We want to retain the full K^size norm. After
    # the last SVD, the "..." part has dim 1 (since we've split off all columns).
    # So leftover is (keep_final, 1). We should multiply new_mps[size-1] by this
    # final factor.

    # leftover.shape[0] should equal new_mps[-1]'s right-bond dim (= keep after
    # the last SVD). leftover[i, 0] is a scalar coefficient per right-bond index.
    # So new_mps[-1] should be multiplied by leftover[:, 0] along its right axis.

    final_factors = leftover[:, 0] if leftover.ndim == 2 else leftover
    # New mps[-1] has shape (bond_left, K, bond_right=keep_final). Multiply
    # along bond_right axis.
    new_mps[-1] = new_mps[-1] * final_factors[None, None, :]

    return new_mps


def compress_mps(mps: list[np.ndarray], chi: int) -> list[np.ndarray]:
    """Left-to-right SVD compression with bond cap chi."""
    n = len(mps)
    if n <= 1:
        return mps
    for i in range(n - 1):
        M = mps[i]
        l, p, r = M.shape
        U, S, Vt = np.linalg.svd(M.reshape(l * p, r), full_matrices=False)
        keep = min(chi, len(S))
        U = U[:, :keep]
        S = S[:keep]
        Vt = Vt[:keep, :]
        mps[i] = U.reshape(l, p, keep)
        mps[i + 1] = np.einsum('lr,rps->lps', S[:, None] * Vt, mps[i + 1])
    return mps


def contract_mps_with_bottom_row(mps: list[np.ndarray], bottom_row: list[np.ndarray]) -> float:
    """
    Final contraction: absorb the bottom row, contracting each cell's S axis
    with the boundary MPS's physical axis. For the bottom row, S axes are
    border-fixed to BORDER (the cell tensor is zero except at S=BORDER).

    Result is a scalar Z.
    """
    K = mps[0].shape[1]
    size = len(mps)
    # For each cell, M[x] (bl, K, br) contracts with bottom_cell[x] (N, E, S=K, W).
    # Bottom cell's S axis is "border-fixed" by zeros at non-BORDER. So contracting
    # over N (full K) and slicing the result for matching N and S.
    # Simpler: contract M[x].N_phys with bottom_cell[x].N, leaving E_x, S_x, W_x, bl, br.
    # Then sum over S_x (since bottom row is closed at S=BORDER, but actually the
    # cell tensor has zeros except at S=BORDER, so summing gives the same as taking
    # S=BORDER value).
    # Actually for a closed contraction, summing over S_x is correct — the cell
    # tensor is already 0 at S != BORDER for a bottom-row cell.

    # Then we have a chain of (E_x, W_x, bl, br) tensors. Contract E_x with W_{x+1},
    # bl_x with br_{x-1} via MPS bond, and at the boundaries: W_0=BORDER, E_{size-1}=BORDER,
    # bl_0 = br_{size-1} = 1.

    # This is essentially another "absorb_row" but with the result being a scalar.
    # Use the same monolithic-then-trace approach.

    # Step 1: contract M[x] with bottom_cell[x] -> (bl, E, S, W, br) per x.
    rows = []
    for x in range(size):
        M = mps[x]
        C = bottom_row[x]
        # einsum 'lnr,nesw->leswr'
        rows.append(np.einsum('lnr,nesw->leswr', M, C))

    # Step 2: sum S axes (since they're closed).
    # Actually S axis is shape K; for bottom row, the cell tensor is only nonzero at S=BORDER,
    # so taking S=BORDER gives the right answer. But also summing over S gives the same
    # answer since other entries are zero. Take S=BORDER for clarity.
    rows = [r[:, :, BORDER, :, :] for r in rows]  # shape (l, E, W, r)

    # Step 3: chain contract horizontally and over MPS bonds.
    # Each rows[x] has 4 axes (l_x, E_x, W_x, r_x).
    # Bonds: l_{x+1} = r_x, E_x = W_{x+1}.
    # Boundaries: l_0 = r_{size-1} = 1, W_0 = E_{size-1} = BORDER.

    # Debug: print shapes
    print(f"  [contract_mps_with_bottom_row] rows shapes: {[r.shape for r in rows]}")

    if size == 1:
        T = rows[0]  # (1, E=K, W=K, 1)
        return float(T[0, BORDER, BORDER, 0])

    # Slice W_0 = BORDER on rows[0], E_{size-1} = BORDER on rows[-1]:
    # rows[0]: (l, E, W, r) → take W=BORDER → (l, E, r)
    rows[0] = rows[0][:, :, BORDER, :]  # (l, E, r) = (1, K, r)
    rows[-1] = rows[-1][:, BORDER, :, :]  # (l, W, r) = (l, K, 1)

    print(f"  [contract_mps_with_bottom_row] after slicing rows[0]: {rows[0].shape} rows[-1]: {rows[-1].shape}")
    if size >= 3:
        print(f"  [contract_mps_with_bottom_row] rows[1]: {rows[1].shape}")

    # Issue diagnosis: the einsum index order. For rows[x] in middle, the order is
    # (l, E, W, r) coming from absorb_row's: it produced (bl, E, S, W, br) then we
    # took S=BORDER → (bl, E, W, br). So axes are bl=0, E=1, W=2, r=3. ✓
    # For A from rows[0]: (l=1, E=K, r). Axes are l=0, E=1, r=2.
    # Bond mapping: A.r (axis 2) = B.l (axis 0), A.E (axis 1) = B.W (axis 2).
    # einsum: A 'ler', B 'lewr' where l_A == l_B and e_A == w_B.
    # Rewrite with unique letters: A='aEr', B='rxyq' with E==y. Output 'axq'.
    # einsum string: 'aer,reaq->aaq' is wrong because 'a' is reused.
    # Use: A='ABC' (axis 0,1,2 = l,E,r), B='CDEF' (axis 0,1,2,3 = l,E,W,r).
    # Constraint: A.r = B.l → C = C (axis 2 of A and axis 0 of B share index).
    # Constraint: A.E = B.W → B = E (axis 1 of A and axis 2 of B share index).
    # So einsum: 'ABC,CBDF->ADF' wait — B axis 1 (E_new) should be free.
    # Let me redo: A indices 'aer', B indices 'rEwq', constraint a.e == B.w.
    # Map: r→bond1 (shared), e→bond2 (shared), so B's index 2 (W) is 'e'.
    # einsum: 'aer,reEq->aEq'. Where in the einsum string 'reEq' means B has axes
    # (l=r, E=E, W=e, r=q). Hmm yes upper/lower case helps. Let me use distinct letters.

    A = rows[0]  # (1, K, r)
    for x in range(1, size):
        B = rows[x]
        if x < size - 1:
            # B has 4 axes (l_x, E_x, W_x, r_x).
            # einsum: 'iWj,jkWl->ikl'  (i=A.l, W=A.E=B.W, j=A.r=B.l, k=B.E, l=B.r)
            # using j as the MPS bond, W as the horizontal bond.
            A = np.einsum('iWj,jkWl->ikl', A, B)
        else:
            # x == size-1. B has 3 axes (l_x, W_x, r_x=1).
            # einsum: 'iWj,jWl->il'  (i=A.l, W=A.E=B.W, j=A.r=B.l, l=B.r)
            A = np.einsum('iWj,jWl->il', A, B)

    # Final A shape (1, 1) → scalar
    return float(A[0, 0])


def compute_log_Z_chi_v2(
    puzzle: Puzzle,
    mu: np.ndarray,
    chi: int,
) -> float:
    """Compute log Z via boundary-MPS contraction with bond dim chi."""
    size = puzzle.size
    K = puzzle.n_colors

    # Lookup
    from peps_lagrangian_v3 import build_piece_signature_lookup
    lookup = build_piece_signature_lookup(puzzle)

    # Build all full cell tensors
    cells = [build_full_cell_tensor(puzzle, pos, lookup, mu) for pos in range(size * size)]

    # Initial top MPS
    mps = initial_top_mps(K, size)

    # Absorb rows 0..size-1
    # Each row r has cells indices r*size..r*size+size-1.
    # For row r, every cell's N axis bonds with mps[x].N_phys, every S becomes the new
    # boundary, every E-W is horizontal.
    # For row r=0: cells have n_border=True (sliced via zeros). Boundary MPS init
    # already encodes BORDER. So we just absorb.
    # For row r=size-1 (bottom): cells have s_border=True. We use the special
    # contract_mps_with_bottom_row to close.

    for r in range(size - 1):
        row_cells = [cells[r * size + x] for x in range(size)]
        mps = absorb_row_v2(mps, row_cells, chi)

    # Bottom row: close
    bottom_row = [cells[(size - 1) * size + x] for x in range(size)]
    Z = contract_mps_with_bottom_row(mps, bottom_row)
    if Z <= 0:
        return -np.inf
    return float(np.log(Z))


if __name__ == "__main__":
    import time
    from puzzle_loader import load_puzzle
    from peps_lagrangian_v3 import compute_piece_marginals_v3

    # Smoke test on 4×4
    p = load_puzzle("../data/generated/size_4_colors_6_92cd6738.csv")
    print(f"4×4 puzzle: K={p.n_colors}")
    mu = np.zeros(p.n_pieces)

    # Reference: exact
    t0 = time.time()
    log_Z_exact, _ = compute_piece_marginals_v3(p, mu, contract_opts={'optimize': 'greedy'})
    print(f"  exact: log_Z = {log_Z_exact:.6f}  ({time.time()-t0:.3f}s)")

    # MPS-chi
    for chi in [4, 8, 16, 32, 64]:
        t0 = time.time()
        log_Z = compute_log_Z_chi_v2(p, mu, chi)
        dt = time.time() - t0
        diff = log_Z - log_Z_exact
        print(f"  chi={chi:3d}: log_Z = {log_Z:.6f}  (Δ={diff:+.4e}, {dt:.3f}s)")
