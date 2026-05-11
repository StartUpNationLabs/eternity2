// Recover a Board from an edge-color assignment.
//
// For each cell, if all 4 surrounding edges are determined (boundary
// sides are fixed BORDER, interior sides are pinned by the assignment),
// look up the (piece, rotation) row whose 4-tuple matches. The
// piece-alldiff is solved by a greedy assignment: cells with the
// smallest candidate set first.
//
// Cells with any unassigned interior edge are left empty in the
// recovered Board — they're the "broken" cells the partial doesn't cover.

use std::collections::BTreeMap;

use eternity2_core::{Board, Color, Position, BORDER};

use crate::tables::Tables;
use crate::topology::{Topology, SIDE_BOTTOM, SIDE_LEFT, SIDE_RIGHT, SIDE_TOP};

/// Convert an edge-color assignment into a Board with pieces placed.
/// Cells with under-determined edges are left empty. Piece-uniqueness
/// is respected via a greedy assignment over fully-determined cells.
#[must_use]
pub fn recover_board(
    puzzle: &eternity2_core::Puzzle,
    topology: &Topology,
    tables: &Tables,
    edge_color: &[Option<Color>],
) -> Board {
    let mut board = Board::empty(puzzle);
    // For each cell, build the 4-tuple of edges (using BORDER for
    // boundary sides). Skip cells where any interior side is None.
    let mut candidates_per_cell: Vec<(u32, Vec<(eternity2_core::PieceId, eternity2_core::Rotation)>)> =
        Vec::with_capacity(topology.n_cells as usize);
    for c in 0..topology.n_cells {
        let sides = topology.cell_sides[c as usize];
        let mut edges_known: [Color; 4] = [BORDER; 4];
        let mut all_known = true;
        for s in 0..4 {
            edges_known[s] = match sides[s] {
                None => BORDER,
                Some(e) => match edge_color[e as usize] {
                    Some(k) => k,
                    None => { all_known = false; break; }
                },
            };
        }
        if !all_known {
            continue;
        }
        // Find rows matching this 4-tuple.
        let mut matches: Vec<(eternity2_core::PieceId, eternity2_core::Rotation)> = Vec::new();
        for row in &tables.rows {
            if row.edges == edges_known {
                matches.push((row.piece_id, row.rotation));
            }
        }
        candidates_per_cell.push((c, matches));
    }

    // Greedy assignment: cells with smallest candidate count first.
    candidates_per_cell.sort_by_key(|(_, m)| m.len());
    let mut used: Vec<bool> = vec![false; tables.max_piece_id as usize + 1];
    for (cell, candidates) in candidates_per_cell {
        for (pid, rot) in candidates {
            if !used[u32::from(pid) as usize] {
                used[u32::from(pid) as usize] = true;
                board.place(cell as Position, pid, rot);
                break;
            }
        }
        // If no unused candidate, leave cell empty — caller can score
        // the partial via the standard edge-matching metric.
    }
    let _ = (SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM, SIDE_LEFT);
    let _ = BTreeMap::<u32, u32>::new();
    board
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_core::{Edges, Piece, Puzzle};

    #[test]
    fn fully_determined_2x2_yields_complete_board() {
        let pieces = vec![
            Piece::new(0, Edges::new(BORDER, 1, 1, BORDER)),
            Piece::new(1, Edges::new(BORDER, BORDER, 1, 1)),
            Piece::new(2, Edges::new(1, 1, BORDER, BORDER)),
            Piece::new(3, Edges::new(1, BORDER, BORDER, 1)),
        ];
        let puzzle = Puzzle::new(2, 2, 2, pieces).unwrap();
        let topo = Topology::new(&puzzle);
        let tables = Tables::new(&puzzle, &topo);
        // 2×2: 4 interior edges (right of cell 0, down of cell 0, ...)
        // We set them all to color 1.
        let n_edges = topo.n_edges as usize;
        let edge_color = vec![Some(1u8); n_edges];
        let board = recover_board(&puzzle, &topo, &tables, &edge_color);
        // All 4 cells should be filled.
        for c in 0..4 {
            assert!(board.get(c).is_some(), "cell {c} not placed");
        }
    }
}
