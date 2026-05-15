// CP-with-LP-UB-pruning: backtracking border-placement search that
// prunes by LP relaxation upper-bound at each placement.
//
// Goal: efficiently find borders with LP UB above some threshold T,
// without enumerating the full 56! perimeter space.
//
// See vault/concepts/cp-with-lp-ub-pruning.md for the design.

#![forbid(unsafe_code)]

use std::collections::{HashMap, HashSet};
use std::path::PathBuf;

use eternity2_core::{Board, BORDER, PieceId, Position, Puzzle, Rotation};

/// User-facing options for the search.
#[derive(Debug, Clone)]
pub struct CpLpSearchOpts {
    /// Prune branches with LP UB < this threshold.
    pub threshold_ub: f64,
    /// Below this depth, use cheap pruning only (color count, Hall).
    pub phase1_depth_max: u32,
    /// At or below this depth, use reduced LP (B-B + B-I only).
    pub phase2_depth_max: u32,
    /// Total wall-clock budget.
    pub time_budget_secs: f64,
    pub threads: u32,
    pub save_dir: PathBuf,
}

impl Default for CpLpSearchOpts {
    fn default() -> Self {
        Self {
            threshold_ub: 478.0,
            phase1_depth_max: 30,
            phase2_depth_max: 55,
            time_budget_secs: 3600.0,
            threads: 8,
            save_dir: PathBuf::from("output/cp_lp_search"),
        }
    }
}

/// Result of a search run.
#[derive(Debug, Clone, Default)]
pub struct CpLpResult {
    pub n_explored: u64,
    pub n_pruned_cheap: u64,
    pub n_pruned_reduced_lp: u64,
    pub n_pruned_full_lp: u64,
    pub n_leaves_kept: u64,
    pub best_lp_ub_seen: f64,
    pub elapsed_secs: f64,
}

/// Placeholder: not yet implemented.
pub fn run_cp_lp_search(_puzzle: &Puzzle, _opts: &CpLpSearchOpts) -> Result<CpLpResult, String> {
    Err("cp-lp-search: implementation in progress".to_string())
}

/// Compute a *partial* LP UB given a partially-placed border board.
/// `placed` is the cells already committed. Empty cells are allowed.
/// Returns the LP optimum value (sum over y vars) given the partial state.
pub fn partial_lp_ub(_puzzle: &Puzzle, _board: &Board, _placed: &[Position])
    -> Result<f64, String>
{
    Err("partial_lp_ub: not yet implemented".to_string())
}

/// Helper: is `pos` on the puzzle perimeter (border ring)?
fn is_perimeter(puzzle: &Puzzle, pos: Position) -> bool {
    let (x, y) = puzzle.xy(pos);
    x == 0 || x == puzzle.width - 1 || y == 0 || y == puzzle.height - 1
}

/// Helper: list of (cell, side) pairs that are demanded by B-I edges
/// when the partial border has the given placed cells. Each entry
/// gives a required color the interior cell must present on that side.
fn b_i_demands_from_partial(puzzle: &Puzzle, board: &Board) -> Vec<(Position, u8, u8)> {
    let w = puzzle.width;
    let h = puzzle.height;
    let mut out = Vec::new();
    for pos in 0..puzzle.cell_count() {
        if !is_perimeter(puzzle, pos) { continue; }
        let Some((pid, rot)) = board.get(pos) else { continue; };
        let Some(p) = puzzle.piece(pid) else { continue; };
        let edges = p.edges.rotated(rot).as_array();
        let (x, y) = puzzle.xy(pos);
        // For each direction, if the neighbor is interior (not perimeter), record demand.
        if y > 0 {
            let n = (y - 1) * w + x;
            if !is_perimeter(puzzle, n) {
                out.push((n, 2u8, edges[0]));
            }
        }
        if x + 1 < w {
            let n = y * w + (x + 1);
            if !is_perimeter(puzzle, n) {
                out.push((n, 3u8, edges[1]));
            }
        }
        if y + 1 < h {
            let n = (y + 1) * w + x;
            if !is_perimeter(puzzle, n) {
                out.push((n, 0u8, edges[2]));
            }
        }
        if x > 0 {
            let n = y * w + (x - 1);
            if !is_perimeter(puzzle, n) {
                out.push((n, 1u8, edges[3]));
            }
        }
    }
    out
}

/// Cheap lower-bound check: returns false if it can prove LP UB < threshold.
///
/// Current implementation: Hall-condition check on (side, color) bipartite.
/// For each (side, color) pair, count demand from placed border cells and
/// supply from remaining INTERIOR pieces. If demand > supply for any
/// (side, color), the partial board cannot be completed without
/// unmatched B-I edges — which lowers the LP UB.
///
/// NB: this is a STRUCTURAL feasibility check, not a numerical UB bound.
/// It returns true (pass) for most reasonable partial borders. False
/// (prune) when the partial border has clearly violated single-slot supply.
pub fn cheap_lb_passes(puzzle: &Puzzle, board: &Board, _threshold: f64) -> bool {
    let max_color = puzzle.color_count.saturating_sub(1) as u8;

    // Collect B-I demands induced by placed perimeter cells.
    let demands = b_i_demands_from_partial(puzzle, board);
    let mut demand_by_side_color: HashMap<(u8, u8), u32> = HashMap::new();
    for &(_cell, side, color) in &demands {
        if color != BORDER {
            *demand_by_side_color.entry((side, color)).or_default() += 1;
        }
    }

    // Identify pinned pieces (any placed cell in board).
    let mut pinned: HashSet<PieceId> = HashSet::new();
    for pos in 0..puzzle.cell_count() {
        if let Some((pid, _)) = board.get(pos) {
            pinned.insert(pid);
        }
    }

    // Supply: (side, color) -> # (interior_piece, rotation) pairs.
    let mut supply_by_side_color: HashMap<(u8, u8), u32> = HashMap::new();
    for piece in puzzle.pieces() {
        if !piece.is_inner() { continue; }
        if pinned.contains(&piece.id) { continue; }
        for &r in &Rotation::ALL {
            let e = piece.edges.rotated(r).as_array();
            for s in 0u8..4 {
                if e[s as usize] != BORDER {
                    *supply_by_side_color.entry((s, e[s as usize])).or_default() += 1;
                }
            }
        }
    }

    // Check Hall condition: every (side, color) with demand must have supply >= demand.
    for s in 0u8..4 {
        for k in 1..=max_color {
            let d = *demand_by_side_color.get(&(s, k)).unwrap_or(&0);
            let sup = *supply_by_side_color.get(&(s, k)).unwrap_or(&0);
            if d > sup {
                return false;
            }
        }
    }

    true
}

#[cfg(test)]
mod tests {
    use super::*;
    use eternity2_puzzle_io::load_puzzle_with_hints;
    use std::path::PathBuf;

    #[test]
    fn skeleton_builds() {
        let _opts = CpLpSearchOpts::default();
    }

    #[test]
    fn cheap_lb_passes_on_empty_board() {
        let path = PathBuf::from("../../v2/../data/puzzles/size_16_official_eternity.csv");
        // Best-effort path; if missing, skip.
        if !path.exists() { return; }
        let Ok((puzzle, _)) = load_puzzle_with_hints(&path) else { return };
        let board = Board::empty(&puzzle);
        assert!(cheap_lb_passes(&puzzle, &board, 478.0));
    }
}
