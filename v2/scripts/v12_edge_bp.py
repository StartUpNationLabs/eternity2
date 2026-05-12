#!/usr/bin/env python3
"""Edge-color BP on canonical E2.

Encoding: variables = grid edges (cell-to-cell + cell-to-frame). Each
variable has 23 states (color 0 = BORDER, colors 1..22 interior).
Boundary edges are pinned to BORDER (delta). The 480 internal edges
are the inferrable variables.

Cell factor: cell c is satisfied iff some (piece, rotation) pair makes
its 4 rotated edges (N, E, S, W) equal the 4 incident-edge variable
values. Hint cells = restricted to a single (piece, rotation).

Soft piece-uniqueness: between BP iterations, normalize the per-piece
expected occupancy across cells so each piece tends to be used once.

Output: per-edge marginal distribution + per-edge entropy, dumped to
JSON for Rust-side consumption. Compare information content to
vol-11's cell-encoding 8.4% interior reduction.

This is the explicit follow-up to project_e2_dead_ends.md, which
recommended this encoding as the message-passing alternative to the
cell-encoding vol-11 ruled out.
"""
from __future__ import annotations

import sys
import json
import time
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v11_load_e2 as loader

W = H = 16
NSTATE = 23  # color 0 + 22 interior colors
BORDER = 0


# ------------------------------------------------------------------
# Grid graph construction.
#
# Cells indexed 0..255 (pos = y*W + x). Each cell has 4 sides:
# side 0 = North, 1 = East, 2 = South, 3 = West (matches PlacementInfo).
# Grid edges: pair of cell-side (each side participates in exactly 1
# grid edge). Boundary edges are pinned to BORDER.
# ------------------------------------------------------------------

def build_grid_edges():
    """Return:
    edges: list of grid-edge dicts with keys: id, kind ('internal'|'boundary'),
           and 'incidences' = list of (cell_pos, side) tuples (1 for boundary,
           2 for internal).
    cell_to_edge: cell_to_edge[pos][side] = edge_id.
    pinned: dict edge_id -> color (BORDER for boundary).
    """
    edges = []
    cell_to_edge = [[None, None, None, None] for _ in range(W * H)]
    pinned = {}
    # Vertical edges: between (x, y) and (x, y+1). cell (x,y) south = cell (x,y+1) north.
    for y in range(H):
        for x in range(W):
            pos = y * W + x
            # North side (side 0).
            if cell_to_edge[pos][0] is None:
                eid = len(edges)
                if y == 0:
                    # boundary edge
                    edges.append({"id": eid, "kind": "boundary",
                                  "incidences": [(pos, 0)]})
                    pinned[eid] = BORDER
                else:
                    npos = (y - 1) * W + x
                    edges.append({"id": eid, "kind": "internal",
                                  "incidences": [(pos, 0), (npos, 2)]})
                    cell_to_edge[npos][2] = eid
                cell_to_edge[pos][0] = eid
            # South side (side 2).
            if cell_to_edge[pos][2] is None:
                eid = len(edges)
                if y == H - 1:
                    edges.append({"id": eid, "kind": "boundary",
                                  "incidences": [(pos, 2)]})
                    pinned[eid] = BORDER
                    cell_to_edge[pos][2] = eid
            # West side (side 3).
            if cell_to_edge[pos][3] is None:
                eid = len(edges)
                if x == 0:
                    edges.append({"id": eid, "kind": "boundary",
                                  "incidences": [(pos, 3)]})
                    pinned[eid] = BORDER
                else:
                    npos = y * W + (x - 1)
                    edges.append({"id": eid, "kind": "internal",
                                  "incidences": [(pos, 3), (npos, 1)]})
                    cell_to_edge[npos][1] = eid
                cell_to_edge[pos][3] = eid
            # East side (side 1).
            if cell_to_edge[pos][1] is None:
                eid = len(edges)
                if x == W - 1:
                    edges.append({"id": eid, "kind": "boundary",
                                  "incidences": [(pos, 1)]})
                    pinned[eid] = BORDER
                    cell_to_edge[pos][1] = eid
    n_internal = sum(1 for e in edges if e["kind"] == "internal")
    n_boundary = sum(1 for e in edges if e["kind"] == "boundary")
    assert n_internal == 2 * W * H - W - H, f"internal {n_internal} expected {2*W*H-W-H}"
    assert n_boundary == 2 * (W + H), f"boundary {n_boundary} expected {2*(W+H)}"
    return edges, cell_to_edge, pinned


