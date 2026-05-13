use std::collections::BTreeSet;
use eternity2_core::{Board, PieceId, Position, Puzzle, Rotation, BORDER};
use pathfinding::kuhn_munkres::kuhn_munkres;

/// Reframe the local repair as an Optimal Transport (Linear Assignment) problem.
/// For the k pieces currently residing in `free_set`, we find the global optimal
/// permutation of these pieces across the k positions, assuming all *other* 
/// neighbors remain fixed at their current state.
/// We iterate this process until the assignment stops changing (fixed point)
/// or we hit max iterations.
pub fn iterative_ot_repair(
    puzzle: &Puzzle,
    board: &Board,
    free_set: &BTreeSet<Position>,
    max_iters: u32,
) -> Board {
    let mut current_board = board.clone();
    let positions: Vec<Position> = free_set.iter().copied().collect();
    let k = positions.len();
    if k == 0 {
        return current_board;
    }

    let w = puzzle.width;
    let h = puzzle.height;

    for _iter in 0..max_iters {
        // 1. Extract the k pieces currently at the free positions.
        let mut pieces = Vec::with_capacity(k);
        for &pos in &positions {
            if let Some((pid, _)) = current_board.get(pos) {
                pieces.push(pid);
            } else {
                // If the board is incomplete, OT repair cannot function cleanly.
                // It expects a fully populated board (which ALNS maintains).
                return current_board;
            }
        }

        // 2. Build the cost matrix and best-rotation memory.
        // cost_matrix[i][j] = cost of placing pieces[i] at positions[j]
        let mut cost_matrix = vec![vec![0i64; k]; k];
        let mut best_rotations = vec![vec![0u8; k]; k];

        for (i, &pid) in pieces.iter().enumerate() {
            let p = puzzle.piece(pid).expect("Piece not found");
            for (j, &pos) in positions.iter().enumerate() {
                let x = pos % w;
                let y = pos / w;

                let mut min_mismatches = 5; // max possible is 4
                let mut best_rot = 0;

                for rot in 0..4 {
                    let edges = p.edges.rotated(rot as u8).as_array();
                    let mut mismatches = 0;

                    // Top
                    if y == 0 {
                        if edges[0] != BORDER { mismatches += 1; }
                    } else {
                        let top_pos = pos - w;
                        if let Some((n_pid, n_rot)) = current_board.get(top_pos) {
                            if free_set.contains(&top_pos) {
                                // Dynamic neighbor: for Sinkhorn, we use its current state
                                let n_p = puzzle.piece(n_pid).unwrap();
                                let n_edges = n_p.edges.rotated(n_rot).as_array();
                                if edges[0] != n_edges[2] && edges[0] != 0 && n_edges[2] != 0 { mismatches += 1; }
                            } else {
                                // Static neighbor
                                let n_p = puzzle.piece(n_pid).unwrap();
                                let n_edges = n_p.edges.rotated(n_rot).as_array();
                                if edges[0] != n_edges[2] && edges[0] != 0 && n_edges[2] != 0 { mismatches += 1; }
                            }
                        }
                    }

                    // Right
                    if x == w - 1 {
                        if edges[1] != BORDER { mismatches += 1; }
                    } else {
                        let right_pos = pos + 1;
                        if let Some((n_pid, n_rot)) = current_board.get(right_pos) {
                            let n_p = puzzle.piece(n_pid).unwrap();
                            let n_edges = n_p.edges.rotated(n_rot).as_array();
                            if edges[1] != n_edges[3] && edges[1] != 0 && n_edges[3] != 0 { mismatches += 1; }
                        }
                    }

                    // Bottom
                    if y == h - 1 {
                        if edges[2] != BORDER { mismatches += 1; }
                    } else {
                        let bottom_pos = pos + w;
                        if let Some((n_pid, n_rot)) = current_board.get(bottom_pos) {
                            let n_p = puzzle.piece(n_pid).unwrap();
                            let n_edges = n_p.edges.rotated(n_rot).as_array();
                            if edges[2] != n_edges[0] && edges[2] != 0 && n_edges[0] != 0 { mismatches += 1; }
                        }
                    }

                    // Left
                    if x == 0 {
                        if edges[3] != BORDER { mismatches += 1; }
                    } else {
                        let left_pos = pos - 1;
                        if let Some((n_pid, n_rot)) = current_board.get(left_pos) {
                            let n_p = puzzle.piece(n_pid).unwrap();
                            let n_edges = n_p.edges.rotated(n_rot).as_array();
                            if edges[3] != n_edges[1] && edges[3] != 0 && n_edges[1] != 0 { mismatches += 1; }
                        }
                    }

                    if mismatches < min_mismatches {
                        min_mismatches = mismatches;
                        best_rot = rot;
                    }
                }

                cost_matrix[i][j] = min_mismatches as i64;
                best_rotations[i][j] = best_rot as u8;
            }
        }

        // 3. Run Hungarian Algorithm (Kuhn-Munkres) to minimize mismatches.
        // `assignment[i]` = j, meaning piece `i` goes to position `j`.
        let (_, assignment) = kuhn_munkres(&cost_matrix);

        // 4. Update the board
        let mut next_board = current_board.clone();
        let mut changed = false;

        for (i, &j) in assignment.iter().enumerate() {
            let pid = pieces[i];
            let pos = positions[j];
            let rot = best_rotations[i][j];

            let prev = current_board.get(pos);
            if prev != Some((pid, rot)) {
                changed = true;
            }
            next_board.set(pos, pid, rot);
        }

        current_board = next_board;

        if !changed {
            break; // Reached fixed point
        }
    }

    current_board
}