def piece_class(piece_edges):
    """Return cell class compatible with this piece: 'corner' / 'edge' / 'interior'."""
    n_border = int((piece_edges == BORDER).sum())
    if n_border == 2:
        return "corner"
    if n_border == 1:
        return "edge"
    return "interior"


def cell_class(pos):
    x, y = pos % W, pos // W
    n = int(x == 0) + int(x == W - 1) + int(y == 0) + int(y == H - 1)
    if n == 2: return "corner"
    if n == 1: return "edge"
    return "interior"


def cell_valid_configs(pos, pieces, hint_pieces_at):
    """Return all (piece_id, rotation, (n_color, e_color, s_color, w_color))
    tuples valid at cell `pos`. If `pos` is a hint, only one tuple.
    """
    if pos in hint_pieces_at:
        pid, rot = hint_pieces_at[pos]
        rotated = np.roll(pieces[pid], rot)
        return [(pid, rot, tuple(int(c) for c in rotated))]

    cclass = cell_class(pos)
    out = []
    # Border mask for cell: which sides face the gray frame (must be BORDER).
    x, y = pos % W, pos // W
    must_border = [y == 0, x == W - 1, y == H - 1, x == 0]
    for pid in range(256):
        if piece_class(pieces[pid]) != cclass:
            continue
        for rot in range(4):
            rotated = np.roll(pieces[pid], rot)
            ok = True
            for s in range(4):
                if must_border[s] and rotated[s] != BORDER:
                    ok = False; break
                if (not must_border[s]) and rotated[s] == BORDER:
                    ok = False; break
            if ok:
                out.append((pid, rot, tuple(int(c) for c in rotated)))
    return out


def run_bp(damping=0.5, n_iters=80, soft_uniqueness=True, log=True):
    """Run edge-color BP. Returns (edge_marginals, info)."""
    p = loader.load()
    pieces = p["pieces"]  # [256, 4]
    hints = p["hints"]
    hint_pieces_at = {pos: (pid, rot) for pos, pid, rot in hints}

    edges, cell_to_edge, pinned = build_grid_edges()
    n_edges = len(edges)

    # Per-cell config list. Compute once.
    cell_configs = []
    for pos in range(W * H):
        configs = cell_valid_configs(pos, pieces, hint_pieces_at)
        cell_configs.append(configs)
        if log and pos in hint_pieces_at:
            print(f"  hint cell {pos}: {len(configs)} configs (pinned)")
    if log:
        tot = sum(len(c) for c in cell_configs)
        print(f"  total cell configs: {tot} (sum of |D[pos]|)")

    # Message arrays.
    #   m_cf[pos, side] : message from cell `pos` to incident edge variable on `side`.
    #                     shape [256, 4, NSTATE].
    #   m_fc[edge_id, side_in_edge]: message from edge to incident cell. Boundary
    #                                edges have only 1 incidence; internal have 2.
    #
    # Represent edge-side messages as a list (one or two per edge), each [NSTATE].
    m_cf = np.full((W * H, 4, NSTATE), 1.0 / NSTATE)
    # m_fc[edge_id] = list of np.array(NSTATE) per incidence in same order as
    # edges[edge_id]['incidences'].
    m_fc = []
    for e in edges:
        if e["kind"] == "boundary":
            v = np.zeros(NSTATE); v[BORDER] = 1.0
            m_fc.append([v])  # pinned message
        else:
            m_fc.append([np.full(NSTATE, 1.0 / NSTATE) for _ in range(2)])

    # Belief = product over incident edges' messages-to-cell, then a soft
    # piece-availability prior (optional).
    piece_use = np.ones(256)  # used^-1 prior — start uniform

    if log: print(f"running BP: damping={damping}, iters={n_iters}, "
                  f"soft_uniqueness={soft_uniqueness}")
    t0 = time.time()

    def cell_belief_over_configs(pos):
        """For each config (pid, rot, edge_colors), the unnormalized weight =
        prod over s in 0..3 of m_fc into pos from edge cell_to_edge[pos][s]
        on the edge-color = edge_colors[s]. Plus optional piece-use weight.
        Returns numpy array over configs."""
        configs = cell_configs[pos]
        if not configs:
            return np.array([])
        ws = np.empty(len(configs))
        # Per-side edge messages into pos (after rotating across edge sides).
        in_msg = np.empty((4, NSTATE))
        for s in range(4):
            eid = cell_to_edge[pos][s]
            e = edges[eid]
            # find which incidence in this edge corresponds to (pos, s)
            inc_idx = e["incidences"].index((pos, s))
            # message from edge to this incidence
            if e["kind"] == "boundary":
                in_msg[s] = m_fc[eid][0]
            else:
                # message from edge to incidence inc_idx is the message-from-
                # the-OTHER incidence (sum-product). Already stored as
                # m_fc[eid][inc_idx]:
                in_msg[s] = m_fc[eid][inc_idx]
        for i, (pid, rot, col) in enumerate(configs):
            w = in_msg[0, col[0]] * in_msg[1, col[1]] * in_msg[2, col[2]] * in_msg[3, col[3]]
            if soft_uniqueness:
                w *= piece_use[pid]
            ws[i] = w
        return ws

    history = []
    for it in range(n_iters):
        change = 0.0
        # Update each cell's outgoing messages.
        new_m_cf = np.zeros_like(m_cf)
        # Also compute per-piece expected occupancy for soft uniqueness.
        new_piece_acc = np.zeros(256)
        for pos in range(W * H):
            configs = cell_configs[pos]
            if not configs:
                continue
            ws = cell_belief_over_configs(pos)
            s = ws.sum()
            if s <= 0:
                continue  # leave previous messages; rare during early iters
            ws_n = ws / s
            # For each outgoing side `s_out`: marginal over the color on side s_out,
            # but DIVIDED by the contribution from the OTHER side's incoming message
            # (to maintain "sum-product over all factors except this one" semantics).
            # Cleaner form: compute m_cf[pos, s_out, c] = sum over configs whose
            # side-s_out color == c, of (config_weight / m_fc_in[s_out, c])
            # but division is numerically unstable. Use the standard formulation:
            #   m_cf[pos, s_out, c] = sum_{configs with color[s_out]=c}
            #     prod_{s' != s_out} m_fc_in[s', col[s']] * piece_use_weight
            # Accumulate that directly.
            in_msg = np.empty((4, NSTATE))
            for s_out in range(4):
                eid = cell_to_edge[pos][s_out]
                e = edges[eid]
                inc_idx = e["incidences"].index((pos, s_out))
                if e["kind"] == "boundary":
                    in_msg[s_out] = m_fc[eid][0]
                else:
                    in_msg[s_out] = m_fc[eid][inc_idx]
            for s_out in range(4):
                acc = np.zeros(NSTATE)
                for (pid, rot, col) in configs:
                    w = 1.0
                    for s in range(4):
                        if s == s_out:
                            continue
                        w *= in_msg[s, col[s]]
                    if soft_uniqueness:
                        w *= piece_use[pid]
                    acc[col[s_out]] += w
                # Normalize.
                t = acc.sum()
                if t > 0:
                    acc /= t
                new_m_cf[pos, s_out] = acc
            # Piece-occupancy accumulator (each config contributes its
            # normalized prob to its piece-id).
            for i, (pid, rot, col) in enumerate(configs):
                new_piece_acc[pid] += ws_n[i]

        # Apply damping on m_cf, and recompute m_fc from m_cf.
        diff = np.abs(new_m_cf - m_cf).sum()
        m_cf = damping * new_m_cf + (1 - damping) * m_cf
        change = diff

        # Recompute m_fc. For each internal edge with 2 incidences (a, b),
        # m_fc to a = m_cf from b; m_fc to b = m_cf from a. Boundary edges
        # have only 1 incidence and the pinned BORDER message remains.
        for eid, e in enumerate(edges):
            if e["kind"] == "boundary":
                continue  # pinned
            (pa, sa), (pb, sb) = e["incidences"]
            m_fc[eid][0] = m_cf[pa, sa].copy()  # delivered to pb in next round? No — convention:
            # in our list, m_fc[eid][i] is the message *from edge to incidence i*.
            # Standard formulation: message from edge to var = product over OTHER
            # vars' messages-to-edge times the factor. Here the "factor" is the
            # identity constraint (same color), so it just passes the other side
            # through.
            m_fc[eid][0] = m_cf[pb, sb].copy()  # to incidence 0 (pa, sa) = from (pb, sb)
            m_fc[eid][1] = m_cf[pa, sa].copy()

        # Soft piece-use re-normalization. Sum of new_piece_acc should be ~256
        # (one per cell). Target occupancy is 1 per piece. We adjust piece_use
        # multiplicatively: piece_use *= (1 / new_piece_acc)^lr, capped.
        if soft_uniqueness:
            lr = 0.3
            mass = new_piece_acc.sum()
            if mass > 0:
                target = mass / 256.0  # expected per-piece mass under uniform usage
                ratio = np.where(new_piece_acc > 1e-9, target / new_piece_acc, 1.0)
                piece_use *= np.exp(lr * np.log(np.clip(ratio, 0.05, 20.0)))

        if log and (it < 5 or it % 5 == 0):
            print(f"  iter {it:3d}: msg_change={change:8.3f}  "
                  f"piece_use[min,max]=[{piece_use.min():.3f},{piece_use.max():.3f}]")
        history.append({"iter": it, "change": float(change),
                        "piece_use_min": float(piece_use.min()),
                        "piece_use_max": float(piece_use.max())})
        if change < 1e-3:
            if log: print(f"  converged at iter {it}")
            break

    elapsed = time.time() - t0
    if log: print(f"BP done in {elapsed:.1f} s after {len(history)} iters")

    # Compute edge marginals (over the 480 internal edges).
    # For internal edge with incidences (pa, sa), (pb, sb):
    #   edge_belief[c] propto m_cf[pa, sa, c] * m_cf[pb, sb, c]
    edge_marginals = []
    interior_entropies = []
    uniform_entropy = float(np.log(NSTATE))
    interior_uniform_entropy = float(np.log(NSTATE - 1))  # without BORDER
    for eid, e in enumerate(edges):
        if e["kind"] == "boundary":
            m = np.zeros(NSTATE); m[BORDER] = 1.0
            edge_marginals.append({"id": eid, "kind": "boundary", "marginal": m.tolist(),
                                   "entropy": 0.0})
            continue
        (pa, sa), (pb, sb) = e["incidences"]
        m = m_cf[pa, sa] * m_cf[pb, sb]
        # Exclude BORDER from internal edges (boundary already pinned)
        m[BORDER] = 0.0
        s = m.sum()
        if s > 0:
            m /= s
        # Entropy in nats (interior colors only).
        eps = 1e-12
        ent = -float(np.sum(m[1:] * np.log(m[1:] + eps)))
        edge_marginals.append({"id": eid, "kind": "internal", "marginal": m.tolist(),
                               "entropy": ent})
        interior_entropies.append(ent)

    mean_ent = float(np.mean(interior_entropies))
    reduction = (interior_uniform_entropy - mean_ent) / interior_uniform_entropy * 100.0
    info = {
        "elapsed_s": elapsed,
        "iters_run": len(history),
        "history": history,
        "mean_interior_edge_entropy": mean_ent,
        "interior_uniform_entropy": interior_uniform_entropy,
        "interior_reduction_pct": reduction,
        "cell_config_total": sum(len(c) for c in cell_configs),
    }

    return edge_marginals, info


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--damping", type=float, default=0.5)
    ap.add_argument("--iters", type=int, default=80)
    ap.add_argument("--no-uniqueness", action="store_true")
    ap.add_argument("--out", type=str, default="output/v12_bp/edge_bp.json")
    args = ap.parse_args()

    print(f"=== edge-color BP on canonical E2 ({W}x{H}, {NSTATE-1} colors) ===")
    edge_marginals, info = run_bp(
        damping=args.damping,
        n_iters=args.iters,
        soft_uniqueness=not args.no_uniqueness,
        log=True,
    )
    print()
    print(f"Mean interior-edge entropy: {info['mean_interior_edge_entropy']:.3f} nats")
    print(f"Uniform-edge entropy:       {info['interior_uniform_entropy']:.3f} nats")
    print(f"Reduction:                  {info['interior_reduction_pct']:.2f}%")
    print()
    print(f"(Vol-11 cell-encoding interior reduction was 8.4%.)")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        json.dump({"schema_version": 1, "info": info,
                   "edges": edge_marginals}, f)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
